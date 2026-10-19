"""Compare final UQ and ACA maps outside buffered published ACA reference areas."""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from osgeo import gdal, ogr, osr


ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
REGIONS = {"gulf": "Gulf", "nwest": "North West", "offshore": "Offshore", "sharkbay": "Shark Bay", "west": "West"}
# ACA covers only a thin strip of the outer Shark Bay coast, so a regional comparison would be misleading.
EXCLUDED_REGIONS = {"Shark Bay"}
LABELS = {
    "benthic": {11: "Sand", 12: "Rubble", 13: "Rock", 14: "Seagrass", 15: "Coral/Algae", 18: "Microalgal Mats"},
    "geomorphic": {11: "Shallow Lagoon", 12: "Deep Lagoon", 13: "Inner Reef Flat", 14: "Outer Reef Flat", 15: "Reef Crest", 16: "Terrestrial Reef Flat", 21: "Sheltered Reef Slope", 22: "Reef Slope", 23: "Plateau", 24: "Back Reef Slope"},
}
ACA_CODES = {objective: {label: code for code, label in labels.items()} for objective, labels in LABELS.items()}
ACA_CODES["geomorphic"]["Patch Reefs"] = 126
REFERENCE_SOURCES = {
    "WA-benthic": ("20201217_WEA_Benthic", "10.6084/m9.figshare.14622759.v1"),
    "WA-geomorphic": ("20201217_WEA_Geomorphic", "10.6084/m9.figshare.14622750.v1"),
    "Timor-benthic": ("20200721_TIS_Benthic", "10.6084/m9.figshare.14120894.v1"),
    "Timor-geomorphic": ("20200721_TIS_Geomorphic", "10.6084/m9.figshare.14120891.v1"),
}


