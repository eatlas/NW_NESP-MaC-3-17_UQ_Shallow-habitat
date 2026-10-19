# UQ and Allen Coral Atlas habitat comparison

## Purpose

This analysis tests whether the final UQ habitat mapping agrees more closely with the available expert-labelled references than the Allen Coral Atlas (ACA). It replaces a cropped visual comparison with a paired quantitative assessment across four modelling regions, with Shark Bay excluded. It also estimates how much of the UQ mapped habitat area ACA covers. It is not a reproduction of UQ's historical validation or an independent validation of the UQ model.

The same reference locations, class definitions and spatial coverage are used for both products. References within 50 m of published ACA reference polygons are excluded. The results describe the available reference sample, not area-weighted accuracy across all habitats in northern and western Australia.

## Products and reference evidence

The final UQ [shallow benthic and geomorphic habitat dataset](https://doi.org/10.26274/QEH6-P243) provides 10 m rasters and ten calibration-reference CSVs. Separate models were developed for Shark Bay, West, North West, Gulf and Offshore. The modelling region comes from each CSV filename, not the reporting regions used for habitat area statistics. Final maps include post-classification masks, ecological rules and expert corrections.

ACA provides reef habitat maps derived from high-resolution imagery and expert interpretation. Its [methods](https://allencoralatlas.org/methods/) and [reference workflow](https://doi.org/10.3389/fmars.2021.643381) describe the reference development process. Local map packages are the Western Australia and Timor and Arafura Seas downloads dated March 2023. This package date is not assumed to be the acquisition date of all source imagery. ACA covers substantially less of the coastal study region than UQ and does not map all the shallow sediment habitats included by UQ. Missing ACA coverage is therefore not automatically a classification error.

Published ACA reference archives contain labelled multipart polygons. Each multipart feature can contain many small, geographically clustered components. Feature counts are not independent sample counts. Both benthic and geomorphic references are screened because shared field evidence and interpretation locations may have informed both classification workflows.

| Reference dataset | Citation | Expected original shapefile |
|:---|:---|:---|
| Western Australia benthic | [Borrego-Acevedo et al., 2021](https://doi.org/10.6084/m9.figshare.14622759.v1) | 20201217_WEA_Benthic.shp |
| Western Australia geomorphic | [Borrego-Acevedo et al., 2021](https://doi.org/10.6084/m9.figshare.14622750.v1) | 20201217_WEA_Geomorphic.shp |
| Timor Sea benthic | [Tudman et al., 2021](https://doi.org/10.6084/m9.figshare.14120894.v1) | 20200721_TIS_Benthic.shp |
| Timor Sea geomorphic | [Tudman et al., 2021](https://doi.org/10.6084/m9.figshare.14120891.v1) | 20200721_TIS_Geomorphic.shp |

These reference datasets are CC BY 4.0. Their correspondence to every reference version used for the downloaded ACA maps is unconfirmed. They are described as calibration and/or validation references, not verified validation-only exports. Their licence does not establish permission to republish the underlying contributed field observations or imagery.

## Spatial exclusion

Read all four ACA reference shapefiles, repair invalid geometries, and split multipart geometries into polygon components. Stop if geometry or coordinate reference information is missing or repair produces non-polygon output. Record original feature counts, component counts, repaired feature counts and geographic extents in the manifest.

Buffer each component by 50 m in its local WGS84 UTM zone, selected from the component centroid. This uses local metre-based distances rather than degree buffers or a single continent-wide projection. Buffer boundaries use 32 line segments per quadrant. Reproject the buffered components to WGS84 and query their combined spatial coverage. A point touching the exclusion boundary is excluded. Polygon holes remain available unless the buffer reaches them. No class label is required for exclusion: any known reference component contributes.

Apply the union of all four datasets to both UQ reference classifications. Also calculate 0 m and 100 m exclusion sensitivities. The 0 m result still excludes direct polygon overlap; it is not an unscreened baseline. Check that the excluded sets are nested. A 50 m buffer limits direct and immediate local reuse, but does not establish statistical independence from reference tiles or shared surveys outside it.

## Class harmonisation

| Classification | Reference and UQ transformations | Shared reference classes |
|:---|:---|:---|
| Benthic | Light seagrass (19) to Seagrass (14); legacy Coral (16) and Algae (17) to Coral/Algae (15) | Sand, Rubble, Rock, Seagrass, Coral/Algae, Microalgal Mats |
| Geomorphic | No pooling | Shallow Lagoon, Deep Lagoon, Inner Reef Flat, Outer Reef Flat, Reef Crest, Terrestrial Reef Flat, Sheltered Reef Slope, Reef Slope, Plateau, Back Reef Slope |

Legacy benthic labels follow the original supplied palette. Raw reference and mapped codes are retained in the point table so their pooling remains auditable. All supported shared classes are included in every region where reference samples occur. The historical report's class exclusions are not inherited.

Deep (2), Sediment Slope (10), Small Reef (26) and Rocky Reef (27) references are outside the shared geomorphic domain. ACA Patch Reefs is retained as a distinct mapped diagnostic code 126 and is not assumed equivalent to Small Reef. Valid mapped classes outside the shared reference domain remain disagreements, rather than being dropped. Unrecognised class codes or ACA class names stop the analysis.

Rocky Reef was introduced in the new mapping and has no ACA equivalent. Terrestrial Reef Flat was applied somewhat differently between the two programmes. As a class-alignment sensitivity, repeat the 50 m geomorphic comparison without points where UQ maps Rocky Reef or where Terrestrial Reef Flat is the reference or either mapped class.

## Reference selection and extraction

Read all ten supplied UQ CSVs, preserving file, row and source identifier. Extract longitude and latitude from GeoJSON point geometry. Transform coordinates with explicit longitude/latitude axis order. Sample the full-resolution UQ raster pixel containing each point. No interpolation, raster reprojection or overview sampling is used. Query the ACA polygon layers using spatial filters and exact geometry intersection. Matching multiple distinct ACA classes is ambiguous and excluded from paired coverage. Identical classes in overlapping map packages are not ambiguous.

Harmonise labels before testing duplicate conflicts. Keep one reference per native UQ pixel, modelling region and classification. Exclude pixels with conflicting harmonised reference labels. Duplicate weighting is reduced, but nearby pixels remain correlated. Points outside the UQ raster extent cannot enter this primary pixel-based selection. Pixels inside that extent with NoData remain in the coverage audit.

Remove unsupported reference classes and references inside the specified ACA exclusion. Only points with valid UQ and unambiguous ACA coverage enter thematic agreement. Record UQ-only, ACA-only and neither-covered counts separately. These are reference-sample coverage counts, not mapped areas. Do not infer habitat absence from NoData.

Shark Bay references are sampled and kept in the point table but excluded from all comparison statistics. ACA maps less than 1% of the UQ habitat area in Shark Bay, so a regional agreement figure would be misleading.

## ACA coverage area

Estimate the fraction of UQ mapped habitat that ACA also maps, by IMCRA v4.0 meso-scale bioregion. Sample every eighth native UQ pixel in each direction, reading full-resolution pixels rather than overviews, because overviews ignore NoData when aggregating and inflate sparse habitat area. Rasterise all ACA map polygons of the same classification at the sample centres. Weight each sample by its spherical cell area. Check that the sampled UQ totals agree with the full-resolution A02 totals.

## Agreement and uncertainty

For each classification and modelling region, calculate overall agreement as matching labels divided by the identical paired point count. Present UQ agreement, ACA agreement and UQ minus ACA in percentage points. Preserve the counts where only UQ is correct and only ACA is correct. Their difference divided by paired sample size must reproduce the reported paired effect.

Produce confusion counts with reference classes as rows and predictions as columns. Producer's agreement is the diagonal count divided by its reference row total. User's agreement is the diagonal count divided by its mapped column total. An absent class denominator yields an unavailable metric, not zero accuracy. These metrics are conditional on the selected references and are not area-weighted predictive values for the entire landscape.

Estimate conditional paired uncertainty by resampling spatial blocks, retaining both predictions together. Blocks use GDA94 Australian Albers (EPSG:3577) and side lengths of 1, 5 and 10 km. The primary diagnostic is 5 km. Use 1,999 replicates, a fixed seed of 42 and percentile 2.5 and 97.5 bounds. Fewer than two occupied blocks yields no interval. No independent-pixel significance test is used. Intervals are exploratory, not adjusted for multiple regional comparisons, and do not account for training reuse or reference bias. An interval above zero supports a sample-conditional advantage, not an independently established landscape-wide accuracy gain.

## Outputs and provenance

Write only the paper's mapped-area coverage, primary paired agreement and geomorphic class-alignment tables to `data/out/stats/HA04-aca-compare`. Publication CSVs contain only the fields needed for those tables. Write intermediate calculations and verification records to `working/HA04-aca-compare`, which is not distributed or tracked in Git. The working summary records the input, duplicate, class, exclusion and coverage counts for all three buffers. Additional working tables contain per-class metrics, long-format confusion counts, uncertainty by block size, every original reference row with eligibility flags and predictions, the regional coverage audit and buffer sensitivity. Preserve full comparison and area calculations in working CSVs. An input manifest records file sizes and modification times, hashes of small source files, reference inventories, script hash, package versions and processing settings. Large raster and GeoPackage content is not fully hashed; those inputs must remain frozen. Check metadata fingerprints before and after execution. Recreate working files by rerunning the scripts.

The script does not import the prototype, use its cached points or read report confusion matrices. Reruns overwrite the named statistics. Source datasets are never modified. Missing inputs stop execution before new statistics are written. A failed run must not be treated as a fresh result even if outputs from an earlier run exist. Consult `status.json` before using results.

## Interpretation

UQ reference points outside known ACA reference areas can support an external reference assessment of ACA. However, they were supplied as UQ calibration data. The comparison remains asymmetric because UQ may have been trained or corrected using them. Reference clustering, expert-selection bias, imperfect labels, incomplete reference archives and differences in habitat observation dates also remain. A larger reference dataset does not by itself demonstrate a larger number of independent sites.

A suitable conclusion, when supported by the results, is that UQ agrees more closely with the available expert-labelled references than ACA outside the published ACA reference areas and within shared map coverage. This is stronger than a visual comparison but is not independent proof of a landscape-wide accuracy improvement. A blind reference audit at new sites would strengthen that claim. Additional coastal coverage should be described separately from classification accuracy.