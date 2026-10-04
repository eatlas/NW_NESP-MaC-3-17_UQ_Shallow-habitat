# Habitat area statistics (A01 to A03) specification

This specification describes the analysis scripts that calculate the area of each benthic and geomorphic class in the published Northern Australia shallow marine habitat mapping. The areas are reported for the whole dataset and broken down by three regionalisations: the NESP 3.17 Analysis-regions, the IMCRA v4.0 Meso-scale Bioregions, and CAPAD 2024 - Marine. The outputs are tables for the results chapter and its appendix. The same three regionalisations, with the same identity attributes, were used to report reef counts and areas for the NESP MaC 3.17 North and West Australian reef boundary mapping (AU_NESP-MaC-3-17_AIMS_NW-Aus-Features). Using them here allows the habitat areas to be compared with that reef mapping. This repository does not depend on the reef mapping repository, and everything needed to run the analysis is described here.

Only area is reported. No features are counted.

## Publication scripts and analysis scripts

The repository holds two groups of scripts. The publication scripts produced the published GeoTIFFs and styling files. These are `01-combine-raw-geotiffs_*.py`, `02-convert-palette_*.py` and `01-download-input-data.py`, which downloads the coastline and land datasets used for the QGIS previews. They are not changed by this work.

The analysis scripts use an `A` prefix and are numbered in run order:

| Script | Purpose |
|---|---|
| `A01-download-analysis-data.py` | Download the third party regionalisations into `data/in-3p/`. |
| `A02-habitat-area-stats.py` | Calculate the area of each class per region and write CSV outputs. |
| `A03-habitat-area-tables.py` | Read the A02 CSV and write Pandoc-ready markdown tables in two layouts. |

The README is updated with a section for each group, the run order of the analysis scripts, and the environment changes.

## Input habitat rasters

The analysis reads the published rasters from `data/out/`, not from the `output_claude/` or `output_gpt5/` working outputs and not from the eAtlas. This keeps the analysis tied to the output of the previous phase, so a new version of the mapping cannot be analysed by accident against an old download.

| Mapping | Raster | Palette |
|---|---|---|
| Benthic | `data/out/benthic/NW_NESP-MaC-3-17_UQ_Shallow-habitat_Benthic_2025.tif` | `NW_NESP-MaC-3-17_UQ_Shallow-habitat_Benthic_2025.clr` in the same folder |
| Geomorphic | `data/out/geomorphic/NW_NESP-MaC-3-17_UQ_Shallow-habitat_Geomorphic_2025.tif` | `NW_NESP-MaC-3-17_UQ_Shallow-habitat_Geomorphic_2025.clr` in the same folder |

