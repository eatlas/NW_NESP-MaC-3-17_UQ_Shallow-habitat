# Habitat Mosaic Processing Setup

This guide explains how to set up the environment and run the mosaic script `01-combine-raw-geotiffs_gpt5.py` to create the final benthic and geomorphic habitat rasters.

## 1. Requirements
- Conda (Anaconda or Miniconda)
- ~50–100 GB free disk space during processing (depends on zip expansion)
- 64 GB RAM (script is optimized to stream but large cache helps)
- Source data in the expected `../original/` folders (see below)

## 2. Directory Layout (relative to this `derived/` folder)
```
../original/Raw benthic raster files/*.zip
../original/Raw geomorphic raster tiles/*.zip
```
Each zip contains only GeoTIFF tiles. The script extracts them to a temporary working area and deletes it afterward (unless `--keep-temp`).

## 3. Create the Conda Environment
```bash
conda env create -f environment_gpt5.yml
```
This creates an environment named `geotiff-processing` (see `environment_gpt5.yml`).

## 4. Activate & Verify
```bash
conda activate habitat-mosaic-gpt5
python -c "from osgeo import gdal; print('GDAL', gdal.__version__)"
```

## 5. Running the Script
Run from the `derived/` directory:
```bash
python 01-combine-raw-geotiffs_gpt5.py            # Process both datasets
python 01-combine-raw-geotiffs_gpt5.py --dataset benthic
python 01-combine-raw-geotiffs_gpt5.py --dataset geomorphic
```
Useful flags:
```
--force        Rebuild even if final output already exists
--keep-temp    Keep extracted & converted tiles for inspection
--dataset      benthic | geomorphic | both (default both)
--workers N    Reserved (present for future parallel logic)
--version      Show script version
```

## 6. Outputs
```
NW_NESP-MaC-3-17_Shallow-habitat_Benthic.tif
NW_NESP-MaC-3-17_Shallow-habitat_Geomorphic.tif
```
Properties:
- Byte (8‑bit), nodata = 0
- Categorical class codes (unknown input codes remapped to 0 during mosaic)
  - Benthic: 1–19 (0 = nodata)
  - Geomorphic: 1–27 (0 = nodata)
- Tiled 256×256, LZW compressed (standard internal tiling for broad compatibility)
- Overviews (MODE resampling) with LZW compression
- Metadata tags: `doi`, `license`, `classes` (only palette/nodata codes retained in final mosaic)

## 7. Processing Logic Summary
1. Unzip all archives for the dataset.
2. Scan tiles; skip blank tiles (all pixels 0) and macOS resource fork files whose names start with `._`.
3. For each non-blank tile, compute exact statistics and a full 0–255 histogram (captures unexpected codes).
4. Convert any 16‑bit / non‑Byte or missing nodata tiles to 8‑bit Byte with nodata=0.
5. Build VRT in alphabetical order (first non‑zero wins in overlaps).
6. Translate VRT to final GeoTIFF (LZW, tiled 256×256).
7. Reclass any pixel value not in the palette (and not 0) to 0 (nodata) in-place.
8. Build MODE overviews (LZW compressed) and write metadata (`classes`, `doi`, `license`).
9. Validate final mosaic using exact statistics (ensures max within expected range after reclass).
10. Print pre-mosaic class distribution table (including unknown codes) and write CSV.
11. Clean up temporary folders (unless `--keep-temp`).

## 8. Progress & Runtime
- Progress bars for: unzip, scan, convert.
- Inline percentage for translation, reclass, and overviews.
- Runtime summary at completion.
- Pre-mosaic class distribution printed (with thousands separators) and saved to CSV.
- Typical total runtime: hours (depends on I/O bandwidth, tile sizes, proportion of blank tiles).

## 9. Troubleshooting
| Issue | Cause | Action |
|-------|-------|--------|
| "No zip files found" | Wrong folder layout | Confirm `../original/...` paths |
| Value >255 error | Corrupt or unexpected tile | Inspect offending tile with `gdalinfo`; script aborts |
| Unexpected class IDs (e.g. > valid max) | Source modeling artifacts | Appear in pre-mosaic table as Unknown_<id>; remapped to 0 in final mosaic |
| `._filename.tif` appears as tile | macOS resource fork on exFAT / external drives | Automatically skipped; no action needed |
| All tiles blank | Source zips contain only empty tiles | Confirm data delivery |
| Overviews missing | Translation aborted earlier | Re-run with `--force` |
| Slow unzip | Antivirus / network drive | Move data to fast local SSD |

## 10. Cleaning Up
Remove environment:
```bash
conda deactivate
conda env remove -n geotiff-processing
```

## 11. Attribution & License
- DOI: https://doi.org/10.26274/qeh6-p243
- License: CC-BY 4.0 (https://creativecommons.org/licenses/by/4.0/deed.en)

## 12. Next Possible Enhancements (Not Implemented)
- Resume/conversion cache
- Parallel per-tile conversion (`--workers` placeholder)
- CSV manifest of processed tiles
- Optional max extent clipping

---
For scientific reproducibility, retain original zip archives and record the script version in downstream metadata.
