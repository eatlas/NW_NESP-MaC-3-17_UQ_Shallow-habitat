# TODO add processing to combine raw GeoTIFF files into a single dataset
"""Combine raw categorical GeoTIFF tiles into mosaics (benthic & geomorphic).

Workflow (per dataset):
 1. Locate input zip files in ../original/<folder>/ (relative to this script).
 2. Extract all .zip contents to a temp directory.
 3. Discover *.tif tiles, alphabetical order (deterministic priority).
 4. For each tile:
	  - Compute stats; if all pixels == 0 treat as blank and skip.
	  - Validate max value <= 255 and within expected class range.
	  - If datatype not Byte or nodata != 0, convert to 8-bit with nodata=0.
 5. Build VRT in the same priority ordering (first non-zero pixel wins because
	 zeros are nodata) using srcNodata=0.
 6. Translate VRT to final GeoTIFF with: Byte, nodata=0, LZW, tiling 256x256.
 7. Build overviews (MODE resampling) with LZW compression.
 8. Set metadata (doi, license).
 9. Clean up temp extracted / converted tiles (unless --keep-temp specified).

Exit codes: any validation or processing error aborts the run (non-zero exit).

CLI examples:
  Process both datasets (default):
	  python 01-combine-raw-geotiffs_gpt5.py
  Force reprocessing even if outputs exist:
	  python 01-combine-raw-geotiffs_gpt5.py --force
  Only benthic with 4 worker threads:
	  python 01-combine-raw-geotiffs_gpt5.py --dataset benthic --workers 4

Note:
 - Designed for large mosaics; operations are streaming via GDAL.
 - Assumes all source tiles share a common CRS / resolution / alignment.
 - Uses GDAL Python bindings (osgeo.gdal) plus zipfile & tqdm for progress.
"""

from __future__ import annotations

import argparse
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from osgeo import gdal
from tqdm import tqdm
import numpy as np

gdal.UseExceptions()


# ----------------------------- Configuration ---------------------------------

DATASET_CONFIG = {
	"benthic": {
		"input_folder": "Raw benthic raster files",
		"output_name": "NW_NESP-MaC-3-17_Shallow-habitat_Benthic.tif",
		"valid_min": 0,  # 0 = nodata
		"valid_max": 19,
	},
	"geomorphic": {
		"input_folder": "Raw geomorphic raster tiles",
		"output_name": "NW_NESP-MaC-3-17_Shallow-habitat_Geomorphic.tif",
		"valid_min": 0,  # 0 = nodata
		"valid_max": 27,
	},
}

DOI = "https://doi.org/10.26274/qeh6-p243"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/deed.en"

# Palette file names relative to the dataset input folder
PALETTE_FILES = {
	"benthic": "benthic_palette.csv",
	"geomorphic": "geo_palette.csv",
}


@dataclass
class TileInfo:
	path: Path
	is_blank: bool
	converted_path: Optional[Path] = None
	stats: Optional[tuple] = None  # (min, max, mean, std) if requested


# ---------------------------- Utility Functions ------------------------------

def human_time(seconds: float) -> str:
	if seconds < 60:
		return f"{seconds:.1f}s"
	m, s = divmod(seconds, 60)
	if m < 60:
		return f"{int(m)}m{s:04.1f}s"
	h, m = divmod(m, 60)
	return f"{int(h)}h{int(m)}m{s:02.0f}s"

def make_temp_dir(base: Path, name: str, force_clean: bool = False) -> Path:
	if base.exists() and force_clean:
		for p in base.rglob("*"):
			try:
				if p.is_file():
					p.unlink()
			except Exception:
				pass
	base.mkdir(parents=True, exist_ok=True)
	d = base / name
	d.mkdir(parents=True, exist_ok=True)
	return d

def unzip_all(zips: List[Path], dest: Path) -> None:
	for zp in tqdm(zips, desc="Unzipping", unit="zip"):
		with zipfile.ZipFile(zp, "r") as zf:
			for member in zf.namelist():
				# Skip directories and macOS resource fork files (._*)
				if member.endswith("/"):
					continue
				if Path(member).name.startswith("._"):
					continue
				target = dest / Path(member).name
				if not target.exists():
					zf.extract(member, dest)
					# If zipped inside a subfolder, move up one level
					extracted = dest / member
					if extracted.exists() and extracted.is_file():
						extracted.rename(target)
				# Cleanup nested path remainder if any
				nested_dir = dest / Path(member).parts[0]
				if nested_dir.is_dir() and nested_dir != dest:
					try:
						for f in nested_dir.iterdir():
							if f.is_file():
								f.rename(dest / f.name)
						nested_dir.rmdir()
					except Exception:
						pass

