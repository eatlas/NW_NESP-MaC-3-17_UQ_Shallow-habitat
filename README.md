# Northern Australian Shallow Marine Habitat Mosaics (NESP MaC 3.17)

This repository contains the final processing workflow to build authoritative benthic and geomorphic habitat mosaics for northern Australia under the NESP Marine and Coastal Hub Project 3.17. The scripts take the tiled predictive habitat model outputs (after manual QA/QC clean‑up) for five regional modelling domains and merge them into two seamless, optimized GeoTIFF datasets: one benthic classification mosaic and one geomorphic classification mosaic.

## Regional Model Domains
Each region was modelled separately (distinct tuning / training) and delivered as zip archives of categorical raster tiles (GeoTIFF):

| Region key | Area | Notes |
|------------|------|-------|
| `gulf`     | Gulf of Carpentaria | Inshore & coastal habitats |
| `nwest`    | Northern Territory & northern Western Australia | Extensive mixed coastal systems |
| `offshore` | Offshore NW (Scott Reef, Ashmore Reef, etc.) | Deeper & reef features |
| `sharkbay` | Shark Bay region | Complex embayment, seagrass & banks |
| `west`     | WA coastline south of Shark Bay to Houtman Abrolhos | Transitional zone |

Overlap occurs between some regional extents; a deterministic precedence (alphabetical by tile filename) is used when combining—"first non‑zero wins"—preserving upstream categorical assignments.

## Classification Schemes
Two categorical products are produced:

1. Benthic habitat classes (0 = nodata)
2. Geomorphic habitat classes (0 = nodata)

During final processing any pixel values outside the published palettes are reclassified to 0 to ensure only sanctioned class codes remain.

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
11. Cleanup temporary working files unless explicitly retained.

## Dual Script Implementations (GPT‑5 vs Claude Sonnet 4.5)
To strengthen confidence in reproducibility and detect subtle specification ambiguities, the processing workflow was implemented twice:

| Script | File | Purpose |
|--------|------|---------|
| GPT‑5 implementation | `01-combine-raw-geotiffs_gpt5.py` | Primary, iteratively refined version (exact stats + reclassification) |
| Claude Sonnet 4.5 implementation | `01-combine-raw-geotiffs_claude.py` | Independent derivation for cross‑validation |

Both large language model (LLM) generated versions followed the same conceptual specification; differences surfaced areas for clarification and improvement.

## Comparison & Findings
Early comparison highlighted a discrepancy: the initial GPT‑5 script used approximate statistics, failing to surface sparse higher geomorphic class codes absent from the loaded palette (`geo_palette.csv`). This caused under‑reporting of some class pixel counts and hid mismatches. After adopting exact statistics and full 0–255 histograms the GPT‑5 version aligned with the Claude result and enabled robust detection and reclassification of unknown values.

Key outcomes:
- Exact statistics (approx_ok=False) are essential for sparse high category detection.
- Full histogram enumeration prevents silent omission of codes outside an expected range.
- Re-running the specification through multiple models exposes implicit assumptions (ordering precedence, handling unknown classes, nodata enforcement) that may otherwise remain undocumented.

## Lessons Learned
The principal source of divergence was not model capability but subtle ambiguity in the original requirements (e.g., whether to treat high unseen codes as errors, whether unknown codes should survive, and how overlap precedence should be defined). Implementing the pipeline with multiple LLMs revealed corner cases (like sparse high values) and refining the final workflow to be deterministic, transparent, and auditable.

## Prompts & Iteration History
A record of the prompts, follow-up clarifications, and incremental refinements is maintained in `PROMPTS.md`. This document provides traceability from the initial specification through each adjustment (tiling size change, overview method fix, classification counting, exact stats adoption, unknown code reclassification, macOS resource fork filtering).

## Setup & Execution
Environment and usage details are documented separately for each implementation:

- GPT‑5 setup: `SETUP_GPT5.md`
- Claude Sonnet 4.5 setup: `SETUP_Claude.md`

Typical run (processing both mosaics):

```bash
python 01-combine-raw-geotiffs_gpt5.py
```

Key operational assumptions:
- All source tiles share a uniform CRS, resolution, and alignment.
- Nodata is enforced as 0 throughout (both source conversion and final mosaic).
- Overlap precedence: alphabetical order with first non‑zero pixel retained.

## Data Integrity & Reclassification
Unknown class IDs (those not present in the respective palette CSV) are remapped to 0 before building pyramids, ensuring derived overviews cannot retain deprecated or spurious category values. The pre‑reclass table and CSV still enumerate these unknowns for audit purposes.

## Citation & Licensing
This processing is associated the the []'Northern Australia shallow marine benthic and geomorphic habitat mapping - (NESP MaC 3.17, UQ, UNSW, AIMS)'](https://doi.org/10.26274/qeh6-p243) dataset.


Please cite the project and DOI when using the mosaics in publications or derivative products.

## Contact
For questions regarding habitat classification methodology or project context, refer to NESP MaC documentation or contact the project maintainers.

---
Generated and iteratively refined with multiple LLM assistants to improve specification clarity and robustness.
