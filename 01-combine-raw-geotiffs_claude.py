#!/usr/bin/env python3
"""
Process and mosaic GeoTIFF files for NESP MaC 3-17 Shallow Habitat Mapping
This script processes benthic and geomorphic raster tiles, combining them into
single optimized GeoTIFF files with compression and pyramids.
"""

import os
import sys
import zipfile
import glob
from pathlib import Path
import shutil
from typing import List, Tuple, Dict
import csv
import time
import numpy as np
from osgeo import gdal, gdalconst
from tqdm import tqdm
from collections import defaultdict

# Enable GDAL exceptions
gdal.UseExceptions()

class GeoTiffProcessor:
    """Process and mosaic GeoTIFF files"""
    
    def __init__(self, base_dir: str | Path = "."):
        self.base_dir = Path(base_dir)
        self.original_dir = self.base_dir.parent / "original"
        self.working_dir = self.base_dir / "working"
        self.output_dir = self.base_dir / "output_claude"
        
        # Define folder structure
        self.folders = {
            'benthic': {
                'source': self.original_dir / "Raw benthic raster files",
                'raw': self.working_dir / "raw" / "benthic",
                'patched': self.working_dir / "raw-patched" / "benthic",
                'output': self.output_dir / "NW_NESP-MaC-3-17_UQ_Shallow-habitat_Benthic_2025.tif",
                'palette_csv': self.original_dir / "Raw benthic raster files" / "benthic_palette.csv"
            },
            'geomorphic': {
                'source': self.original_dir / "Raw geomorphic raster tiles",
                'raw': self.working_dir / "raw" / "geomorphic",
                'patched': self.working_dir / "raw-patched" / "geomorphic",
                'output': self.output_dir / "NW_NESP-MaC-3-17_UQ_Shallow-habitat_Geomorphic_2025.tif",
                'palette_csv': self.original_dir / "Raw geomorphic raster tiles" / "geo_palette.csv"
            }
        }
        
        # Pyramid levels
        self.overview_levels = [2, 4, 8, 16, 32, 64, 128]
        
        # Class statistics (pixel counts per class)
        self.class_counts = {
            'benthic': defaultdict(int),
            'geomorphic': defaultdict(int)
        }
        
        # Class names from CSV
        self.class_names = {
            'benthic': {},
            'geomorphic': {}
        }
        
    def create_directories(self):
        """Create necessary working directories"""
        print("Creating working directories...")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for dataset in self.folders.values():
            dataset['raw'].mkdir(parents=True, exist_ok=True)
            dataset['patched'].mkdir(parents=True, exist_ok=True)
    
    def load_class_palette(self, dataset_name: str):
        """Load class names from CSV palette file"""
        dataset = self.folders[dataset_name]
        csv_path = dataset['palette_csv']
        
        if not csv_path.exists():
            print(f"WARNING: Palette CSV not found: {csv_path}")
            return
        
        print(f"Loading class palette from {csv_path.name}...")
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                class_id = int(row['class_id'])
                class_name = row['class_name'].replace('*', '')  # Remove asterisks
                self.class_names[dataset_name][class_id] = class_name
        
        print(f"  Loaded {len(self.class_names[dataset_name])} class definitions")
    
    def extract_zip_files(self, dataset_name: str):
        """Extract all zip files from source folder to raw working folder"""
        dataset = self.folders[dataset_name]
        source_dir = dataset['source']
        raw_dir = dataset['raw']
        
        print(f"\n{'='*70}")
        print(f"Processing {dataset_name} dataset")
        print(f"{'='*70}")
        
        if not source_dir.exists():
            print(f"ERROR: Source directory not found: {source_dir}")
            return False
            
        zip_files = list(source_dir.glob("*.zip"))
        
        if not zip_files:
            print(f"WARNING: No zip files found in {source_dir}")
            return False
        
        print(f"\nExtracting {len(zip_files)} zip files...")
        for zip_path in tqdm(zip_files, desc="Extracting zips"):
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(raw_dir)
            except Exception as e:
                print(f"ERROR extracting {zip_path}: {e}")
                return False
        
        return True
    
    def check_if_blank_and_count_classes(self, tif_path: Path, dataset_name: str) -> Tuple[bool, bool, int, int, str]:
        """
        Check if GeoTIFF is blank (all zeros), validate data type, and count pixel classes.
        Returns: (is_blank, has_error, max_value, bit_depth, error_message)
        """
        try:
            ds = gdal.Open(str(tif_path), gdalconst.GA_ReadOnly)
            if ds is None:
                return False, True, 0, 0, "Unable to open file (not a valid GeoTIFF)"
            
            band = ds.GetRasterBand(1)
            
            # Get data type
            gdal_dtype = band.DataType
            bit_depth = gdal.GetDataTypeSize(gdal_dtype)
            
            # Read the entire band data
            data = band.ReadAsArray()
            
            if data is None:
                ds = None
                return False, True, 0, 0, "Unable to read raster data"
            
            # Get min/max values
            min_val = np.min(data)
            max_val = np.max(data)
            
            # Check if blank (all zeros)
            is_blank = (max_val == 0)
            
            # Check for values > 255 (error condition)
            has_error = (max_val > 255)
            error_message = f"Max value {max_val} exceeds 255" if has_error else ""
            
            # Count pixels per class (only if not blank and no error)
            if not is_blank and not has_error:
                unique, counts = np.unique(data, return_counts=True)
                for class_id, count in zip(unique, counts):
                    self.class_counts[dataset_name][int(class_id)] += int(count)
            
            ds = None
            
            return is_blank, has_error, int(max_val), bit_depth, error_message
            
        except Exception as e:
            return False, True, 0, 0, f"Exception: {str(e)}"
    
    def analyze_tiff_files(self, dataset_name: str) -> List[Path]:
        """
        Analyze all TIFF files, identify blank ones, check for errors, and count classes.
        Returns list of non-blank files to process.
        """
        dataset = self.folders[dataset_name]
        raw_dir = dataset['raw']
        
        # Get all .tif files, but exclude macOS metadata files (._*)
        all_tif_files = list(raw_dir.glob("*.tif"))
        tif_files = [f for f in all_tif_files if not f.name.startswith('._')]
        
        if not tif_files:
            print(f"WARNING: No valid TIFF files found in {raw_dir}")
            return []
        
        if len(all_tif_files) != len(tif_files):
            skipped = len(all_tif_files) - len(tif_files)
            print(f"Skipping {skipped} macOS metadata file(s) (._ prefix)")
        
        print(f"\nAnalyzing {len(tif_files)} TIFF files and counting classes...")
        
        non_blank_files = []
        blank_count = 0
        error_count = 0
        skipped_count = 0
        bit_depth_counts = {}
        
        for tif_path in tqdm(tif_files, desc="Analyzing files"):
            is_blank, has_error, max_val, bit_depth, error_message = self.check_if_blank_and_count_classes(tif_path, dataset_name)
            
            if has_error:
                # If it's a file that couldn't be opened, skip it silently (likely invalid file)
                if "Unable to open file" in error_message or "Exception" in error_message:
                    print(f"\nSkipping invalid file: {tif_path.name} - {error_message}")
                    skipped_count += 1
                else:
                    # This is a real error (values > 255)
                    print(f"\nERROR: {tif_path.name} - {error_message}")
                    error_count += 1
                continue
            
            if is_blank:
                blank_count += 1
            else:
                non_blank_files.append(tif_path)
                bit_depth_counts[bit_depth] = bit_depth_counts.get(bit_depth, 0) + 1
        
        print(f"\nAnalysis complete:")
        print(f"  Total files: {len(tif_files)}")
        print(f"  Blank files (skipped): {blank_count}")
        print(f"  Invalid files (skipped): {skipped_count}")
        print(f"  Non-blank files: {len(non_blank_files)}")
        print(f"  Files with errors: {error_count}")
        
        if bit_depth_counts:
            print(f"  Bit depths found:")
            for depth, count in sorted(bit_depth_counts.items()):
                print(f"    {depth}-bit: {count} files")
        
        if error_count > 0:
            print("\nERROR: Cannot proceed due to files with values > 255")
            return []
        
        return non_blank_files
    
    def print_class_statistics(self, dataset_name: str):
        """Print class statistics and generate CLASSES metadata string"""
        counts = self.class_counts[dataset_name]
        names = self.class_names[dataset_name]
        
        print(f"\nClass Statistics for {dataset_name} (input data before filtering):")
        print(f"{'Class ID':<10} {'Class Name':<30} {'Pixel Count':<20} {'Status':<15}")
        print("-" * 80)
        
        # Build metadata string (exclude class 0 and unknown classes)
        classes_metadata_parts = []
        total_unknown_pixels = 0
        valid_class_ids = set(names.keys())
        
        # Prepare data for CSV export
        csv_data = []
        
        for class_id in sorted(counts.keys()):
            count = counts[class_id]
            
            # Check if class is in palette
            if class_id in names:
                name = names[class_id]
                status = "Valid"
                # Add to metadata (exclude 0)
                if class_id != 0:
                    classes_metadata_parts.append(f"{class_id}:{name}")
            else:
                name = f"Unknown_{class_id}"
                status = "→ Set to nodata"
                total_unknown_pixels += count
            
            print(f"{class_id:<10} {name:<30} {count:<20,} {status:<15}")
            
            # Add to CSV data
            csv_data.append({
                'class_id': class_id,
                'class_name': name,
                'count': count
            })
        
        # Export to CSV
        csv_path = self.output_dir / f"{dataset_name}_class_counts.csv"
        self.export_class_counts_csv(csv_path, csv_data)
        
        # Create metadata string
        classes_metadata = ",".join(classes_metadata_parts)
        
        print(f"\n{'='*80}")
        if total_unknown_pixels > 0:
            print(f"WARNING: {total_unknown_pixels:,} pixels with unknown class IDs will be set to nodata (0)")
        print(f"Total valid classes (excluding nodata): {len(classes_metadata_parts)}")
        print(f"CLASSES metadata: {classes_metadata}")
        print(f"Class counts exported to: {csv_path}")
        print(f"{'='*80}")
        
        return classes_metadata, valid_class_ids
    
    def export_class_counts_csv(self, csv_path: Path, csv_data: List[Dict]):
        """Export class counts to CSV file"""
        try:
            with open(csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['class_id', 'class_name', 'count'])
                writer.writeheader()
                writer.writerows(csv_data)
            print(f"  Class counts saved to: {csv_path.name}")
        except Exception as e:
            print(f"  ERROR saving class counts CSV: {e}")

    def patch_tiff(self, input_path: Path, output_path: Path, valid_class_ids: set):
        """
        Convert TIFF to 8-bit with nodata=0, filtering out unknown class values.
        Pixels with class IDs not in valid_class_ids are set to 0 (nodata).
        """
        try:
            # Open source file
            src_ds = gdal.Open(str(input_path), gdalconst.GA_ReadOnly)
            if src_ds is None:
                raise ValueError(f"Cannot open {input_path}")
            
            # Read the data
            src_band = src_ds.GetRasterBand(1)
            data = src_band.ReadAsArray()
            
            # Filter: set unknown class IDs to 0 (nodata)
            mask = np.isin(data, list(valid_class_ids), invert=True)
            if np.any(mask):
                data[mask] = 0
            
            # Create output file
            driver = gdal.GetDriverByName('GTiff')
            dst_ds = driver.Create(
                str(output_path),
                src_ds.RasterXSize,
                src_ds.RasterYSize,
                1,
                gdalconst.GDT_Byte,
                options=[
                    'TILED=YES',
                    'COMPRESS=LZW',
                    'BIGTIFF=IF_SAFER'
                ]
            )
            
            if dst_ds is None:
                raise ValueError(f"Cannot create {output_path}")
            
            # Copy georeferencing
            dst_ds.SetGeoTransform(src_ds.GetGeoTransform())
            dst_ds.SetProjection(src_ds.GetProjection())
            
            # Write filtered data
            dst_band = dst_ds.GetRasterBand(1)
            dst_band.WriteArray(data)
            dst_band.SetNoDataValue(0)
            
            # Cleanup
            dst_band.FlushCache()
            dst_band = None
            dst_ds = None
            src_ds = None
            
        except Exception as e:
            print(f"\nERROR patching {input_path.name}: {e}")
            raise
    
    def patch_tiff_files(self, dataset_name: str, files_to_patch: List[Path], valid_class_ids: set):
        """Patch all non-blank TIFF files, filtering out unknown class values"""
        dataset = self.folders[dataset_name]
        patched_dir = dataset['patched']
        
        print(f"\nPatching {len(files_to_patch)} files to 8-bit with nodata=0...")
        print(f"Filtering: Setting pixels with unknown class IDs to nodata (0)")
        
        for input_path in tqdm(files_to_patch, desc="Patching files"):
            output_path = patched_dir / input_path.name
            self.patch_tiff(input_path, output_path, valid_class_ids)
    
    def create_mosaic(self, dataset_name: str, classes_metadata: str):
        """Create final mosaic with pyramids and metadata"""
        dataset = self.folders[dataset_name]
        patched_dir = dataset['patched']
        output_path = dataset['output']
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get all patched files
        patched_files = list(patched_dir.glob("*.tif"))
        
        if not patched_files:
            print(f"ERROR: No patched files found in {patched_dir}")
            return False
        
        print(f"\nCreating mosaic from {len(patched_files)} files...")
        print(f"Output: {output_path}")
        
        # Create VRT first
        vrt_path = patched_dir / "mosaic.vrt"
        
        try:
            # Build VRT
            print("Building virtual raster...")
            vrt_options = gdal.BuildVRTOptions(
                srcNodata=0,
                VRTNodata=0
            )
            
            vrt_ds = gdal.BuildVRT(
                str(vrt_path),
                [str(f) for f in patched_files],
                options=vrt_options
            )
            vrt_ds = None
            
            # Translate VRT to final output with compression and metadata
            print("Converting to final GeoTIFF (this may take several hours)...")
            translate_options = gdal.TranslateOptions(
                format='GTiff',
                creationOptions=[
                    'TILED=YES',
                    'COMPRESS=LZW',
                    'BIGTIFF=YES',
                    'NUM_THREADS=ALL_CPUS'
                ],
                callback=gdal.TermProgress_nocb,
                metadataOptions=[
                    'DOI=https://doi.org/10.26274/qeh6-p243',
                    'LICENSE_URL=https://creativecommons.org/licenses/by/4.0/deed.en',
                    f'CLASSES={classes_metadata}'
                ]
            )
            
            gdal.Translate(
                str(output_path),
                str(vrt_path),
                options=translate_options
            )
            
            # Add pyramids/overviews
            print(f"\nBuilding pyramids (levels: {self.overview_levels})...")
            ds = gdal.Open(str(output_path), gdalconst.GA_Update)
            
            if ds is None:
                print(f"ERROR: Could not open {output_path} for adding pyramids")
                return False
            
            # Use MODE resampling for categorical data
            ds.BuildOverviews(
                'MODE',
                self.overview_levels,
                gdal.TermProgress_nocb
            )
            
            ds = None
            
            print(f"\nMosaic complete: {output_path}")
            
            # Get file size
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"File size: {size_mb:.1f} MB")
            
            return True
            
        except Exception as e:
            print(f"\nERROR creating mosaic: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_dataset(self, dataset_name: str):
        """Process a complete dataset (benthic or geomorphic)"""
        print(f"\n{'#'*70}")
        print(f"# PROCESSING {dataset_name.upper()} DATASET")
        print(f"{'#'*70}")
        
        # Step 0: Load class palette
        self.load_class_palette(dataset_name)
        
        # Step 1: Extract zip files
        if not self.extract_zip_files(dataset_name):
            print(f"Failed to extract zip files for {dataset_name}")
            return False
        
        # Step 2: Analyze and identify non-blank files (also counts classes)
        non_blank_files = self.analyze_tiff_files(dataset_name)
        if not non_blank_files:
            print(f"No valid files to process for {dataset_name}")
            return False
        
        # Step 2.5: Print class statistics and generate metadata
        classes_metadata, valid_class_ids = self.print_class_statistics(dataset_name)
        
        # Step 3: Patch files (8-bit, nodata=0, filter unknown classes)
        self.patch_tiff_files(dataset_name, non_blank_files, valid_class_ids)
        
        # Step 4: Create mosaic with metadata
        if not self.create_mosaic(dataset_name, classes_metadata):
            print(f"Failed to create mosaic for {dataset_name}")
            return False
        
        print(f"\n{'#'*70}")
        print(f"# {dataset_name.upper()} DATASET COMPLETE")
        print(f"{'#'*70}\n")
        
        return True
    
    def run(self):
        """Run the complete processing workflow"""
        start_time = time.time()
        
        print("\n" + "="*70)
        print("NESP MaC 3-17 Shallow Habitat GeoTIFF Processing")
        print("="*70 + "\n")
        
        # Create directories
        self.create_directories()
        
        # Process both datasets
        success_benthic = self.process_dataset('benthic')
        success_geomorphic = self.process_dataset('geomorphic')
        
        # Calculate total processing time
        end_time = time.time()
        total_time = end_time - start_time
        hours = int(total_time // 3600)
        minutes = int((total_time % 3600) // 60)
        seconds = int(total_time % 60)
        
        # Summary
        print("\n" + "="*70)
        print("PROCESSING COMPLETE")
        print("="*70)
        print(f"\nBenthic: {'✓ SUCCESS' if success_benthic else '✗ FAILED'}")
        print(f"Geomorphic: {'✓ SUCCESS' if success_geomorphic else '✗ FAILED'}")
        print(f"\nTotal processing time: {hours}h {minutes}m {seconds}s ({total_time:.1f} seconds)")
        
        if success_benthic and success_geomorphic:
            print("\nAll processing completed successfully!")
            print(f"Output files saved to: {self.output_dir}")
            return 0
        else:
            print("\nSome datasets failed to process.")
            return 1


def main():
    """Main entry point"""
    # Get the script directory
    script_dir = Path(__file__).parent
    
    # Create processor and run
    processor = GeoTiffProcessor(script_dir)
    return processor.run()


if __name__ == "__main__":
    sys.exit(main())
