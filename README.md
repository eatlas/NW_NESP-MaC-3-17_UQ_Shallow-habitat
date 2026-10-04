# Northern Australian Shallow Marine Habitat Mosaics (NESP MaC 3.17)

This repository contains the final preparation workflow to build benthic and geomorphic habitat mosaics for northern Australia under the NESP Marine and Coastal Hub Project 3.17. The scripts take the tiled predictive habitat model outputs (after manual QA/QC clean‑up) for five regional modelling domains and merge them into two seamless, optimized GeoTIFF datasets: one benthic classification mosaic and one geomorphic classification mosaic. This code does not include the modelling process itself, just the data format conversion for efficient visualisation and publication and analysis scripts for creating area summary statistics. 

## Metadata
The full metadata for this dataset can be found from: 
Markey, K., Lyons, M., Borrego Accevedo, R., Roe, M., Lawrey, E., Phinn, S., & Roelfsema, C. (2025). Shallow benthic and geomorphic habitat maps for Northern and Western Australia (NESP MaC 3.17, UQ, UNSW, AIMS) [Data set]. eAtlas. https://doi.org/10.26274/QEH6-P243

## Input data - Regional Model Domains
Each region was modelled separately (distinct tuning / training) and delivered as zip archives of categorical raster tiles (GeoTIFF):

| Region key | Area | Notes |
|------------|------|-------|
| `gulf`     | Gulf of Carpentaria | Inshore & coastal habitats |
| `nwest`    | Northern Territory & northern Western Australia | Extensive mixed coastal systems |
| `offshore` | Offshore NW (Scott Reef, Ashmore Reef, etc.) | Deeper & reef features |
| `sharkbay` | Shark Bay region | Complex embayment, seagrass & banks |
| `west`     | WA coastline south of Shark Bay to Houtman Abrolhos | Transitional zone |

Overlap occurs between some regional extents. When converting to a final image we use a a deterministic precedence (alphabetical by tile filename) combined with "first non‑zero value wins" when there are overlapping values from two models. 

Each classification class is represented as the integer value assigned to each pixel. The class name, class ids (associated integer values) and default colour styles were provided in CSV files, one for the benthic mapping and one for the geomorphic mapping.

One challenge was that the geomorphic mapping contained a very low number of values not included in the classification palette file.  

One challenge was that the geomorphic data files contained pixels values not included in the classification palette file, and the palette files (both benthic and geomorphic) contained classifications not used in the data files. Those classifications not provided in the palette file corresponded to only a tiny fraction of the mapped pixels and appear to be a by-product of some previous processing stage rather than useful data. This was cleaned up by reassigning these pixels to no data. The classification classes used in the dataset was determined by counting the number of data pixels associated with each classification. Classifications with no data pixels were dropped from the output styling.  

## Output data
These scripts generate the following output products:
- Merged benthic GeoTiff covering the full study area - LZW compressed with internal tiling and pyramids
- Merged geomorphic GeoTiff covering the full study area - LZW compressed with internal tiling and pyramids
- QGIS symbology files (.clr) for setting up a Paletted/Unique Value symbology for the benthic and geomorphic data. These only include classes used in the data.
- CSV files containing the pixel count of each classification value. These are of the raw input data. These were develop solely for determining which classification classes to retain and which data values didn't match the input palette CSVs. 

## High‑Level Processing Pipeline
For each classification type (benthic, geomorphic):

1. Locate & unzip all regional model zip archives.
2. Discover GeoTIFF tiles, skipping blank tiles (all pixel values = 0) and macOS resource fork artifacts (`._*`).
3. Compute exact per‑tile statistics and a full 0–255 histogram to capture any unexpected / sparse high codes.
4. Convert non‑Byte or incorrectly defined nodata tiles to Byte (8‑bit), enforcing `nodata=0` and tiling (256×256) with LZW compression.
5. Build a VRT in deterministic alphabetical order; overlapping pixels retain the first non‑zero value encountered.
6. Translate VRT to a single optimized GeoTIFF (Byte, tiled, LZW, nodata=0).
7. Reclass any pixel whose value is not in the official palette (and not 0) to 0 (nodata).
8. Build mode-resampled overview pyramids (LZW compressed) to preserve categorical integrity at reduced scales.
9. Embed metadata: DOI, license, and a `classes` list enumerating only retained codes.
10. Output a class usage report (CSV + console table) for transparency (includes unknown codes prior to reclassification).