If a raster is missing, A02 stops with a message directing the user to download the published data from the eAtlas share (https://nextcloud.eatlas.org.au/s/QBRBYaisJCgXf7g) into `data/out/`. The share has the same folder structure as `data/out/`. This download is not scripted.

Both rasters are Byte, EPSG:4326, with a pixel size of 0.000089831528412 degrees (about 10 m) and nodata of 0. The two rasters have the same pixel size but different origins and sizes, so each is processed on its own grid.

The published rasters are single band greyscale GeoTIFFs. Each pixel value is the `class_id` of the class mapped at that pixel. The class names are read from the `.clr` files, which have one line per class in the form `class_id R G B A class_name`. The class name can contain spaces. Only `class_id` and `class_name` are used. `R G B A` is the display colour of the class in QGIS and has no role in the analysis. The largest class ID in either palette is 27. Palette order is ascending `class_id`.

The mapped area of a region is the sum of the areas of all palette classes in that mapping. This includes the geomorphic `Deep` class. `Deep` is clipped to the manual reef mapping, so it represents deep coral reef banks rather than open deep water. There is no benthic mapping where the geomorphic mapping is `Deep`, so the geomorphic mapped area is larger than the benthic mapped area. The mapped area also includes `Terrestrial Reef Flat`, which marks flat shallow sediment areas that are mostly `Sand` in the benthic mapping.

Any non-zero pixel value not in the palette is recorded as `Unknown` with its class ID. Out-of-palette values should have been removed by the publication processing, so `Unknown` is an error detector and is expected to be empty. Any `Unknown` area is printed as a warning and written to the CSV and the checks. It is left out of mapped area totals and the A03 tables.

## Third party regionalisations (A01)

A01 uses the `DataDownloader` class from the open-AIMS `data-downloader` package, in the same way as the existing `01-download-input-data.py`. Each dataset is downloaded, unzipped and flattened into its own folder in `data/in-3p/`. A dataset whose folder already exists is skipped. `data/in-3p/` can be a symbolic link to a folder outside the repository. Each download in A01 is preceded by a comment giving the full citation and the purpose of the dataset.

**Analysis-regions v1.** Lawrey, E. (2025). Supporting datasets for estimating reef counts in the Coral Sea and northern Australia (NESP MaC 3.17, AIMS) (Version 1) [Data set]. eAtlas. https://doi.org/10.26274/xr0r-tb19

- Download: `https://nextcloud.eatlas.org.au/s/HmSS5bxxgKdDxEP/download?path=%2Fv1%2Fin%2Fanalysis-regions`
- Saved to: `data/in-3p/nesp-3-17-analysis-regions/analysis-regions.shp`

**IMCRA v4.0 Meso-scale Bioregions.** Department of Climate Change, Energy, the Environment and Water. (2023). Integrated Marine and Coastal Regionalisation of Australia (IMCRA) v4.0 - Meso-scale Bioregions [Data set]. https://fed.dcceew.gov.au/datasets/erin::integrated-marine-and-coastal-regionalisation-of-australia-imcra-v4-0-meso-scale-bioregions/about. CC BY 3.0.

- Download: `https://hub.arcgis.com/api/v3/datasets/7f83e6e00406487d88d52ac4c2d8c8d4_0/downloads/data?format=shp&spatialRefId=4283&where=1%3D1`
- Saved to: `data/in-3p/IMCRA-v4-0-Meso-Bioregions/IMCRA-v4-Mesoscale-Bioregions.shp`. The long file names in the download are shortened with the `file_find` and `file_replace` options of `download_and_unzip`, which require data-downloader v1.2.0. The options are `file_find=["Integrated_Marine_and_Coastal_Regionalisation_of_Australia_(IMCRA)_v4.0_-_Meso-scale_Bioregions"]` and `file_replace=["IMCRA-v4-Mesoscale-Bioregions"]`.

**CAPAD 2024 - Marine.** Department of Climate Change, Energy, the Environment and Water. (2025). Collaborative Australian Protected Areas Database (CAPAD) 2024 - Marine [Data set]. https://fed.dcceew.gov.au/datasets/erin::collaborative-australian-protected-areas-database-capad-2024-marine/about. CC BY. Attribution: 'Collaborative Australian Protected Areas Database (CAPAD) 2024, Commonwealth of Australia 2025'.

- Download: `https://hub.arcgis.com/api/v3/datasets/0b6e7b6c48a64a3a82c225fa48aee13d_1/downloads/data?format=shp&spatialRefId=4283&where=1%3D1`
- Saved to: `data/in-3p/CAPAD-2024/Collaborative_Australian_Protected_Areas_Database_(CAPAD)_2024_-_Marine.shp`. The folder name is kept short because the file names are long and Windows limits path length.

## Regionalisations

| Short name | Identity | Slug | Overlapping |
|---|---|---|---|
| Analysis-regions v1 | `subregion`, with `region` kept as a grouping | analysis-region | No |
| IMCRA v4.0 Meso-scale Bioregions (2023) | `MESO_NAME` | imcra | No |
| CAPAD 2024 - Marine | `TYPE`, `NAME` | capad | Yes |

The habitat mapping covers only part of each regionalisation. In the Analysis-regions it falls within the North and North-west regions and a small part of the South-west region. Only the IMCRA regions around the Central West Coast and the Abrolhos Islands are used in the South-west. Each regionalisation is therefore first reduced to the polygons that intersect the union of the bounding boxes of the two habitat rasters. Regions that fall inside the bounding box but contain no mapped habitat in either mapping are dropped from the outputs. This removes regions such as GBR, Indonesia and East Cape York without a hand-maintained list. Timor East / Indonesia is kept, because it holds about 2,050 km² of geomorphic mapping (mostly `Deep` reef banks on the Sahul Shelf) even though it has no benthic mapping.

The Analysis-regions and IMCRA are not dissolved. Each polygon is a region, and its identity is unique within the study area. The only repeated IMCRA `MESO_NAME` is a Victorian bioregion made of three polygons, which is outside the study area. A02 stops if an identity is repeated after the regions are filtered.

All regions are reprojected to EPSG:4326 to match the rasters. The difference between GDA94 and WGS84 is about 1 to 2 m, which is negligible at this pixel size. Invalid geometries are repaired with `make_valid`, keeping only the polygonal parts. CAPAD divides each protected area into management zones, such as sanctuary and habitat protection zones. The zones are dissolved by `TYPE` and `NAME` so that each protected area is a single geometry. Both fields are needed because some Australian Marine Parks and state marine parks share a name. `TYPE` and `NAME` are kept as separate fields, and the display label `NAME - TYPE` is only built for the tables. CAPAD is not simplified because rasterisation already removes detail finer than a pixel. The prepared regions are cached as GeoPackages in `working/A02/` for review in QGIS.

The Analysis-regions and IMCRA are each meant to be a set of non-overlapping regions. If two regions overlapped, the pixels in the overlap would go to whichever region was rasterised last. A02 therefore checks each pair of intersecting regions and stops if their overlap is larger than 0.01 km², measured in EPSG:3112. Smaller overlaps are digitising slivers along shared boundaries and are ignored. Any overlaps that fail the check are saved to `working/A02/` for inspection.

## Area calculation (A02)

### Caching

A full run takes about 20 min (see Probe test results). A02 caches the output of each stage in `working/A02/` and skips any stage whose output already exists, so a rerun after a failure resumes at the stage that failed. The cached stages are:

1. Prepared regions, as one GeoPackage per regionalisation.
2. Main pass sums, as one CSV per mapping.
3. Per protected area sums, as one CSV per mapping. A row is appended after each protected area, so an interrupted run resumes at the next protected area.

Each cache file is written under a temporary name and renamed when complete, so a partly written file is never treated as finished. Caches are not checked against their inputs. After changing an input, delete the cache of that stage and of every later stage. Deleting `working/A02/` rebuilds everything.

### Pixel area

The rasters are in geographic coordinates, so pixel area decreases towards the south. All pixels in a raster row have the same area. The area of each row's pixels is calculated once on the WGS84 ellipsoid with the closed-form authalic formula for a cell between two latitudes and a longitude step. The result is checked against `pyproj.Geod.polygon_area_perimeter` for the first, middle and last rows, and A02 stops if the relative difference is greater than 1e-6. Rasters are not reprojected, because resampling would alter the class values.

### Zones

The Analysis-regions and IMCRA are rasterised onto the grid of each habitat raster during the main pass, one strip at a time. Full-size zone rasters are not written. The regions of each regionalisation are loaded once per mapping from the cached GeoPackage into an in-memory OGR layer. For each strip that holds habitat, each regionalisation is rasterised with `gdal.RasterizeLayer` into an in-memory UInt16 strip. This strip covers only the columns from the first to the last habitat pixel in that strip, not the full raster width. GDAL is used rather than rasterio because it is already in the environment. Each pixel takes the region containing its centre (`ALL_TOUCHED=FALSE`). The zone value is a region index starting at 1, stored as an attribute in the GeoPackage, and 0 marks pixels outside all regions. A lookup CSV maps each index to the region identity.

Pixel-centre assignment gives a small error along region boundaries. The regions are large compared with the 10 m pixels, so this error is negligible and an exact fractional overlay is not needed.

The probe showed that writing a full-size zone raster as a GeoTIFF takes about 6.3 min for each combination of mapping and regionalisation, or about 25 min for all four. Rasterising only the habitat column span of each strip in memory takes about 1.2 to 1.9 min per combination. The cost is that the zones cannot be checked visually in QGIS as rasters. The prepared GeoPackages can still be checked against the habitat rasters in QGIS.

### Main pass

Each habitat raster is read once, in strips whose height is the block height of the raster (256 rows). Strips with no habitat are skipped, and in the remaining strips only non-zero habitat pixels are used. The habitat mapping covers less than 1% of the raster area. Both non-overlapping regionalisations are rasterised for the strip as described above. For each regionalisation, the area of each (zone, class) pair is summed with a weighted `numpy.bincount` on `zone * 256 + class`, weighted by the pixel area of each pixel's row. Zone 0 gives the area outside all regions. The dataset-wide totals are summed in the same pass. A progress bar shows progress through the strips.

### Per protected area

CAPAD protected areas can overlap, so they cannot share one set of zones. Each dissolved protected area that intersects the habitat extent is processed on its own, over a window of the habitat raster.

The window is the bounding box of the protected area intersected with the raster extent. It is converted to pixel offsets by rounding the left and top edges down and the right and bottom edges up to whole pixels. The geotransform of the window is built from these integer offsets and the geotransform of the raster, so every window pixel lies exactly on a habitat pixel.

A large protected area can span tens of thousands of pixels in each direction, so the window is processed in strips of the raster block height. The habitat strip is read first, and strips with no mapped habitat are skipped. For the remaining strips, the protected area geometry is first clipped to the rectangle of the strip with `shapely.clip_by_rect`. The clipped part is placed in an in-memory OGR layer and rasterised with `gdal.RasterizeLayer` into an in-memory strip. The area of each class inside the protected area is then summed.

Clipping to the strip is essential for speed. Some protected areas have very detailed boundaries. Lalang-gaddam Marine Park has 512,228 vertices and North Kimberley Marine Park has 314,862. Rasterising the whole polygon for every strip was so slow that the probe was stopped before these areas finished. With clipping, Lalang-gaddam takes 4.1 s and North Kimberley 6.3 s. Where protected areas overlap, the shared area is reported in each, so the per protected area results have no total. No combined inside or outside protected area figures are produced.

### Checks

These checks are written to `working/A02/A02_checks.csv` and summarised on the console. A failed check is reported as a warning rather than stopping the script, so the outputs can be inspected.

- For the Analysis-regions and IMCRA, the area of each class summed over all regions plus 'Outside all regions' equals the dataset-wide area of that class.
- No protected area holds more of a class than the dataset-wide area of that class.
- The total area and pixel count of any `Unknown` class. A non-zero value is also printed as a warning.

The tolerance is 1e-6 of the dataset-wide area.

## Outputs

Generated outputs are saved to `data/out/stats/`. Each file name starts with the number of the script that made it, so every file can be traced back to its script.

### A02 CSV

`data/out/stats/A02_Habitat-area-stats.csv` is a long-format table. It has one row per region, mapping and palette class, including classes with zero area. `Unknown` rows are only written where they have a non-zero area. The `Outside all regions` rows are always written for the Analysis-regions and IMCRA. In the geomorphic mapping these include the `Deep` areas along the edge of the Sahul Shelf, much of which is on the Timor side.

| Column | Description |
|---|---|
| `Regionalisation` | `Dataset`, `Analysis-regions v1`, `IMCRA v4.0 Meso-scale Bioregions (2023)` or `CAPAD 2024 - Marine` |
| `Region_group` | Analysis-regions `region` (for example `North-west`). Empty for others. |
| `Region_type` | CAPAD `TYPE`. Empty for others. |
| `Region_name` | Region name, `All` for `Dataset`, and `Outside all regions` for pixels not in any Analysis-region or IMCRA region. |
| `Mapping` | `Benthic` or `Geomorphic` |
| `Class_id` | Pixel value |
| `Class_name` | Name from the `.clr` file, or `Unknown` |
| `Area_km2` | Area in km² to 6 decimal places |

### A03 tables

A03 writes the same tables in two layouts so that they can be compared in the report:

- `data/out/stats/A03_Habitat-area-tables_combined.md` uses the combined layout.
- `data/out/stats/A03_Habitat-area-tables_separate.md` uses the separate layout.

Both files hold Pandoc pipe tables ready for conversion to Word. Each file starts with an HTML comment naming the script that generated it. Each table is preceded by a caption line of the form `**Table N.** Caption text`. Table numbers are provisional placeholders, because the tables are renumbered when pasted into the report. Text columns are left aligned and number columns are right aligned. Areas are in km² to 2 decimal places with thousands separators, and `<0.01` is shown for small non-zero areas. No percentages are reported.

The tables only list classes with a non-zero area in a region, so there are no rows of zeros. A region with no area in a mapping is left out of that mapping's lists. Classes are listed in palette order. Regions are listed in a fixed order that matches the reef mapping tables. Analysis-regions are ordered by `region` and then `subregion`. IMCRA bioregions are ordered by name. Protected areas are ordered by `TYPE` and then `NAME`. For the Analysis-regions and IMCRA, the area outside all regions is listed last, labelled `Outside all Analysis-regions` or `Outside IMCRA meso-scale bioregions`.

The benthic and geomorphic mappings classify the same area in two different ways. In the combined layout, the benthic results and the geomorphic results are two groups of columns in the same table. For each region, the benthic classes are listed down the benthic columns and the geomorphic classes are listed down the geomorphic columns. The two lists are independent. A benthic class and a geomorphic class on the same row are not related. The two lists usually differ in length, so the shorter list has blank cells below its last class. Each region ends with a bold total row. For example:

| Region | Benthic class | Area (km²) | Geomorphic class | Area (km²) |
|:---|:---|---:|:---|---:|
| North (Nearshore) | Sand | x | Deep | x |
| | Seagrass | x | Sediment Slope | x |
| | | | Reef Slope | x |
| **Total** | | **x** | | **x** |

In the separate layout, each combined table is split into a benthic table followed by a geomorphic table with the same rows. Each has the columns `Region`, `Class` and `Area (km²)`, and each region ends with a bold total row.

Results section tables:

1. Dataset-wide area of each benthic and geomorphic class.
2. Total mapped benthic area and total mapped geomorphic area for each Analysis-region subregion. The columns are `Subregion`, `Benthic area (km²)` and `Geomorphic area (km²)`. There is one row per subregion, a row for the area outside all Analysis-regions, and a bold total row equal to the dataset-wide mapped area. This table is the same in both layouts.

Appendix tables:

1. Area of each class by Analysis-region subregion.
2. Area of each class by IMCRA meso-scale bioregion.
3. Area of each class by protected area (`NAME - TYPE`). Each protected area has its own total row, but there is no overall total because protected areas can overlap.

## Environment

`environment.yml` is extended to cover both groups of scripts. The additions are `geopandas`, `shapely` and `pyproj` for preparing the regions and checking pixel areas, and data-downloader is updated to v1.2.0. The existing `gdal`, `numpy` and `tqdm` are kept.

## Probe test results

Before A02 was implemented, a set of throwaway probe scripts tested the approach in this specification against the published rasters. The scripts were run in `working/probe/` and are not kept in the repository. They used the `nw-aus-feat-env` conda environment (GDAL 3.10.2, geopandas 1.0.1, pyproj 3.7.2, shapely 2.0.7). The regionalisations were read from the reef mapping repository, because `data/in-3p/` did not yet hold them. The probes found no problems that block implementation. They led to the in-memory zones, the clipping of protected areas to each strip, and the single read of each raster for both regionalisations described above. The results below are recorded as a reference for checking A02 and for writing up the method.

### Raster layout

Both rasters use 256 by 256 pixel tiles with LZW compression. Every tile is stored, including tiles that are entirely nodata, so GDAL cannot skip empty areas without reading them. Every strip must therefore be read and decompressed, and empty strips are skipped by their content. The benthic raster has 887 strips and the geomorphic raster has 863.

### Pixel area

The closed-form authalic formula agrees with `pyproj.Geod.polygon_area_perimeter` to a relative difference of about 1e-10. This is well within the 1e-6 tolerance of the A02 check.

### Dataset totals

The benthic mapping covers about 26,555 km². The geomorphic mapping covers about 33,994 km², of which `Deep` is about 4,225 km². No pixel values outside the palettes were found, so the `Unknown` class is empty in both mappings. These totals give a reference for the Dataset rows of the A02 CSV.

### Regions

| Regionalisation | Features | Intersect the habitat extent | Invalid | Duplicate identities | Overlaps > 0.01 km² |
|:---|---:|---:|---:|---:|---:|
| Analysis-regions v1 | 18 | 10 | 0 | 0 | 0 |
| IMCRA v4.0 Meso-scale Bioregions | 62 | 29 | 0 | 0 | 0 |
| CAPAD 2024 - Marine | 5,337 zones | 355 zones, dissolved to 60 protected areas | 6 | 0 | not checked (overlapping) |

Loading and dissolving CAPAD takes about 30 s. The other regionalisations load in under 1 s, and the overlap checks take under 1 s.

### Run time

| Step | Benthic | Geomorphic |
|:---|---:|---:|
| Main pass, both regionalisations | 6.8 min | 7.8 min |
| Of which rasterising zones | 3.0 min | 3.9 min |
| Per protected area, all 60 areas | 1.3 min | not measured, expected to be similar |

A full run of A02 is therefore expected to take about 20 min. The probes for the main pass and the protected areas ran at the same time, so these times may be slightly high. An earlier probe that read each raster in full without zones took about 9 min per raster, which shows that read times vary with disk and system load. The slowest protected area was the Kimberley Australian Marine Park, at 14.5 s. Its time is dominated by reading 153 strips of a window 60,485 pixels wide, rather than by rasterising.

### Area conservation

For both regionalisations and both mappings, the area of each class summed over all regions plus the area outside all regions matched the dataset-wide area to about 1e-14. This is the expected result, because each pixel is assigned to exactly one zone. The check remains useful for detecting indexing errors in the implementation.

### Results to expect in the outputs

About 4.7 km² of each mapping falls outside all Analysis-regions. The cause has not been inspected. It is likely to be small gaps along the coastline or the outer boundary of the regions.

About 1,595 km² of benthic mapping and 4,247 km² of geomorphic mapping falls outside the IMCRA meso-scale bioregions. The meso-scale bioregions cover the continental shelf, so this is expected to be mostly offshore reefs beyond the shelf, such as the Rowley Shoals, Scott Reef and Ashmore Reef, and `Deep` reef banks along the edge of the Sahul Shelf.

Timor East / Indonesia holds about 2,052 km² of geomorphic mapping and no benthic mapping. It will appear in Results table 2 with a benthic area of zero. The IMCRA Oceanic Shoals bioregion shows the same pattern, with about 670 km² of geomorphic mapping and 3 km² of benthic mapping.

The Analysis-regions GBR and Indonesia and the IMCRA East Cape York bioregion have no habitat in either mapping and will be dropped. Nine protected areas have no benthic habitat: the Argo-Rowley Terrace, Gascoyne, Ningaloo, Oceanic Shoals, Shark Bay and West Cape York Australian Marine Parks, the Escape River Fish Habitat Area, and the Great Barrier Reef and Great Barrier Reef Coast Marine Parks. The geomorphic mapping was not tested for protected areas. Some of these areas may hold geomorphic `Deep` reef banks, so they are only dropped if they are also empty in the geomorphic mapping.
