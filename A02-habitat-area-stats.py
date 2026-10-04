"""Calculate the area of each benthic and geomorphic class per region (A02).

Reads the published habitat rasters in data/out/ and the regionalisations downloaded
by A01, and writes data/out/stats/A02_Habitat-area-stats.csv. Intermediate results
are cached in working/A02/ so a failed run resumes at the stage that failed. Delete
the cache of a stage, and of every later stage, after changing its inputs.

See A02-habitat-area-stats-spec.md for the method.
"""
import csv
import math
import os
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from osgeo import gdal, ogr, osr
from pyproj import Geod
from tqdm import tqdm

gdal.UseExceptions()
ogr.UseExceptions()

# Resolving the symbolic link keeps the long CAPAD paths under the Windows path length limit.
IN3P = Path(os.path.realpath("data/in-3p"))
WORK = Path("working/A02")
OUT = Path("data/out/stats")
OUT_CSV = OUT / "A02_Habitat-area-stats.csv"
CHECKS_CSV = WORK / "A02_checks.csv"
EATLAS_SHARE = "https://nextcloud.eatlas.org.au/s/QBRBYaisJCgXf7g"

MAPPINGS = {
    "Benthic": Path("data/out/benthic/NW_NESP-MaC-3-17_UQ_Shallow-habitat_Benthic_2025.tif"),
    "Geomorphic": Path("data/out/geomorphic/NW_NESP-MaC-3-17_UQ_Shallow-habitat_Geomorphic_2025.tif"),
}

REGIONALISATIONS = {
    "analysis-region": {
        "name": "Analysis-regions v1",
        "path": IN3P / "nesp-3-17-analysis-regions" / "analysis-regions.shp",
        "fields": ["region", "subregion"],
        "identity": ["subregion"],
        "order": ["region", "subregion"],
    },
    "imcra": {
        "name": "IMCRA v4.0 Meso-scale Bioregions (2023)",
        "path": IN3P / "IMCRA-v4-0-Meso-Bioregions" / "IMCRA-v4-Mesoscale-Bioregions.shp",
        "fields": ["MESO_NAME"],
        "identity": ["MESO_NAME"],
        "order": ["MESO_NAME"],
    },
    "capad": {
        "name": "CAPAD 2024 - Marine",
        "path": IN3P / "CAPAD-2024" / "Collaborative_Australian_Protected_Areas_Database_(CAPAD)_2024_-_Marine.shp",
        "fields": ["TYPE", "NAME"],
        "identity": ["TYPE", "NAME"],
        "order": ["TYPE", "NAME"],
    },
}
ZONED = ["analysis-region", "imcra"]

DATASET = "Dataset"
OUTSIDE = "Outside all regions"
UNKNOWN = "Unknown"
OVERLAP_LIMIT_M2 = 0.01e6
TOLERANCE = 1e-6
NCLS = 256

# WGS84 ellipsoid
WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563

SRS_4326 = osr.SpatialReference()
SRS_4326.ImportFromEPSG(4326)
SRS_4326.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)


# ---------------------------------------------------------------- helpers

def tmp_path(path):
    return path.with_name(path.stem + ".tmp" + path.suffix)


def write_csv_atomic(df, path):
    tmp = tmp_path(path)
    df.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, path)


def read_palette(tif):
    clr = tif.with_suffix(".clr")
    if not clr.exists():
        sys.exit(f"Palette not found: {clr}")
    palette = {}
    for line in clr.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=5)
        if len(parts) == 6:
            palette[int(parts[0])] = parts[5].strip()
    return dict(sorted(palette.items()))


def raster_info(tif):
    ds = gdal.Open(str(tif))
    band = ds.GetRasterBand(1)
    gt = ds.GetGeoTransform()
    _, block_height = band.GetBlockSize()
    return ds, band, gt, ds.RasterXSize, ds.RasterYSize, block_height