def compute_stats_exact(path: Path) -> tuple:
	ds = gdal.Open(str(path), gdal.GA_ReadOnly)
	if ds is None:
		raise RuntimeError(f"Failed to open {path}")
	band = ds.GetRasterBand(1)
	# exact stats: approx_ok=False, force=True
	stats = band.GetStatistics(False, True)
	ds = None
	return stats

def convert_to_byte_if_needed(tile: TileInfo, out_dir: Path) -> TileInfo:
	ds = gdal.Open(str(tile.path), gdal.GA_ReadOnly)
	band = ds.GetRasterBand(1)
	nodata = band.GetNoDataValue()
	dtype = band.DataType
	ds = None
	needs_convert = False
	# GDAL data type codes: GDT_Byte = 1
	if dtype != gdal.GDT_Byte:
		needs_convert = True
	if nodata not in (0, None):
		needs_convert = True
	if not needs_convert:
		return tile  # Use original

	out_dir.mkdir(parents=True, exist_ok=True)
	target = out_dir / tile.path.name
	translate_options = gdal.TranslateOptions(
		outputType=gdal.GDT_Byte,
		noData=0,
		creationOptions=[
			"TILED=YES",
			"COMPRESS=LZW",
			"BLOCKXSIZE=256",
			"BLOCKYSIZE=256",
			"BIGTIFF=NO",
		],
	)
	gdal.Translate(str(target), str(tile.path), options=translate_options)
	tile.converted_path = target
	return tile

def build_vrt(tile_paths: List[Path], vrt_path: Path) -> Path:
	vrt_options = gdal.BuildVRTOptions(srcNodata=0, VRTNodata=0)
	gdal.BuildVRT(str(vrt_path), [str(p) for p in tile_paths], options=vrt_options)
	return vrt_path

def translate_vrt_to_geotiff(vrt_path: Path, out_path: Path) -> None:
	translate_options = gdal.TranslateOptions(
		outputType=gdal.GDT_Byte,
		noData=0,
		creationOptions=[
			"TILED=YES",
			"COMPRESS=LZW",
			"BLOCKXSIZE=256",
			"BLOCKYSIZE=256",
			"BIGTIFF=NO",
		],
	)
	gdal.Translate(str(out_path), str(vrt_path), options=translate_options, callback=_gdal_progress, callback_data="Translate")

def build_overviews(path: Path, extra_metadata: Optional[dict] = None) -> None:
	ds = gdal.Open(str(path), gdal.GA_Update)
	if ds is None:
		raise RuntimeError(f"Cannot open output for overviews: {path}")
	xsize = ds.RasterXSize
	ysize = ds.RasterYSize
	max_dim = max(xsize, ysize)
	levels = []
	factor = 2
	while max_dim / factor > 512:  # stop when overview would be smaller than ~512
		levels.append(factor)
		factor *= 2
	if not levels:
		ds = None
		return
	# Set overview compression options via config options
	gdal.SetConfigOption("COMPRESS_OVERVIEW", "LZW")
	gdal.SetConfigOption("INTERLEAVE_OVERVIEW", "PIXEL")
	# Build overviews at dataset level (band.BuildOverviews not available in some GDAL builds)
	ds.BuildOverviews("MODE", levels, callback=_gdal_progress, callback_data="Overviews")
	ds.FlushCache()
	# Metadata
	ds.SetMetadataItem("doi", DOI)
	ds.SetMetadataItem("license", LICENSE_URL)
	if extra_metadata:
		for k, v in extra_metadata.items():
			if v is not None:
				ds.SetMetadataItem(k, v)
	ds = None

def validate_final(path: Path, valid_max: int) -> None:
	ds = gdal.Open(str(path), gdal.GA_ReadOnly)
	if ds is None:
		raise RuntimeError(f"Failed to open final mosaic {path}")
	band = ds.GetRasterBand(1)
	stats = band.GetStatistics(False, True)
	nodata = band.GetNoDataValue()
	if nodata != 0:
		raise RuntimeError("Output nodata is not 0")
	if stats[1] > valid_max:
		raise RuntimeError(f"Output contains values > configured max ({valid_max}): {stats[1]}")
	ds = None


def reclass_output(path: Path, valid_ids: set[int]) -> None:
	ds = gdal.Open(str(path), gdal.GA_Update)
	if ds is None:
		raise RuntimeError(f"Cannot open for reclass: {path}")
	band = ds.GetRasterBand(1)
	block_x, block_y = band.GetBlockSize()
	xsize = band.XSize
	ysize = band.YSize
	for y in range(0, ysize, block_y):
		rows = block_y if y + block_y <= ysize else ysize - y
		for x in range(0, xsize, block_x):
			cols = block_x if x + block_x <= xsize else xsize - x
			data = band.ReadAsArray(xoff=x, yoff=y, xsize=cols, ysize=rows)
			if data is None:
				continue
			mask_invalid = ~np.isin(data, list(valid_ids))
			if mask_invalid.any():
				data[mask_invalid] = 0
				band.WriteArray(data, xoff=x, yoff=y)
	band.FlushCache()
	ds.FlushCache()
	ds = None