def progress(stage, state, note):
    timestamp = datetime.now(timezone.utc).isoformat()
    temporary = ROOT / "status.json.tmp"
    temporary.write_text(json.dumps(dict(stage=stage, state=state, note=note, updatedAt=timestamp), indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, ROOT / "status.json")
    with (ROOT / "progress.md").open("a", encoding="utf-8") as stream:
        stream.write(f"{timestamp} {note}\n")


def inputs(data):
    files = {}
    for name, (stem, _) in REFERENCE_SOURCES.items():
        for extension in ["shp", "shx", "dbf", "prj"]:
            files[f"reference/{name}/{extension}"] = data / "in-3p-mirror" / "ACA-ref" / name / f"{stem}.{extension}"
    for key in REGIONS:
        for objective in LABELS:
            token = "benthic" if objective == "benthic" else "geo"
            matches = sorted((data / "out" / "reference_training_csv").glob(f"{key}_{token}_training*.csv"))
            if len(matches) != 1:
                raise FileNotFoundError(f"Expected one {key}/{objective} training CSV; found {len(matches)} in {data / 'out' / 'reference_training_csv'}")
            files[f"training/{key}/{objective}"] = matches[0]
    for objective in LABELS:
        files[f"uq/{objective}"] = data / "out" / objective / f"NW_NESP-MaC-3-17_UQ_Shallow-habitat_{objective.title()}_2025.tif"
        for area in ["WA", "Timor-Arafura"]:
            folder = "Benthic-Map" if objective == "benthic" else "Geomorphic-Map"
            files[f"aca/{area}/{objective}"] = data / "in-3p" / "AllenCoralAtlas" / area / folder / f"{objective}.gpkg"
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing analysis inputs. Use the supplied data bundle or follow README.md, 'Mirrored third-party data and manual downloads', for ACA references; obtain the required maps and training CSVs.\n" + "\n".join(missing))
    return files


def fingerprint(files):
    result = {}
    for key, path in files.items():
        item = dict(bytes=path.stat().st_size, mtime_ns=path.stat().st_mtime_ns)
        # Hash smaller inputs; use size and modification time for the large map files.
        if path.suffix not in {".gpkg", ".tif"}:
            with path.open("rb") as stream:
                item["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        result[key] = item
    return result


def coordinates(frame, target):
    source = osr.SpatialReference()
    source.ImportFromEPSG(4326)
    # Keep longitude/x first, even when the CRS formally specifies latitude first.
    source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    destination = target.Clone()
    destination.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(source, destination)
    return np.asarray(transform.TransformPoints(list(zip(frame.longitude, frame.latitude))))[:, :2]


def raster_sample(path, frame):
    # frame contains one row per reference sample point, with WGS84 longitude and latitude.
    dataset = gdal.Open(str(path))
    band = dataset.GetRasterBand(1)
    locations = coordinates(frame, dataset.GetSpatialRef())
    inverse = gdal.InvGeoTransform(dataset.GetGeoTransform())
    # Transform reference point locations into zero-based indices of their containing pixels.
    columns = np.floor(inverse[0] + locations[:, 0] * inverse[1] + locations[:, 1] * inverse[2]).astype(np.int64)
    rows = np.floor(inverse[3] + locations[:, 0] * inverse[4] + locations[:, 1] * inverse[5]).astype(np.int64)
    inside = (columns >= 0) & (rows >= 0) & (columns < dataset.RasterXSize) & (rows < dataset.RasterYSize)
    values = np.zeros(len(frame), dtype=np.int32)
    width, height = band.GetBlockSize()
    # Group points by storage block so each required block is read only once.
    # position refers to array order, not the possibly non-consecutive DataFrame index.
    blocks = pd.DataFrame(dict(position=np.flatnonzero(inside), block_col=columns[inside] // width, block_row=rows[inside] // height))
    for (block_col, block_row), group in blocks.groupby(["block_col", "block_row"]):
        positions = group.position.to_numpy()
        left, top = int(block_col * width), int(block_row * height)
        # Edge blocks may be smaller than the raster's nominal storage block size.
        window_width, window_height = min(width, dataset.RasterXSize - left), min(height, dataset.RasterYSize - top)
        window = band.ReadAsArray(left, top, window_width, window_height)
        mask = band.GetMaskBand().ReadAsArray(left, top, window_width, window_height)
        # Convert whole-raster indices to indices within this block's array.
        sampled = window[rows[positions] - top, columns[positions] - left].astype(np.int32)
        sampled[mask[rows[positions] - top, columns[positions] - left] == 0] = 0
        values[positions] = sampled
    nodata = band.GetNoDataValue()
    # Outside extent, masked pixels and explicit NoData all use zero for no valid class.
    if nodata is not None:
        values[values == nodata] = 0
    return values, rows, columns, inside


def polygon_sample(paths, frame, objective):
    # Sets collapse repeated polygons of the same class without hiding class conflicts.
    matches = [set() for _ in range(len(frame))]
    for path in paths:
        dataset = ogr.Open(str(path))
        layer = dataset.GetLayer(0)
        locations = coordinates(frame, layer.GetSpatialRef())
        minimum_x, maximum_x, minimum_y, maximum_y = layer.GetExtent()
        candidates = np.flatnonzero((locations[:, 0] >= minimum_x) & (locations[:, 0] <= maximum_x) & (locations[:, 1] >= minimum_y) & (locations[:, 1] <= maximum_y))
        for position in candidates:
            point = ogr.Geometry(ogr.wkbPoint)
            point.AddPoint_2D(*locations[position])
            # Use a spatial filter for candidates, then test exact geometry intersection.
            # Intersects includes boundaries, where different classes may both match.
            layer.SetSpatialFilter(point)
            for feature in layer:
                if feature.GetGeometryRef().Intersects(point):
                    label = feature.GetField("class")
                    if label not in ACA_CODES[objective]:
                        raise ValueError(f"Unrecognised ACA class {label!r}: {path}")
                    matches[position].add(ACA_CODES[objective][label])
        print(f"Sampled {objective} ACA {path.parent.parent.name}", flush=True)
    # One distinct class is usable; -2 means conflicting classes and zero means no match.
    return np.array([next(iter(found)) if len(found) == 1 else (-2 if found else 0) for found in matches], dtype=np.int32)


def harmonise(values, objective):
    # Merge UQ benthic subclasses into shared classes for both references and predictions.
    return values.replace({16: 15, 17: 15, 19: 14}) if objective == "benthic" else values.copy()


def select_pixels(frame):
    keys = ["region", "objective", "uq_row", "uq_col"]
    frame = frame.copy()
    # Within each region/objective, reject every row in a pixel with conflicting labels.
    # Otherwise retain the first reference row per pixel, provided it is inside the raster.
    frame["conflicting_pixel"] = frame.groupby(keys).reference.transform("nunique") > 1
    frame["unique_pixel"] = ~frame.duplicated(keys) & ~frame.conflicting_pixel & frame.uq_inside_extent
    return frame


def sample_inputs(files):
    groups = []
    for key, path in files.items():
        if not key.startswith("training/"):
            continue
        _, region, objective = key.split("/")
        original = pd.read_csv(path, dtype={"system:index": str})
        # Earth Engine CSV exports store each point's GeoJSON in the .geo field.
        geometry = original[".geo"].map(json.loads)
        if not geometry.map(lambda item: item["type"] == "Point").all():
            raise ValueError(f"Non-point training geometry in {path}")
        locations = geometry.map(lambda item: item["coordinates"])
        group = pd.DataFrame(dict(source_file=path.name, source_row=np.arange(len(original)), source_id=original["system:index"], region=REGIONS[region], objective=objective,
                                  reference_raw=original.class_num.astype(int), longitude=locations.str[0], latitude=locations.str[1]))
        if not (group.longitude.between(-180, 180) & group.latitude.between(-90, 90)).all():
            raise ValueError(f"Invalid coordinates in {path}")
        groups.append(group)
    frame = pd.concat(groups, ignore_index=True)
    for objective in LABELS:
        indices = frame.index[frame.objective == objective]
        group = frame.loc[indices]
        print(f"Sampling {objective}: {len(group)} references", flush=True)
        values, rows, columns, inside = raster_sample(files[f"uq/{objective}"], group)
        known = {0, 11, 12, 13, 14, 15, 16, 17, 18, 19} if objective == "benthic" else {0, 2, 10, 11, 12, 13, 14, 15, 16, 21, 22, 23, 24, 26, 27}
        if not set(values) <= known or not set(group.reference_raw) <= known - {0}:
            raise ValueError(f"Unrecognised {objective} codes in UQ map or references")
        frame.loc[indices, "uq_raw"] = values
        frame.loc[indices, "uq_row"] = rows
        frame.loc[indices, "uq_col"] = columns
        frame.loc[indices, "uq_inside_extent"] = inside
        frame.loc[indices, "aca"] = polygon_sample([files[f"aca/{area}/{objective}"] for area in ["WA", "Timor-Arafura"]], group, objective)
        frame.loc[indices, "reference"] = harmonise(group.reference_raw, objective)
        # Preserve the subset's original index so pandas aligns values to the correct rows.
        frame.loc[indices, "uq"] = harmonise(pd.Series(values, index=indices), objective)
    for column in ["reference", "uq_raw", "uq", "aca", "uq_row", "uq_col"]:
        frame[column] = frame[column].astype(np.int64)
    frame["uq_inside_extent"] = frame.uq_inside_extent.astype(bool)
    return select_pixels(frame)


def reference_parts(files):
    parts, inventory = [], []
    for name, (_, doi) in REFERENCE_SOURCES.items():
        path = files[f"reference/{name}/shp"]
        original = gpd.read_file(path)
        if original.crs is None or original.empty or original.geometry.isna().any():
            raise ValueError(f"Empty reference layer or missing geometry/CRS: {path}")
        repaired = original.geometry.make_valid()
        # Split multipart reference areas before selecting a local projection for buffering.
        polygons = gpd.GeoSeries(repaired, crs=original.crs).explode(index_parts=False).reset_index(drop=True)
        if not polygons.geom_type.isin(["Polygon", "MultiPolygon"]).all():
            raise ValueError(f"Reference geometry repair produced non-polygons: {path}")
        polygons = polygons.to_crs(4326)
        inventory.append(dict(dataset=name, doi=doi, features=len(original), polygon_parts=len(polygons), repaired_features=int((~original.geometry.is_valid).sum()), bounds=polygons.total_bounds.tolist()))
        parts.extend(polygons.to_list())
    return gpd.GeoSeries(parts, crs=4326), inventory


def exclusion_mask(points, polygons, buffer_m):
    if buffer_m < 0:
        raise ValueError("Buffer distance must be non-negative")
    # Choose WGS84 UTM by each component's centroid so buffer distances are in metres.
    centroids = shapely.centroid(polygons.to_numpy())
    zones = np.clip(((shapely.get_x(centroids) + 180) // 6 + 1).astype(int), 1, 60)
    north = shapely.get_y(centroids) >= 0
    codes = np.where(north, 32600, 32700) + zones
    excluded = np.zeros(len(points), dtype=bool)
    for code in np.unique(codes):
        projected = polygons[codes == code].to_crs(int(code))
        buffered = projected.buffer(buffer_m, quad_segs=32) if buffer_m else projected
        geographic = buffered.to_crs(4326)
        tree = shapely.STRtree(geographic.to_numpy())
        # Query pairs contain point indices first and polygon indices second.
        # Mark points intersecting any reference area, across both regions/classifications.
        intersections = tree.query(points.to_numpy(), predicate="intersects")
        excluded[np.unique(intersections[0])] = True
    return excluded


def class_metrics(reference, prediction):
    matrix = pd.crosstab(pd.Series(np.asarray(reference), name="reference"), pd.Series(np.asarray(prediction), name="prediction"))
    rows = []
    # Include prediction-only classes so unmatched mapped classes still count as errors.
    for code in sorted(set(reference) | set(prediction)):
        correct = int(((reference == code) & (prediction == code)).sum())
        reference_n, mapped_n = int((reference == code).sum()), int((prediction == code).sum())
        rows.append(dict(class_num=int(code), reference_n=reference_n, mapped_n=mapped_n, correct=correct,
                         producer_agreement_pct=100 * correct / reference_n if reference_n else np.nan,
                         user_agreement_pct=100 * correct / mapped_n if mapped_n else np.nan))
    return matrix, rows


def bootstrap(group, block_m, replicates):
    if group.empty:
        return dict(blocks=0, low_pp=np.nan, high_pp=np.nan)
    # Australian Albers gives a common metre-based grid for grouping nearby references.
    locations = gpd.GeoSeries(gpd.points_from_xy(group.longitude, group.latitude), crs=4326).to_crs(3577)
    # Per-point differences are +1 (only UQ correct), -1 (only ACA), or 0 (both/neither).
    counts = pd.DataFrame(dict(block_x=np.floor(locations.x / block_m).astype(int), block_y=np.floor(locations.y / block_m).astype(int),
                               difference=(group.reference.to_numpy() == group.uq.to_numpy()).astype(int) - (group.reference.to_numpy() == group.aca.to_numpy()).astype(int)))
    blocks = counts.groupby(["block_x", "block_y"]).difference.agg(["sum", "count"])
    if len(blocks) < 2:
        return dict(blocks=len(blocks), low_pp=np.nan, high_pp=np.nan)
    generator = np.random.default_rng(42)
    estimates = []
    for _ in range(replicates):
        # Resample occupied blocks with replacement, retaining paired observations together.
        # Dividing pooled totals keeps the estimate point-weighted, not block-weighted.
        draw = generator.integers(0, len(blocks), len(blocks))
        estimates.append(100 * blocks["sum"].to_numpy()[draw].sum() / blocks["count"].to_numpy()[draw].sum())
    low, high = np.quantile(estimates, [0.025, 0.975])
    return dict(blocks=len(blocks), low_pp=float(low), high_pp=float(high))


def summarise(frame, output, replicates):
    summary, classes, confusion, uncertainty = [], [], [], []
    for buffer_m in [0, 50, 100]:
        for (region, objective), raw in frame.groupby(["region", "objective"]):
            if region in EXCLUDED_REGIONS:
                continue
            unique = raw[raw.unique_pixel]
            # Only shared reference classes are eligible; mapped-only classes remain errors.
            supported = unique[unique.reference.isin(LABELS[objective])]
            retained = supported[~supported[f"excluded_{buffer_m}m"]]
            uq_valid, aca_valid = retained.uq > 0, retained.aca > 0
            # Compare products on exactly the same points; report unpaired coverage separately.
            paired = retained[uq_valid & aca_valid]
            tags = dict(buffer_m=buffer_m, region=region, objective=objective)
            reference = paired.reference.to_numpy()
            uq_correct = reference == paired.uq.to_numpy()
            aca_correct = reference == paired.aca.to_numpy()
            uq_pct = 100 * uq_correct.mean() if len(paired) else np.nan
            aca_pct = 100 * aca_correct.mean() if len(paired) else np.nan
            summary.append(dict(**tags, input_n=len(raw), conflicting_rows=int(raw.conflicting_pixel.sum()), unique_pixel_n=len(unique),
                                unsupported_reference_n=len(unique) - len(supported), eligible_n=len(supported), excluded_n=len(supported) - len(retained), retained_n=len(retained),
                                uq_only_n=int((uq_valid & ~aca_valid).sum()), aca_only_n=int((~uq_valid & aca_valid).sum()), neither_n=int((~uq_valid & ~aca_valid).sum()),
                                ambiguous_aca_n=int((retained.aca == -2).sum()), paired_n=len(paired), uq_agreement_pct=uq_pct, aca_agreement_pct=aca_pct, difference_pp=uq_pct - aca_pct,
                                uq_only_correct=int((uq_correct & ~aca_correct).sum()), aca_only_correct=int((~uq_correct & aca_correct).sum())))
            for product in ["uq", "aca"]:
                matrix, details = class_metrics(reference, paired[product].to_numpy())
                classes.extend(dict(**tags, product=product, class_name=LABELS[objective].get(detail["class_num"], "Unmatched mapped class"), **detail) for detail in details)
                confusion.extend(dict(**tags, product=product, reference=int(reference_code), prediction=int(prediction_code), n=int(matrix.loc[reference_code, prediction_code]))
                                 for reference_code in matrix.index for prediction_code in matrix.columns)
            for block_m in [1000, 5000, 10000]:
                uncertainty.append(dict(**tags, block_m=block_m, replicates=replicates, **bootstrap(paired, block_m, replicates)))
    result = pd.DataFrame(summary)
    checks = result.paired_n + result.uq_only_n + result.aca_only_n + result.neither_n == result.retained_n
    if not checks.all():
        raise AssertionError("Coverage counts do not partition the retained references")
    populated = result[result.paired_n > 0]
    # Both-correct and both-wrong pairs cancel, leaving only the discordant pairs.
    if not np.allclose(populated.difference_pp, 100 * (populated.uq_only_correct - populated.aca_only_correct) / populated.paired_n):
        raise AssertionError("Paired effect does not match discordant counts")
    result.to_csv(output / "summary.csv", index=False)
    pd.DataFrame(classes).to_csv(output / "classes.csv", index=False)
    pd.DataFrame(confusion).to_csv(output / "confusion.csv", index=False)
    pd.DataFrame(uncertainty).to_csv(output / "uncertainty.csv", index=False)
    frame.to_csv(output / "points.csv", index=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=BASE / "data")
    parser.add_argument("--check-inputs", action="store_true", help="Check required files without sampling or writing statistics.")
    parser.add_argument("--replicates", type=int, default=1999)
    options = parser.parse_args()
    if options.replicates < 99:
        parser.error("Use at least 99 bootstrap replicates")
    gdal.UseExceptions()
    ogr.UseExceptions()
    gdal.SetCacheMax(256 * 1024 * 1024)
    try:
        progress("inputs", "running", "Checking final maps, training references and four ACA reference polygon datasets.")
        files = inputs(options.data_dir.resolve())
        if options.check_inputs:
            print(f"PASS: {len(files)} required input files exist.")
            progress("inputs", "done", "All required comparison inputs exist; no map sampling was requested.")
            return
        output = BASE / "working" / "HA04-aca-compare"
        output.mkdir(parents=True, exist_ok=True)
        manifest = fingerprint(files)
        frame = sample_inputs(files)
        progress("sampling", "running", f"Sampled both final maps at {len(frame)} supplied UQ reference rows.")
        polygons, inventory = reference_parts(files)
        points = gpd.GeoSeries(gpd.points_from_xy(frame.longitude, frame.latitude), crs=4326)
        for buffer_m in [0, 50, 100]:
            frame[f"excluded_{buffer_m}m"] = exclusion_mask(points, polygons, buffer_m)
        # Increasing the exclusion buffer must never make an excluded point eligible again.
        if not ((frame.excluded_0m <= frame.excluded_50m) & (frame.excluded_50m <= frame.excluded_100m)).all():
            raise AssertionError("Exclusion masks are not nested")
        progress("exclusion", "running", "Applied the combined ACA reference exclusion with 0, 50 and 100 m buffers.")
        result = summarise(frame, output, options.replicates)
        # Recheck inputs before recording provenance to detect changes during the run.
        if manifest != fingerprint(files):
            raise RuntimeError("Inputs changed during analysis; rerun before using outputs")
        (output / "manifest.json").write_text(json.dumps(dict(created_utc=datetime.now(timezone.utc).isoformat(), files=manifest, reference_layers=inventory,
            code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), primary_buffer_m=50, buffer_crs="local WGS84 UTM by polygon component centroid", exclusion_sources="union of both classifications and both ACA reference regions",
            gdal=gdal.VersionInfo(), geopandas=gpd.__version__, shapely=shapely.__version__, numpy=np.__version__, pandas=pd.__version__, replicates=options.replicates, seed=42), indent=2) + "\n", encoding="utf-8")
        print(result[result.buffer_m == 50].to_string(index=False))
        progress("complete", "done", "Saved analysis and verification records to working/HA04-aca-compare; run make_tables.py and coverage.py for publication tables.")
    except Exception as error:
        progress("analysis", "blocked", str(error).splitlines()[0])
        raise


if __name__ == "__main__":
    main()