## Dual Script Implementations (GPT‑5 vs Claude Sonnet 4.5)
Much of the processing code developed in this repository was created by LLM coding models. These were developed using Github Copilot in VSCode using Agent mode. Each script was developed twice by two different coding agents, based on the same prompt structure and approach. Double coding the processing was primarily done to allow the relative performance of GPT-5 and Claude Sonnet 4.5 to be evaluated on a real world scripting task. The secondary reason was to improve the confidence in the processed results. Specification ambiguities can lead to outputs that look OK, but contain subtle errors that are missed. By coding the processing twice using independent agents these subtle errors can be detected by comparing the double processed outputs. 

All prompts used to write the scripts and the follow up prompts are recorded in [PROMPT.md](PROMPT.md). This document provides traceability from the initial specification through each adjustment (tiling size change, overview method fix, classification counting, exact stats adoption, unknown code reclassification, macOS resource fork filtering).

Both large language model (LLM) generated versions followed the same conceptual specification; differences surfaced areas for clarification and improvement.

## Double coding findings
Early comparison highlighted a discrepancy: the initial GPT‑5 script used approximate statistics, failing to surface sparse higher geomorphic class codes absent from the loaded palette (`geo_palette.csv`). This caused under‑reporting of some class pixel counts and hid mismatches. If undetected this would have led to a small number of stray pixels with classification values outside the defined classes. This was detected because the Claude sonnet implementation used exact statistics, resulting in a much longer class counts list. The class pixel counts also differed because of the different counting technique. After adjusting the GPT5 script to adopt exact statistics and full 0–255 histograms to ensure there were no assumptions about the maximum class value the GPT‑5 version aligned with the Claude result and enabled robust detection and reclassification of unknown values.

### Model differences
Both GPT-5 and Claude Sonnet 4.5 performed similarly. Both generated approximately the same amount of code, both asked similar clarification questions, both required a similar number of follow up iterations to achieve the final processing. The noted differences were:
- GPT-5 asked more clarifying questions at the start of the process. It is unclear that these questions cover more of the umbiguity of the specifications though. 
- Claude Sonnet is much better at generating nice looking standard out progress messages.
- Claude made a non functional environment.yml including a pip package that couldn't be installed. Both models incorrectly handled the relative paths '../original/'. Both had a similar number of bugs that needing fixing.

There was no winner. It was a draw.

### Lessons Learned
The principal source of divergence was not model capability but subtle ambiguity in the original requirements (e.g., whether to treat high unseen codes as errors, whether unknown codes should survive, and how overlap precedence should be defined). The original specification for the pixel counting was:
> During the pass where you are checking files for zeros, calculate a count for each class_id value. At the end of processing each kind (benthic, geomorphic) output these stats. 

This does not specify that the counting should be exact, although this is what I had assumed. It is common for approximate counting to be used, and so in many cases using approximate counting would have been appropriate. It is likely that the use of approximate counting would have been overlooked if there wasn't the double implementation to detect this error.

Implementing the pipeline with multiple LLMs revealed corner cases (like sparse high values) and refining the final workflow to be deterministic, transparent, and auditable.

## Setup & Execution
The repository holds two groups of scripts:

