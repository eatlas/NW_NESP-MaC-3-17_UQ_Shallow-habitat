# GeoTIFF Processing Setup and Usage Guide

## Prerequisites
- Anaconda or Miniconda installed
- Access to the `../original` folder containing the zip files

## Setup Instructions

### 1. Create the Conda Environment

Open a terminal in this directory and run:

```bash
conda env create -f environment_claude.yml
```

This will create a new conda environment called `geotiff-processing` with all required dependencies (GDAL, Python, numpy, tqdm).

### 2. Activate the Environment

```bash
conda activate geotiff-processing
```

### 3. Verify GDAL Installation

```bash
python -c "from osgeo import gdal; print(f'GDAL version: {gdal.__version__}')"
```

## Running the Script

With the environment activated, run:

```bash
python 01-combine-raw-geotiffs_claude.py
```

### Expected Processing Time
- The complete processing may take several hours depending on:
  - Total data size
  - Number of files
  - System performance
- Progress bars will show the current stage
- Total processing time will be displayed at the end for benchmarking

### What the Script Does

1. **Loads class palettes** from CSV files:
   - `benthic_palette.csv` for benthic classification names
   - `geo_palette.csv` for geomorphic classification names

2. **Extracts zip files** from:
   - `../original/Raw benthic raster files/`
   - `../original/Raw geomorphic raster tiles/`

3. **Analyzes all GeoTIFF files**:
   - Identifies blank files (100% zeros)
   - Skips invalid files (e.g., macOS metadata files starting with `._`)
   - Checks for values > 255 (error condition)
   - Reports bit depth distribution
   - **Counts pixel occurrences for each classification class**

4. **Reports class statistics**:
   - Displays pixel counts for each class found in the input data
   - Identifies classes not defined in the palette CSV files
   - Reports total pixels with unknown class IDs that will be filtered
   - Generates CLASSES metadata string (excludes class 0/nodata and unknown classes)

5. **Patches non-blank files**:
   - Converts all to 8-bit
   - Sets nodata value to 0
   - **Filters unknown class values**: Sets pixels with class IDs not in the palette to 0 (nodata)
   - Applies LZW compression

6. **Creates final mosaics with metadata**:
   - Builds virtual raster (VRT)
   - Exports to compressed GeoTIFF
   - Generates pyramids at levels: 2, 4, 8, 16, 32, 64, 128
   - Uses MODE resampling (appropriate for categorical data)
   - Embeds metadata: DOI, LICENSE_URL, and CLASSES

### Output Files

Output files are saved to the `output/` directory:

- `output/NW_NESP-MaC-3-17_Shallow-habitat_Benthic.tif`
- `output/NW_NESP-MaC-3-17_Shallow-habitat_Geomorphic.tif`

### Embedded Metadata

Each output file includes:
- **DOI**: https://doi.org/10.26274/qeh6-p243
- **LICENSE_URL**: https://creativecommons.org/licenses/by/4.0/deed.en
- **CLASSES**: Comma-separated list of class_id:class_name pairs for all valid classes present in the data (excluding nodata/0 and unknown classes)

### Data Filtering

The script ensures data quality by:
- Reading class definitions from palette CSV files (`benthic_palette.csv`, `geo_palette.csv`)
- Reporting statistics on the raw input data, including any unknown class IDs
- **Filtering the output**: Any pixels with class IDs not defined in the palette are automatically set to 0 (nodata)
- Only valid, defined classes appear in the final mosaic and metadata

### Working Directories (Kept for Verification)

- `working/raw/benthic/` - Extracted benthic TIFFs
- `working/raw/geomorphic/` - Extracted geomorphic TIFFs
- `working/raw-patched/benthic/` - Processed benthic TIFFs
- `working/raw-patched/geomorphic/` - Processed geomorphic TIFFs

## Troubleshooting

### "Source directory not found"
- Verify the `../original/` folder structure exists
- Check that zip files are in the correct subdirectories

### "Files with values > 255"
- The script will report which files have invalid values
- This indicates an issue with the source data that needs investigation

### "No valid files to process"
- All files may be blank (all zeros)
- Check that the zip files contain valid data

### Memory Issues
- The script is designed for systems with 64GB RAM
- If issues occur, close other applications
- GDAL uses tiled processing to minimize memory usage

### "Cannot open output for adding pyramids"
- May indicate disk space issues
- Verify sufficient free space for the output files

## Cleaning Up (Optional)

To remove the working directories after successful processing:

```bash
rm -rf working/
```

To remove the conda environment when done:

```bash
conda deactivate
conda env remove -n geotiff-processing
```