def row_areas_m2(gt, ny):
    """Area of the pixels in each raster row, on the WGS84 ellipsoid (authalic formula)."""
    e2 = WGS84_F * (2 - WGS84_F)
    e = math.sqrt(e2)
    b = WGS84_A * (1 - WGS84_F)

    def q(lat):
        s = np.sin(np.radians(lat))
        return s / (1 - e2 * s * s) + np.log((1 + e * s) / (1 - e * s)) / (2 * e)

    top = gt[3] + gt[5] * np.arange(ny, dtype=np.float64)
    return np.abs(np.radians(gt[1]) * b * b / 2 * (q(top) - q(top + gt[5])))


def check_row_areas(mapping, gt, areas):
    """Compare the formula with pyproj.Geod for the first, middle and last rows. Stops on failure."""
    geod = Geod(ellps="WGS84")
    worst = 0.0
    for r in (0, len(areas) // 2, len(areas) - 1):
        top = gt[3] + gt[5] * r
        bottom = top + gt[5]
        left, right = gt[0], gt[0] + gt[1]
        geod_area, _ = geod.polygon_area_perimeter([left, right, right, left], [top, top, bottom, bottom])
        rel = abs(abs(geod_area) - areas[r]) / abs(geod_area)
        worst = max(worst, rel)
    if worst > TOLERANCE:
        sys.exit(f"{mapping}: pixel area formula differs from pyproj.Geod by {worst:.2e} (limit {TOLERANCE:g})")
    return worst


def memory_layer(geoms, values):
    """In-memory OGR layer with an integer 'zone' attribute. Keep the returned datasource alive."""
    driver = ogr.GetDriverByName("Memory") or ogr.GetDriverByName("MEM")
    mem = driver.CreateDataSource("")
    layer = mem.CreateLayer("zones", SRS_4326, ogr.wkbUnknown)
    layer.CreateField(ogr.FieldDefn("zone", ogr.OFTInteger))
    for geom, value in zip(geoms, values):
        feat = ogr.Feature(layer.GetLayerDefn())
        feat.SetField("zone", int(value))
        feat.SetGeometry(ogr.CreateGeometryFromWkb(geom.wkb))
        layer.CreateFeature(feat)
    return mem, layer


def burn(layer, gt, x0, y0, width, height):
    """Rasterise the 'zone' attribute onto a window of the habitat grid (pixel centres)."""
    out = gdal.GetDriverByName("MEM").Create("", int(width), int(height), 1, gdal.GDT_UInt16)
    out.SetGeoTransform((gt[0] + x0 * gt[1], gt[1], 0.0, gt[3] + y0 * gt[5], 0.0, gt[5]))
    gdal.RasterizeLayer(out, [1], layer, options=["ATTRIBUTE=zone"])
    return out.GetRasterBand(1).ReadAsArray()


def label(row, fields):
    return " / ".join(str(row[f]) for f in fields)


# ---------------------------------------------------------------- stage 1: regions

def polygonal(geom):
    if geom is None or geom.is_empty:
        return None
    if geom.is_valid:
        return geom
    geom = shapely.make_valid(geom)
    parts = [g for g in getattr(geom, "geoms", [geom]) if g.geom_type in ("Polygon", "MultiPolygon")]
    return shapely.union_all(parts) if parts else None


def check_overlaps(slug, cfg, gdf):
    projected = gdf.to_crs(3112).reset_index(drop=True)
    left, right = projected.sindex.query(projected.geometry, predicate="intersects")
    keep = left < right
    failures = []
    for i, j in zip(left[keep], right[keep]):
        overlap = projected.geometry.iloc[i].intersection(projected.geometry.iloc[j])
        if overlap.area > OVERLAP_LIMIT_M2:
            failures.append({
                "region_a": label(projected.iloc[i], cfg["identity"]),
                "region_b": label(projected.iloc[j], cfg["identity"]),
                "area_km2": overlap.area / 1e6,
                "geometry": overlap,
            })
    print(f"  {int(keep.sum())} touching pairs, {len(failures)} overlaps larger than "
          f"{OVERLAP_LIMIT_M2 / 1e6:g} km2")
    if failures:
        path = WORK / f"A02_overlaps_{slug}.gpkg"
        gpd.GeoDataFrame(failures, crs=3112).to_file(path, driver="GPKG")
        for f in failures:
            print(f"    {f['region_a']} x {f['region_b']}: {f['area_km2']:.4f} km2")
        sys.exit(f"{cfg['name']} has overlapping regions. See {path}")


def prepare_regions(slug, cfg, bbox):
    gpkg = WORK / f"A02_regions_{slug}.gpkg"
    if gpkg.exists():
        print(f"{cfg['name']}: using cached {gpkg}")
        return gpd.read_file(gpkg)
    if not cfg["path"].exists():
        sys.exit(f"{cfg['path']} not found. Run A01-download-analysis-data.py first.")

    print(f"{cfg['name']}: preparing regions")
    gdf = gpd.read_file(cfg["path"])[cfg["fields"] + ["geometry"]].to_crs(4326)
    invalid = int((~gdf.geometry.is_valid).sum())
    gdf["geometry"] = gdf.geometry.apply(polygonal)
    gdf = gdf[gdf.geometry.notna()]
    gdf = gdf[gdf.intersects(shapely.box(*bbox))]
    print(f"  {len(gdf)} features intersect the habitat extent, {invalid} invalid geometries repaired")
    if slug == "capad":
        gdf = gdf.dissolve(by=cfg["identity"], as_index=False)
        print(f"  dissolved to {len(gdf)} protected areas")

    duplicated = gdf[gdf.duplicated(cfg["identity"], keep=False)]
    if len(duplicated):
        names = sorted({label(r, cfg["identity"]) for _, r in duplicated.iterrows()})
        sys.exit(f"{cfg['name']} has repeated identities: {names}")
    if slug in ZONED:
        check_overlaps(slug, cfg, gdf)

    gdf = gdf.sort_values(cfg["order"]).reset_index(drop=True)
    gdf = gdf[cfg["fields"] + ["geometry"]]
    if slug in ZONED:
        gdf.insert(0, "zone", np.arange(1, len(gdf) + 1, dtype=np.int32))
        lookup = pd.concat([pd.DataFrame({"zone": [0], **{f: [""] for f in cfg["fields"]}}),
                            gdf.drop(columns="geometry")], ignore_index=True)
        lookup.loc[0, cfg["identity"][-1]] = OUTSIDE
        write_csv_atomic(lookup, WORK / f"A02_zones_{slug}.csv")

    tmp = tmp_path(gpkg)
    if tmp.exists():
        tmp.unlink()
    gdf.to_file(tmp, driver="GPKG", layer=slug)
    os.replace(tmp, gpkg)
    return gdf


# ---------------------------------------------------------------- stage 2: main pass

def main_pass(mapping, tif, zone_regions):
    cache = WORK / f"A02_main_{mapping.lower()}.csv"
    if cache.exists():
        print(f"{mapping}: using cached {cache}")
        return pd.read_csv(cache)

    ds, band, gt, nx, ny, block_height = raster_info(tif)
    areas = row_areas_m2(gt, ny)
    worst = check_row_areas(mapping, gt, areas)
    print(f"{mapping}: pixel area formula agrees with pyproj.Geod to {worst:.1e}")

    layers = {slug: memory_layer(gdf.geometry, gdf["zone"]) for slug, gdf in zone_regions.items()}
    nzones = {slug: len(gdf) + 1 for slug, gdf in zone_regions.items()}
    area_sums = {slug: np.zeros(n * NCLS) for slug, n in nzones.items()}
    pixel_sums = {slug: np.zeros(n * NCLS, dtype=np.int64) for slug, n in nzones.items()}
    total_area = np.zeros(NCLS)
    total_pixels = np.zeros(NCLS, dtype=np.int64)

    start = time.perf_counter()
    for y0 in tqdm(range(0, ny, block_height), desc=f"{mapping} main pass", unit="strip"):
        height = min(block_height, ny - y0)
        strip = band.ReadAsArray(0, y0, nx, height)
        cols = np.flatnonzero(strip.any(axis=0))
        if cols.size == 0:
            continue
        c0, c1 = int(cols[0]), int(cols[-1]) + 1
        sub = strip[:, c0:c1]
        rows, cc = np.nonzero(sub)
        values = sub[rows, cc].astype(np.intp)
        weights = areas[y0 + rows]
        total_area += np.bincount(values, weights=weights, minlength=NCLS)
        total_pixels += np.bincount(values, minlength=NCLS)
        for slug, (_, layer) in layers.items():
            zones = burn(layer, gt, c0, y0, c1 - c0, height)[rows, cc].astype(np.intp)
            key = zones * NCLS + values
            area_sums[slug] += np.bincount(key, weights=weights, minlength=nzones[slug] * NCLS)
            pixel_sums[slug] += np.bincount(key, minlength=nzones[slug] * NCLS)
    print(f"{mapping}: main pass took {(time.perf_counter() - start) / 60:.1f} min")

    records = []
    for cid in np.flatnonzero(total_pixels):
        records.append(("dataset", 0, int(cid), int(total_pixels[cid]), float(total_area[cid])))
    for slug in zone_regions:
        for key in np.flatnonzero(pixel_sums[slug]):
            zone, cid = divmod(int(key), NCLS)
            records.append((slug, zone, cid, int(pixel_sums[slug][key]), float(area_sums[slug][key])))
    df = pd.DataFrame(records, columns=["Regionalisation", "Zone", "Class_id", "Pixels", "Area_m2"])
    df["Row_area_check"] = worst
    write_csv_atomic(df, cache)
    return df


# ---------------------------------------------------------------- stage 3: protected areas

def protected_area_sums(band, gt, nx, ny, block_height, areas, geom):
    area = np.zeros(NCLS)
    pixels = np.zeros(NCLS, dtype=np.int64)
    minx, miny, maxx, maxy = geom.bounds
    x0 = max(0, math.floor((minx - gt[0]) / gt[1]))
    x1 = min(nx, math.ceil((maxx - gt[0]) / gt[1]))
    y0 = max(0, math.floor((maxy - gt[3]) / gt[5]))
    y1 = min(ny, math.ceil((miny - gt[3]) / gt[5]))
    if x1 <= x0 or y1 <= y0:
        return area, pixels

    ys = y0
    while ys < y1:
        ye = min(y1, (ys // block_height + 1) * block_height)
        height = ye - ys
        strip = band.ReadAsArray(x0, ys, x1 - x0, height)
        cols = np.flatnonzero(strip.any(axis=0))
        if cols.size:
            c0, c1 = int(cols[0]), int(cols[-1]) + 1
            left, right = gt[0] + (x0 + c0) * gt[1], gt[0] + (x0 + c1) * gt[1]
            top, bottom = gt[3] + ys * gt[5], gt[3] + ye * gt[5]
            # Clipping first keeps rasterisation fast for polygons with hundreds of thousands of vertices.
            part = shapely.clip_by_rect(geom, left, bottom, right, top)
            if not part.is_empty:
                _mem, layer = memory_layer([part], [1])
                inside = burn(layer, gt, x0 + c0, ys, c1 - c0, height)
                sub = strip[:, c0:c1]
                rows, cc = np.nonzero((sub != 0) & (inside == 1))
                values = sub[rows, cc].astype(np.intp)
                weights = areas[ys + rows]
                area += np.bincount(values, weights=weights, minlength=NCLS)
                pixels += np.bincount(values, minlength=NCLS)
        ys = ye
    return area, pixels


def capad_pass(mapping, tif, palette, capad):
    cache = WORK / f"A02_capad_{mapping.lower()}.csv"
    if cache.exists():
        print(f"{mapping}: using cached {cache}")
        return pd.read_csv(cache, keep_default_na=False)

    partial = WORK / f"A02_capad_{mapping.lower()}.partial.csv"
    done = set()
    if partial.exists():
        previous = pd.read_csv(partial, keep_default_na=False)
        done = set(zip(previous["TYPE"], previous["NAME"]))
        print(f"{mapping}: resuming protected areas, {len(done)} already done")
    else:
        with open(partial, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["TYPE", "NAME", "Class_id", "Pixels", "Area_m2"])

    ds, band, gt, nx, ny, block_height = raster_info(tif)
    areas = row_areas_m2(gt, ny)
    start = time.perf_counter()
    with open(partial, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for pa in tqdm(capad.itertuples(), total=len(capad), desc=f"{mapping} protected areas", unit="area"):
            if (pa.TYPE, pa.NAME) in done:
                continue
            area, pixels = protected_area_sums(band, gt, nx, ny, block_height, areas, pa.geometry)
            # Every palette class is written so that each protected area leaves a resume marker.
            ids = sorted(set(palette) | {int(c) for c in np.flatnonzero(pixels)})
            writer.writerows([pa.TYPE, pa.NAME, cid, int(pixels[cid]), repr(float(area[cid]))] for cid in ids)
            f.flush()
    print(f"{mapping}: protected areas took {(time.perf_counter() - start) / 60:.1f} min")
    os.replace(partial, cache)
    return pd.read_csv(cache, keep_default_na=False)


# ---------------------------------------------------------------- outputs and checks

def class_ids(palette, areas):
    """Palette classes, then any out-of-palette classes with a non-zero area."""
    return list(palette) + sorted(c for c, a in areas.items() if c not in palette and a > 0)


def class_rows(base, mapping, palette, areas):
    rows = []
    for cid in class_ids(palette, areas):
        rows.append({**base, "Mapping": mapping, "Class_id": cid,
                     "Class_name": palette.get(cid, UNKNOWN),
                     "Area_km2": f"{areas.get(cid, 0.0) / 1e6:.6f}"})
    return rows


def area_dict(df):
    return dict(zip(df["Class_id"].astype(int), df["Area_m2"].astype(float)))


def mapped_area(palette, areas):
    return sum(a for c, a in areas.items() if c in palette)


def build_outputs(palettes, regions, main, capad_sums):
    rows, checks = [], []
    blank = {"Region_group": "", "Region_type": ""}

    dataset_areas = {}
    for mapping, df in main.items():
        dataset_areas[mapping] = area_dict(df[df["Regionalisation"] == "dataset"])
        rows += class_rows({"Regionalisation": DATASET, **blank, "Region_name": "All"},
                           mapping, palettes[mapping], dataset_areas[mapping])
        unknown = df[(df["Regionalisation"] == "dataset") & ~df["Class_id"].isin(list(palettes[mapping]))]
        unknown_km2 = unknown["Area_m2"].sum() / 1e6
        checks.append({"Check": "Unknown class area (km2)", "Mapping": mapping, "Regionalisation": DATASET,
                       "Value": unknown_km2, "Tolerance": 0.0, "Passed": unknown_km2 == 0,
                       "Detail": f"{int(unknown['Pixels'].sum())} pixels in classes "
                                 f"{sorted(unknown['Class_id'].tolist())}"})
        checks.append({"Check": "Pixel area formula vs pyproj.Geod (relative)", "Mapping": mapping,
                       "Regionalisation": DATASET, "Value": float(df["Row_area_check"].iloc[0]),
                       "Tolerance": TOLERANCE, "Passed": True, "Detail": "first, middle and last rows"})

    for slug in ZONED:
        cfg, gdf = REGIONALISATIONS[slug], regions[slug]
        zone_areas = {m: {z: area_dict(g) for z, g in df[df["Regionalisation"] == slug].groupby("Zone")}
                      for m, df in main.items()}
        for _, region in gdf.iterrows():
            z = int(region["zone"])
            if not any(mapped_area(palettes[m], zone_areas[m].get(z, {})) > 0 for m in main):
                continue
            base = {"Regionalisation": cfg["name"],
                    "Region_group": region["region"] if slug == "analysis-region" else "",
                    "Region_type": "", "Region_name": region[cfg["identity"][-1]]}
            for m in main:
                rows += class_rows(base, m, palettes[m], zone_areas[m].get(z, {}))
        for m in main:
            rows += class_rows({"Regionalisation": cfg["name"], **blank, "Region_name": OUTSIDE},
                               m, palettes[m], zone_areas[m].get(0, {}))

        for m in main:
            dataset_total = sum(dataset_areas[m].values())
            summed = {}
            for areas in zone_areas[m].values():
                for c, a in areas.items():
                    summed[c] = summed.get(c, 0.0) + a
            classes = set(summed) | set(dataset_areas[m])
            worst_class = max(classes, key=lambda c: abs(summed.get(c, 0.0) - dataset_areas[m].get(c, 0.0)))
            error = abs(summed.get(worst_class, 0.0) - dataset_areas[m].get(worst_class, 0.0)) / dataset_total
            checks.append({"Check": "Regions plus outside equal dataset (relative)", "Mapping": m,
                           "Regionalisation": cfg["name"], "Value": error, "Tolerance": TOLERANCE,
                           "Passed": error <= TOLERANCE, "Detail": f"worst class {worst_class}"})

    cfg, capad = REGIONALISATIONS["capad"], regions["capad"]
    pa_areas = {m: {key: area_dict(g) for key, g in df.groupby(["TYPE", "NAME"])}
                for m, df in capad_sums.items()}
    for pa in capad.itertuples():
        key = (pa.TYPE, pa.NAME)
        if not any(mapped_area(palettes[m], pa_areas[m].get(key, {})) > 0 for m in capad_sums):
            continue
        base = {"Regionalisation": cfg["name"], "Region_group": "", "Region_type": pa.TYPE,
                "Region_name": pa.NAME}
        for m in capad_sums:
            rows += class_rows(base, m, palettes[m], pa_areas[m].get(key, {}))
    for m in capad_sums:
        dataset_total = sum(dataset_areas[m].values())
        worst, detail = -math.inf, ""
        for key, areas in pa_areas[m].items():
            for c, a in areas.items():
                excess = (a - dataset_areas[m].get(c, 0.0)) / dataset_total
                if excess > worst:
                    worst, detail = excess, f"{key[1]} - {key[0]}, class {c}"
        checks.append({"Check": "Protected area class area minus dataset class area (relative)",
                       "Mapping": m, "Regionalisation": cfg["name"], "Value": worst,
                       "Tolerance": TOLERANCE, "Passed": worst <= TOLERANCE, "Detail": f"largest: {detail}"})

    columns = ["Regionalisation", "Region_group", "Region_type", "Region_name",
               "Mapping", "Class_id", "Class_name", "Area_km2"]
    return pd.DataFrame(rows, columns=columns), pd.DataFrame(checks)


# ---------------------------------------------------------------- main

def main():
    for mapping, tif in MAPPINGS.items():
        if not tif.exists():
            sys.exit(f"{mapping} raster not found: {tif}\nDownload the published data from the eAtlas "
                     f"share ({EATLAS_SHARE}) into data/out/. The share has the same folder structure.")
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    palettes = {m: read_palette(tif) for m, tif in MAPPINGS.items()}
    extents = []
    for tif in MAPPINGS.values():
        _ds, _band, gt, nx, ny, _ = raster_info(tif)
        extents.append((gt[0], gt[3] + gt[5] * ny, gt[0] + gt[1] * nx, gt[3]))
    bbox = (min(e[0] for e in extents), min(e[1] for e in extents),
            max(e[2] for e in extents), max(e[3] for e in extents))

    regions = {slug: prepare_regions(slug, cfg, bbox) for slug, cfg in REGIONALISATIONS.items()}
    main_sums = {m: main_pass(m, tif, {s: regions[s] for s in ZONED}) for m, tif in MAPPINGS.items()}
    capad_sums = {m: capad_pass(m, tif, palettes[m], regions["capad"]) for m, tif in MAPPINGS.items()}

    table, checks = build_outputs(palettes, regions, main_sums, capad_sums)
    write_csv_atomic(table, OUT_CSV)
    write_csv_atomic(checks, CHECKS_CSV)
    print(f"\nWrote {OUT_CSV} ({len(table)} rows)")

    print(f"\nChecks (also in {CHECKS_CSV}):")
    for c in checks.itertuples():
        status = "ok  " if c.Passed else "WARN"
        print(f"  {status} {c.Mapping:10s} {c.Regionalisation:40s} {c.Check}: {c.Value:.3g} ({c.Detail})")
    if not checks["Passed"].all():
        print("\nWARNING: some checks failed. Inspect the outputs before using them.")

    print("\nMapped area by mapping:")
    for m in MAPPINGS:
        dataset = table[(table["Regionalisation"] == DATASET) & (table["Mapping"] == m)
                        & (table["Class_name"] != UNKNOWN)]
        print(f"  {m:10s} {dataset['Area_km2'].astype(float).sum():12,.2f} km2")


if __name__ == "__main__":
    main()