def _gdal_progress(complete: float, message: str, data: str | None) -> int:  # pragma: no cover (progress UI)
	# Simple inline progress printing (not interfering with tqdm bars)
	percent = complete * 100
	sys.stdout.write(f"\r{data}: {percent:5.1f}%")
	sys.stdout.flush()
	if complete >= 1.0:
		sys.stdout.write("\n")
	return 1

# ------------------------------ Core Processing ------------------------------

def load_palette(kind: str, input_dir: Path) -> dict[int, str]:
	palette_path = input_dir / PALETTE_FILES[kind]
	mapping: dict[int, str] = {}
	if not palette_path.exists():
		print(f"[WARN] Palette file not found for {kind}: {palette_path}")
		return mapping
	try:
		import csv
		with palette_path.open("r", encoding="utf-8-sig") as f:
			reader = csv.DictReader(f)
			for row in reader:
				try:
					cid = int(row.get("class_id", "").strip())
				except Exception:
					continue
				name = row.get("class_name", "").strip()
				# Remove asterisk only if present (as per requirement)
				if name.endswith("*"):
					name = name[:-1]
				mapping[cid] = name
	except Exception as e:
		print(f"[WARN] Failed to parse palette {palette_path}: {e}")
	return mapping


def process_dataset(kind: str, args) -> None:
	cfg = DATASET_CONFIG[kind]
	script_dir = Path(__file__).resolve().parent
	input_dir = (script_dir / ".." / "original" / cfg["input_folder"]).resolve()
	if not input_dir.exists():
		raise SystemExit(f"Input directory not found: {input_dir}")

	# Output directory change
	output_dir = script_dir / "output"
	output_dir.mkdir(parents=True, exist_ok=True)
	output_path = output_dir / cfg["output_name"]
	if output_path.exists() and not args.force:
		print(f"[SKIP] {kind} output exists: {output_path}")
		return

	temp_base = script_dir / "working" / f"_temp_{kind}"
	extracted_dir = temp_base / "extracted"
	converted_dir = temp_base / "converted"
	if temp_base.exists():  # clean previous temp
		for p in sorted(temp_base.rglob("*"), reverse=True):
			try:
				if p.is_file():
					p.unlink()
				else:
					p.rmdir()
			except Exception:
				pass
	extracted_dir.mkdir(parents=True, exist_ok=True)
	converted_dir.mkdir(parents=True, exist_ok=True)

	# 1. Gather and unzip
	zips = sorted([p for p in input_dir.glob("*.zip")])
	if not zips:
		raise SystemExit(f"No zip files found in {input_dir}")
	unzip_all(zips, extracted_dir)

	# 2. Discover tiles (skip macOS resource fork files starting with ._)
	tiles = sorted([p for p in extracted_dir.glob("*.tif") if not p.name.startswith("._")])
	if not tiles:
		raise SystemExit(f"No GeoTIFF tiles extracted for {kind}")

	# 3. Scan tiles
	tile_infos: List[TileInfo] = []
	# Load palette for mapping id->name
	palette = load_palette(kind, input_dir)
	# Accumulate class counts (exclude 0) while scanning
	class_counts: dict[int, int] = {}
	valid_max = cfg["valid_max"]
	scan_start = time.time()
	for tif in tqdm(tiles, desc=f"Scanning {kind}", unit="tile"):
		stats = compute_stats_exact(tif)
		tinfo = TileInfo(path=tif, is_blank=(stats[0] == 0 and stats[1] == 0), stats=stats)
		if stats[1] > 255:
			raise SystemExit(f"Tile {tif.name} has value >255 ({stats[1]}). Aborting.")
		if stats[1] > valid_max:
			print(f"[WARN] Tile {tif.name} max {stats[1]} exceeds expected class max {valid_max}")
		tile_infos.append(tinfo)
		# If non-blank, compute full histogram (0-255) capturing unexpected codes
		if not tinfo.is_blank:
			try:
				ds_tile = gdal.Open(str(tif), gdal.GA_ReadOnly)
				band = ds_tile.GetRasterBand(1)
				hist = band.GetHistogram(min=0.0, max=255.0, buckets=256, include_out_of_range=1, approx_ok=0)
				ds_tile = None
				if hist:
					for cid, cnt in enumerate(hist):
						if cnt == 0:
							continue
						class_counts[cid] = class_counts.get(cid, 0) + cnt
			except Exception as e:
				raise SystemExit(f"Failed histogram on {tif.name}: {e}")
	scan_dur = time.time() - scan_start

	non_blank = [t for t in tile_infos if not t.is_blank]
	if not non_blank:
		raise SystemExit(f"All tiles blank for {kind}; nothing to mosaic.")
	print(f"{kind}: {len(tile_infos)} tiles, {len(non_blank)} non-blank, scan {human_time(scan_dur)}")

	# 4. Convert as needed
	convert_start = time.time()
	for t in tqdm(non_blank, desc=f"Convert {kind}", unit="tile"):
		convert_to_byte_if_needed(t, converted_dir)
	convert_dur = time.time() - convert_start

	# Build list preserving alphabetical order
	sources: List[Path] = []
	for t in non_blank:
		sources.append(t.converted_path if t.converted_path else t.path)

	# 5. Build VRT
	vrt_path = temp_base / f"{kind}.vrt"
	build_vrt(sources, vrt_path)

	# 6. Translate to final GeoTIFF
	translate_start = time.time()
	translate_vrt_to_geotiff(vrt_path, output_path)
	translate_dur = time.time() - translate_start

	# 7. Reclass unknown values to 0 before overviews
	reclass_start = time.time()
	reclass_output(output_path, set(palette.keys()) | {0})
	reclass_dur = time.time() - reclass_start

	# 8. Overviews & metadata (exclude unknown >0 ids from metadata)
	overview_start = time.time()
	used_pairs: List[str] = []
	for cid in sorted(class_counts.keys()):
		if cid not in palette and cid != 0:
			continue
		name = (palette.get(cid, "Ignore") if cid == 0 else palette.get(cid, f"Unknown_{cid}"))
		used_pairs.append(f"{cid}:{name}")
	classes_metadata_value = ",".join(used_pairs)
	extra_meta = {"classes": classes_metadata_value if classes_metadata_value else None}
	build_overviews(output_path, extra_metadata=extra_meta)
	overview_dur = time.time() - overview_start

	# 9. Validate
	validate_final(output_path, valid_max)

	# Output class counts summary (pre-mosaic distribution including unknowns)
	if class_counts:
		print(f"\nClass ID   Class Name                     Pixel Count")
		print("-" * 60)
		rows = []
		for cid in sorted(class_counts.keys()):
			name = palette.get(cid, f"Unknown_{cid}")
			count = class_counts[cid]
			rows.append((cid, name, count))
		for cid, name, count in rows:
			print(f"{str(cid).ljust(10)} {name.ljust(30)} {count:,}")
		csv_path = output_dir / f"{kind}_class_counts.csv"
		try:
			with csv_path.open("w", encoding="utf-8") as f:
				f.write("class_id,class_name,count\n")
				for cid, name, count in rows:
					f.write(f"{cid},{name},{count}\n")
			print(f"[INFO] Wrote class counts CSV: {csv_path}")
		except Exception as e:
			print(f"[WARN] Could not write class counts CSV: {e}")

	# 9. Cleanup temp unless requested to keep
	if not args.keep_temp:
		for p in sorted(temp_base.rglob("*"), reverse=True):
			try:
				if p.is_file():
					p.unlink()
				else:
					p.rmdir()
			except Exception:
				pass

	total = scan_dur + convert_dur + translate_dur + reclass_dur + overview_dur
	print(
		f"[DONE] {kind} -> {output_path.name} | scan {human_time(scan_dur)}, convert {human_time(convert_dur)}, translate {human_time(translate_dur)}, reclass {human_time(reclass_dur)}, overviews {human_time(overview_dur)}, total {human_time(total)}"
	)