- **Publication scripts** (`01-download-input-data.py`, `01-combine-raw-geotiffs_*.py`, `02-convert-palette_*.py`, `03-convert-training-to-shp.py`) produced the published GeoTIFFs and styling files.
- **Analysis scripts** (`A01` to `A03`) calculate summary statistics from the published GeoTIFFs. See [Habitat area statistics](#habitat-area-statistics-a01-to-a03).

Both groups use the single `environment.yml`. The analysis scripts added `geopandas`, `shapely`, `pyproj` and `pandas`, and data-downloader was updated to v1.2.0. Update an existing environment with `conda env update -f environment.yml --prune`.

Environment and usage details for the publication scripts are documented separately for each implementation:

- GPT‑5 setup: `SETUP_GPT5.md`
- Claude Sonnet 4.5 setup: `SETUP_Claude.md`

Typical run (processing both mosaics):

```bash
conda env create -f environment_gpt5.yml
conda activate habitat-mosaic-gpt5
python 01-combine-raw-geotiffs_gpt5.py
python 01-combine-raw-geotiffs_claude.py
```

Key operational assumptions:
- All source tiles share a uniform CRS, resolution, and alignment.
- Nodata is enforced as 0 throughout (both source conversion and final mosaic).
- Overlap precedence: alphabetical order with first non‑zero pixel retained.

## Data Integrity & Reclassification
Unknown class IDs (those not present in the respective palette CSV) are remapped to 0 before building pyramids, ensuring derived overviews cannot retain deprecated or spurious category values. The pre‑reclass table and CSV still enumerate these unknowns for audit purposes.

## Citation & Licensing
This processing is associated the the ['Northern Australia shallow marine benthic and geomorphic habitat mapping - (NESP MaC 3.17, UQ, UNSW, AIMS)'](https://doi.org/10.26274/qeh6-p243) dataset.


Please cite the project and DOI when using the mosaics in publications or derivative products.

## Benchmarks

| Computer                   | 01-combine-raw-geotiffs_claude.py | 01-combine-raw-gpt5.py |
|----------------------------|-----------------------------------|------------------------|
| 11th Gen Intel i7-1185G7 @ 3.00GHz (1.80 GHz) |         1h 27m |                 2h 50m |
| MacBook Pro M4 Max                            |            27m |                    25m |

# Analysis of the habitat mapping
In this section we detail the analysis of the habitat mapping. We compare it to the Allen Coral Atlas and calculate the area of each habitat class by region.

## Habitat area statistics (A01 to A03)
These scripts calculate the area of each benthic and geomorphic class for the whole dataset and for each region of three regionalisations: the NESP 3.17 Analysis-regions, the IMCRA v4.0 Meso-scale Bioregions and CAPAD 2024 - Marine. The method is described in [A02-habitat-area-stats-spec.md](A02-habitat-area-stats-spec.md).

The scripts read the published rasters from `data/out/benthic/` and `data/out/geomorphic/`. If these are missing, download the published data from the eAtlas share (https://nextcloud.eatlas.org.au/s/QBRBYaisJCgXf7g) into `data/out/`.

Run order:

```bash
conda activate habitat-mosaic
python A01-download-analysis-data.py   # regionalisations into data/in-3p/
python A02-habitat-area-stats.py       # about 20 min, writes data/out/stats/A02_Habitat-area-stats.csv
python A03-habitat-area-tables.py      # writes data/out/stats/A03_Habitat-area-tables_*.md
```

A02 caches each stage in `working/A02/`, so a failed run resumes where it stopped. After changing an input, delete the cache of that stage and every later stage, or delete `working/A02/` to rebuild everything. The checks are written to `working/A02/A02_checks.csv`.

## Download
To compare with the Allen Coral Atlas the following process needs to be followed:
1. Create an account with the https://allencoralatlas.org.
2. Download the area assests for [Western Australia](https://coral-atlas-user-downloads-prod.storage.googleapis.com/fc45f571-7d9c-478f-97eb-a20ae7818e6a/Western-Australia-20230310001457.zip) and [Timor and Arafura Seas](https://coral-atlas-user-downloads-prod.storage.googleapis.com/1dd3f53b-3ca0-44a1-b65f-eb131cae298f/Timor---Arafura-Seas-20230310000037.zip). Save and unzip these to `data/in-3p/AllenCoralAtlas/WA` and `data/in-3p/AllenCoralAtlas/Timor-Arafura`. Note: If you want to save them to a different folder, but still have the QGIS files work then use a symbolic link. 
```batch
mklink /D "in-3p" "C:\data-3p\NW-NESP-MaC-3-17_UQ_Shallow-habitat\in-3p"
```

## Setting up in QGIS
To set up the new Shallow Habitat layers in QGIS the the `data\out\benthic\NW_NESP-MaC-3-17_UQ_Shallow-habitat_Benthic_2025.tif` and `data\out\NW_NESP-MaC-3-17_UQ_Shallow-habitat_Geomorphic_2025.tif` should be added to QGIS. They can then be styled using the matching `*.clr` file by using `Layer Properties > Symbology > Render type: Paletted/Unique values` the `... > Load Color Map from File ...`.

## Loading PlanetLabs imagery in QGIS
For the comparison mapping we load the Allen Coral Atlas PlanetLabs imagery into QGIS by setting up an XYZ tile service.
- **Name**: Allen Coral Atlas PlanetLabs
- **URL**: `https://storage.googleapis.com/production-coral-tiles/visual/coral_reefs_2020_visual_v1_mosaic/{z}/{x}/{y}.png`
- **Tile Resolution**: Standard (256x256 / 96 DPI)