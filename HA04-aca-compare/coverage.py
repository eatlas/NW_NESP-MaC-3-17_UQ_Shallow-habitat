"""Estimate how much of the UQ mapped area is also mapped by ACA, by IMCRA meso-scale bioregion."""

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from osgeo import gdal

from compare import BASE, LABELS

AUTHALIC_RADIUS_KM = 6371.0072
STRIP_ROWS = 1024


def grid(path, step):
    # Overviews ignore NoData when aggregating, which inflates sparse habitat area, so read full-resolution pixels instead.
    dataset = gdal.OpenEx(str(path), gdal.OF_RASTER, open_options=["OVERVIEW_LEVEL=NONE"])
    # This grid assumes the UQ inputs are north-up longitude/latitude rasters.
    x0, dx, _, y0, _, dy = dataset.GetGeoTransform()
    # Keep complete step-sized cells only; any partial right/bottom strip is omitted.
    shape = (dataset.RasterYSize // step, dataset.RasterXSize // step)
    return dataset, shape, (x0, dx * step, 0, y0, 0, dy * step)


def rasterise(source, destination, shape, transform, data_type, attribute=None):
    target = gdal.GetDriverByName("GTiff").Create(str(destination), shape[1], shape[0], 1, data_type, ["COMPRESS=DEFLATE", "TILED=YES", "BIGTIFF=YES"])
    target.SetGeoTransform(transform)
    target.SetProjection("EPSG:4326")
    for path in source:
        # Burn either a bioregion ID or a binary coverage flag onto the same sampling grid.
        layer_options = dict(attribute=attribute) if attribute else dict(burnValues=[1])
        gdal.Rasterize(target, str(path), **layer_options)
    target = None


def row_areas(transform, rows):
    # Integrate each longitude/latitude cell on an equal-area sphere, in square kilometres.
    # Cell area varies with latitude but is constant across each north-up raster row.
    top = np.radians(transform[3] + transform[5] * rows)
    bottom = np.radians(transform[3] + transform[5] * (rows + 1))
    return AUTHALIC_RADIUS_KM ** 2 * np.radians(transform[1]) * np.abs(np.sin(top) - np.sin(bottom))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=BASE / "data")
    parser.add_argument("--step", type=int, default=8, help="Sample every nth native UQ pixel in each direction (8 is about 80 m).")
    options = parser.parse_args()
    gdal.UseExceptions()
    data = options.data_dir.resolve()
    working = BASE / "working" / "HA04-aca-compare"
    working.mkdir(parents=True, exist_ok=True)
    output = data / "out" / "stats" / "HA04-aca-compare"
    output.mkdir(parents=True, exist_ok=True)
    imcra = gpd.read_file(data / "in-3p" / "IMCRA-v4-0-Meso-Bioregions" / "IMCRA-v4-Mesoscale-Bioregions.shp").to_crs(4326)
    # Reserve zero for cells outside the bioregions; positive IDs link back to their names.
    imcra["zone"] = np.arange(1, len(imcra) + 1, dtype=np.int32)
    imcra[["zone", "MESO_NAME", "geometry"]].to_file(working / "imcra.gpkg", driver="GPKG")
    names = dict(zip(imcra.zone, imcra.MESO_NAME)) | {0: "Outside IMCRA meso-scale bioregions"}
    rows = []
    for objective in LABELS:
        dataset, shape, transform = grid(data / "out" / objective / f"NW_NESP-MaC-3-17_UQ_Shallow-habitat_{objective.title()}_2025.tif", options.step)
        band = dataset.GetRasterBand(1)
        nodata = band.GetNoDataValue()
        print(f"{objective}: sampling grid {shape[1]} x {shape[0]}, {abs(transform[1]) * 111.32:.3f} km at the equator", flush=True)
        aca_path, zone_path = working / f"aca-{objective}.tif", working / f"imcra-{objective}.tif"
        folder = "Benthic-Map" if objective == "benthic" else "Geomorphic-Map"
        rasterise([data / "in-3p" / "AllenCoralAtlas" / area / folder / f"{objective}.gpkg" for area in ["WA", "Timor-Arafura"]], aca_path, shape, transform, gdal.GDT_Byte)
        rasterise([working / "imcra.gpkg"], zone_path, shape, transform, gdal.GDT_Int16, attribute="zone")
        aca_dataset, zone_dataset = gdal.Open(str(aca_path)), gdal.Open(str(zone_path))
        aca_band, zone_band = aca_dataset.GetRasterBand(1), zone_dataset.GetRasterBand(1)
        totals = np.zeros((len(names) + 1, 3))
        # Process strips to bound memory use instead of loading the whole regional mosaic.
        for start in range(0, shape[0], STRIP_ROWS):
            height = min(STRIP_ROWS, shape[0] - start)
            # Select native pixels by nearest neighbour, not an average of habitat classes.
            # Each selected pixel represents its coarser sampling cell, so areas are estimates.
            uq = band.ReadAsArray(0, start * options.step, shape[1] * options.step, height * options.step, buf_xsize=shape[1], buf_ysize=height, resample_alg=gdal.GRIORA_NearestNeighbour)
            uq_mapped = uq > 0 if nodata is None else (uq > 0) & (uq != nodata)
            aca = aca_band.ReadAsArray(0, start, shape[1], height) > 0
            if not (uq_mapped.any() or aca.any()):
                continue
            zones = zone_band.ReadAsArray(0, start, shape[1], height)
            areas = np.broadcast_to(row_areas(transform, np.arange(start, start + height))[:, None], uq.shape)
            # Accumulate area by bioregion for UQ coverage, ACA coverage and their intersection.
            for column, mask in enumerate([uq_mapped, aca, uq_mapped & aca]):
                totals[:, column] += np.bincount(zones[mask], weights=areas[mask], minlength=len(totals))
        for zone in np.flatnonzero(totals[:, 0] + totals[:, 1]):
            uq_km2, aca_km2, both_km2 = totals[zone]
            rows.append(dict(objective=objective, region=names[zone], uq_km2=uq_km2, aca_km2=aca_km2, both_km2=both_km2,
                             uq_with_aca_pct=100 * both_km2 / uq_km2 if uq_km2 else np.nan, aca_outside_uq_km2=aca_km2 - both_km2))
        uq_km2, aca_km2, both_km2 = totals.sum(axis=0)
        rows.append(dict(objective=objective, region="All", uq_km2=uq_km2, aca_km2=aca_km2, both_km2=both_km2, uq_with_aca_pct=100 * both_km2 / uq_km2, aca_outside_uq_km2=aca_km2 - both_km2))
    result = pd.DataFrame(rows)
    result.to_csv(working / "coverage-area.csv", index=False)
    result[["objective", "region", "uq_km2", "uq_with_aca_pct"]].to_csv(output / "coverage-area.csv", index=False)
    # Keep all regions in the CSV; the publication table suppresses very small UQ areas.
    table = result[(result.uq_km2 >= 1) | (result.region == "All")].pivot(index="region", columns="objective", values=["uq_km2", "uq_with_aca_pct"])
    table = table.sort_values(("uq_km2", "benthic"), ascending=False)
    lines = ["| IMCRA meso-scale bioregion | UQ benthic (km²) | Also mapped by ACA (%) | UQ geomorphic (km²) | Also mapped by ACA (%) |", "|:---|---:|---:|---:|---:|"]
    ordered = [region for region in table.index if region != "All"] + ["All"]
    for region in ordered:
        item = table.loc[region]
        cells = [f"{item[(measure, objective)]:,.0f}" if measure == "uq_km2" else f"{item[(measure, objective)]:.0f}" for objective in LABELS for measure in ["uq_km2", "uq_with_aca_pct"]]
        lines.append(f"| {'**All**' if region == 'All' else region} | " + " | ".join(cell.replace("nan", "-") for cell in cells) + " |")
    caption = "**Table 1. UQ mapped habitat area and the percentage also mapped by ACA, by IMCRA v4.0 meso-scale bioregion.** Areas were estimated from a systematic sample of native UQ pixels, every eighth pixel in each direction by default (about 80 m spacing), with latitude-dependent spherical cell areas. The geomorphic area includes the UQ Deep class on deep reef banks. Coverage indicates the presence of ACA mapping, not agreement between habitat classes. Rows with at least 1 km² of UQ mapping in either classification are shown, ordered by UQ benthic area; All includes every bioregion. Areas and percentages are rounded to whole numbers, so a displayed zero can represent a small nonzero value. Script: HA04-aca-compare/coverage.py\n"
    (output / "coverage-area-table.md").write_text(caption + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