# ------------------------------- CLI Interface -------------------------------

def parse_args(argv: List[str]) -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Mosaic categorical habitat GeoTIFF tiles.")
	parser.add_argument(
		"--dataset",
		choices=["benthic", "geomorphic", "both"],
		default="both",
		help="Dataset to process (default: both)",
	)
	parser.add_argument("--workers", type=int, default=1, help="Reserved arg (future parallel); currently informational.")
	parser.add_argument("--force", action="store_true", help="Rebuild even if output file exists.")
	parser.add_argument("--keep-temp", action="store_true", help="Retain temporary extracted / converted tiles.")
	parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
	return parser.parse_args(argv)


def main(argv: List[str]) -> int:
	args = parse_args(argv)
	start_all = time.time()
	targets = ["benthic", "geomorphic"] if args.dataset == "both" else [args.dataset]
	try:
		for kind in targets:
			process_dataset(kind, args)
	except KeyboardInterrupt:
		print("Aborted by user.")
		return 2
	except SystemExit as e:
		return e.code if isinstance(e.code, int) else 1
	except Exception as e:
		print(f"ERROR: {e}")
		return 1
	print(f"All done in {human_time(time.time() - start_all)}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main(sys.argv[1:]))

# TODO add processing to combine raw GeoTIFF files into a single dataset in this file.