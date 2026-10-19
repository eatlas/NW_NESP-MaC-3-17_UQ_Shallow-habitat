# UQ and ACA comparison

This standalone analysis compares final UQ and Allen Coral Atlas maps at common expert-labelled reference locations. It excludes UQ points within 50 m of the combined published ACA reference polygons. Only locations with coverage in both products enter the paired agreement calculation. [PAPER.md](PAPER.md) is the self-contained mini-paper intended for linking from the main report. [FINDINGS.md](FINDINGS.md) gives the concise outcome and qualifications. Read [SPECIFICATION.md](SPECIFICATION.md) for the detailed analysis protocol.

## Run

From `derived/geotiff-cleanup`, use the existing environment:

```bash
conda activate habitat-mosaic
python 01-download-input-data.py
python HA04-aca-compare/compare.py --check-inputs
python -m unittest discover -s HA04-aca-compare -p 'test_*.py' -v
python -u HA04-aca-compare/compare.py
python HA04-aca-compare/verify_results.py
python HA04-aca-compare/make_tables.py
python HA04-aca-compare/coverage.py
```

ACA reference polygons and their metadata are supplied under `data/in-3p-mirror/ACA-ref/{WA-benthic,WA-geomorphic,Timor-benthic,Timor-geomorphic}`, with original filenames. They do not need to be downloaded again when using the distributed data bundle. For a code-only rebuild, follow the [global README's manual download instructions](../README.md#mirrored-third-party-data-and-manual-downloads). The downloader prints a reminder rather than attempting unreliable ACA reference URLs; it still downloads the existing coastline inputs. The old prototype's `ACA-reference` folder is not used.

Final UQ rasters and reference CSVs must already exist under `data/out/benthic`, `data/out/geomorphic` and `data/out/reference_training_csv`. Obtain ACA map GeoPackages through its [download portal](https://allencoralatlas.org/atlas/) and retain the existing structure under `data/in-3p/AllenCoralAtlas/WA` and `Timor-Arafura`, with `Benthic-Map/benthic.gpkg` and `Geomorphic-Map/geomorphic.gpkg` in each. Reference archives are not substitutes for these map layers.

The analysis resolves default paths relative to its location. `--data-dir PATH` supports an alternative data root. `--check-inputs` checks required file presence without sampling. The default bootstrap uses 1,999 replicates; `--replicates` can change this, with a minimum of 99 for development checks. No packages beyond the existing environment are required. Tests use temporary synthetic data and do not need the downloads.

## Statistics

Only tables presented in PAPER.md are written under `data/out/stats/HA04-aca-compare`.

| File | Contents |
|:---|:---|
| coverage-area.csv | Table 1 source: classification, bioregion, UQ area in square kilometres and percentage also mapped by ACA |
| coverage-area-table.md | Formatted mapped-area coverage table supporting Table 1; the paper selects and orders the displayed bioregions |
| report_table.csv | Table 2: classification, region, paired count, agreement percentages, difference in percentage points, interval bounds and occupied 5 km block count |
| report-table.md | Formatted Table 2 with caption and limitations |
| class-alignment-table.md | Table 3: geomorphic agreement without Rocky Reef and Terrestrial Reef Flat points |

Intermediate calculations and verification records are written to `working/HA04-aca-compare`. They are not distributed with the dataset or tracked in Git. Rerun the scripts to recreate them. The point file is retained here for spatial inspection and verification.

| File | Contents |
|:---|:---|
| summary.csv | Paired regional agreement, differences and exclusion/coverage counts; use buffer_m = 50 for primary results |
| classes.csv | Per-class user's and producer's agreement for each product |
| confusion.csv | Long-format confusion counts, including unexpected valid mapped classes |
| uncertainty.csv | Conditional paired block-bootstrap intervals at 1, 5 and 10 km |
| points.csv | Original reference rows, raw and harmonised labels, predictions, duplicate flags and exclusion masks |
| manifest.json | Input fingerprints, reference geometry inventories, package versions and processing settings |
| report_table.csv | Full primary 50 m results joined to the 5 km uncertainty estimates, before publication-column selection |
| coverage-table.md | Primary regional exclusion and coverage counts |
| sensitivity-table.md | Paired effects and sample sizes for the 0, 50 and 100 m buffers |
| coverage-area.csv | Full area calculations, including ACA area, intersection area and ACA area outside UQ |

Shark Bay is sampled into points.csv but excluded from the comparison statistics because ACA maps less than 1% of its habitat area. `coverage.py` needs the IMCRA bioregions from `A01-download-analysis-data.py` and writes temporary rasters to `working/HA04-aca-compare`.

The 0 m sensitivity applies no buffer but still removes points that fall inside ACA reference polygons; 100 m provides a wider exclusion. The 5 km figure is not a buffer: it is the grid size used to resample points in spatial blocks when estimating the 95% intervals. The script checks nested masks, coverage partitions and paired-effect arithmetic. `status.json` and `progress.md` track execution in this script folder. Do not publish old statistics as a successful new run if the current status is blocked.

The publication verifier expects the primary 1,999-replicate run. Development runs with fewer replicates should not be used to regenerate publication tables. The paper contains a static copy of the primary table for GitHub readability; regenerate tables and review the paper whenever inputs or methods change. Use a release-commit permalink to the paper when citing it from the report. No GitHub publication or main-report edit is performed by these scripts.