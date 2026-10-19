# Comparing UQ and Allen Coral Atlas shallow habitat maps in northern and western Australia

Eric Lawrey - Australian Institute of Marine Science

*Technical analysis, 17 October 2026. This document accompanies the NESP Marine and Coastal Hub Project 3.17 habitat mapping dataset. It reports a comparative reference-agreement assessment, not an independent validation of both map products.*

## Abstract

The new University of Queensland (UQ) shallow habitat maps provide regionally adapted benthic and geomorphic classifications for northern and western Australia. We assessed the earlier Allen Coral Atlas (ACA) maps of the same area against the expert-labelled reference data developed for the new mapping, and compared the result with the UQ maps. The ACA maps are limited by both coverage and accuracy. ACA maps only 32% of the benthic habitat area and 26% of the geomorphic habitat area mapped by UQ. Large sections of the inshore coast have no ACA mapping, including Geraldton to southern Ningaloo, Eighty Mile Beach, the southern Joseph Bonaparte Gulf, the Sir Edward Pellew Group and western Cape York. Shark Bay was excluded from the accuracy comparison because ACA maps only 0.1% of the UQ habitat area there. Where both products provide mapping, they were evaluated at identical reference locations using harmonised classes. Locations within 50 m of published ACA reference polygons were excluded to avoid direct reuse of ACA training data. The paired samples contained 5,508 benthic and 7,594 geomorphic locations across four modelling regions. ACA agreement with the references ranged from 22.0% to 54.6% for benthic mapping and from 6.6% to 62.4% for geomorphic mapping. UQ agreement was higher in all eight comparisons, ranging from 70.3% to 92.0% and from 54.2% to 82.4%. Conditional 95% spatial-block bootstrap intervals for the difference were above zero in seven comparisons; West benthic mapping was the exception. Part of the geomorphic difference reflects classes added in the new mapping, particularly Rocky Reef, but large differences remained when these were removed. The references were supplied as UQ calibration data, so the UQ agreement values are optimistic and are not independent accuracy estimates. The ACA values are more informative. They indicate how well the existing ACA mapping matches current expert interpretation where ACA provides coverage.

## 1. Question and background

The project produced new 10 m benthic and geomorphic habitat maps for northern and western Australia using improved imagery, regional classification models and expert refinement (Markey et al., 2025). Earlier map comparisons were illustrated using selected image crops. Although useful for showing individual errors, a crop cannot establish whether apparent improvements extend across the available study-region references. Here we ask two related questions. **How much of the newly mapped habitat area was previously mapped by ACA? Where ACA does provide mapping, how closely does it agree with the expert-labelled references developed for the new mapping, and how does this compare with the final UQ maps?**

ACA maps shallow, optically accessible reef environments using satellite imagery and expert reference interpretation (Allen Coral Atlas, n.d.). Reference development includes field evidence, image segmentation and interpretation (Roelfsema et al., 2021). ACA mapping was framed around classical coral reef structure. It did not separately consider rocky reefs, and its coverage of turbid inshore coasts and shallow sediment environments is limited. The new UQ mapping extends into these environments. Comparing each product on a different spatial sample would confound classification performance with coverage. We therefore report coverage separately and compare both products only at reference points where both provide mapping.

ACA reference data are sparse across much of northern Australia. In the Northern Territory they are concentrated around Darwin, the Wessel Islands and the Cobourg Peninsula. Large sections of the coast were therefore mapped by ACA with little local reference data. The new reference data cover these areas more fully, including the Gulf of Carpentaria around Mornington Island and Groote Eylandt. Outside the immediate ACA reference areas they provide a useful test of how well the ACA classification generalised.

The supplied UQ calibration CSVs are substantially more useful for this paired question than isolated map crops, but they are not an independent validation set for UQ. The validation locations used for the UQ chapter were not available. We do not reconstruct those locations, split the calibration CSVs into a nominal holdout, or substitute the chapter's accuracy percentages for newly calculated UQ agreement. The historical chapter and this analysis concern different reference samples and map-processing stages.

## 2. Methods

### 2.1 Map products and reference observations

We used the final published UQ benthic and geomorphic GeoTIFF mosaics and the local ACA Western Australia and Timor and Arafura Seas map GeoPackages. The ACA package filenames identify March 2023 downloads. These dates are not assumed to describe all source imagery dates. UQ maps were evaluated after their final post-classification refinement, rather than at the Stage 1 processing version assessed in the historical report.

The ten UQ reference CSVs contain 73,233 rows: 31,344 benthic and 41,889 geomorphic. Each row provides a reference habitat code and point coordinates, together with predictor attributes used in model development. Labels were derived through expert interpretation informed by imagery and supporting observations. They are not treated as purpose-collected field ground truth. The source CSV determines the modelling region: Shark Bay, West, North West, Gulf or Offshore. These regions are distinct from the regionalisations used elsewhere in the project for area statistics. Shark Bay references (6,968 benthic and 9,210 geomorphic rows) were sampled but excluded from the comparison statistics. ACA maps only a thin strip along the outer ocean edge of Shark Bay, so a regional agreement figure would describe a small and unrepresentative part of that region.

Four published ACA reference datasets were used to screen potential overlap: Western Australia benthic and geomorphic references, and Timor Sea benthic and geomorphic references (Borrego-Acevedo et al., 2021a, 2021b; Tudman et al., 2021a, 2021b). They contain calibration and/or validation reference polygons; their individual training roles are not assumed. The archives were obtained manually because programmatic download links were unreliable. Copies and accompanying attribution metadata are supplied in the dataset's third-party mirror.

### 2.2 Excluding published ACA reference areas

The reference archives contain multipart features, often with many small, clustered polygon components. We split those features into components before buffering. All benthic and geomorphic components from both ACA regions contributed to the exclusion, irrespective of class. This conservative treatment allows for shared reference locations between classification workflows.

Each component was buffered by 50 m in the local WGS84 UTM zone selected from its centroid. This avoids buffering in angular units or relying on one projection for the full study area. Buffered polygons were transformed to WGS84 for spatial intersection with the UQ references. Points intersecting a polygon or its buffer boundary were excluded. The buffer used 32 segments per quadrant. An invalid geomorphic reference feature was repaired before component extraction.

The 50 m buffer is intended to stop ACA training and validation sites from being used directly in the comparison, and to remove the immediate surrounding area where reference labels are strongly spatially correlated. We repeated the assessment with no buffer and with a 100 m buffer. In the no-buffer scenario, reported as 0 m, points falling inside an ACA reference polygon are still excluded. It is therefore not an unscreened baseline. Increasing buffer sizes were checked to produce nested excluded sets. These exclusions reduce known local reuse but do not prove independence from all ACA training evidence or nearby interpretation sites.

### 2.3 Common habitat classes

For benthic mapping, Light seagrass (19) was pooled into Seagrass (14). Legacy Coral (16) and Algae (17) codes were pooled into Coral/Algae (15), following the original supplied palette. The source CSVs contained 30 legacy Coral rows and no legacy Algae rows. Raw codes were preserved. The comparison allowed six common benthic classes: Sand, Rubble, Rock, Seagrass, Coral/Algae and Microalgal Mats. A class entered a regional comparison only when retained reference observations existed.

Geomorphic reference classes were restricted to Shallow Lagoon, Deep Lagoon, Inner Reef Flat, Outer Reef Flat, Reef Crest, Terrestrial Reef Flat, Sheltered Reef Slope, Reef Slope, Plateau and Back Reef Slope. Deep, Sediment Slope, Small Reef and Rocky Reef were added in the new mapping to represent nearshore and deeper features better. They have no ACA equivalent and were excluded as reference classes. ACA Patch Reefs was not equated to UQ Small Reef. The UQ palette also contains a Patch Reef code (25), but it does not occur at any reference location. Valid map predictions outside the common reference classes remained disagreements. This prevents a product's unexpected class assignments from being silently removed from its error count.

The same expert team developed the ACA and UQ classifications, so the shared geomorphic classes are expected to be closely aligned in definition. Two exceptions are known. Rocky Reef was introduced in the new mapping because ACA interpreted habitat through a classical coral reef model and did not consider rocky reefs separately. It was not clear how rocky reefs should fit within the reef geomorphic scheme. As a result, UQ maps some locations as Rocky Reef where the reference labels, and ACA, use a reef zone class. Terrestrial Reef Flat was also difficult to apply consistently, and its use is likely to differ slightly between the two mapping programmes. Several years separate the ACA and UQ reference interpretation and so some drift in expert classification is therefore likely. We tested the effect of the two known differences by repeating the geomorphic comparison without points where UQ mapped Rocky Reef or where Terrestrial Reef Flat was the reference or either mapped class.

These common classes differ from the class subsets used in the historical report matrices. In particular, Microalgal Mats was not excluded automatically outside North West, and supported geomorphic classes were not dropped merely because they were absent from an old validation matrix.

### 2.4 Spatial sampling and paired selection

At every supplied reference location, we read the native full-resolution UQ pixel containing the point. No interpolation, raster reprojection or reduced-resolution overview was used. ACA predictions were obtained by exact point intersection with map polygons. Multiple intersecting polygons of the same class produced one prediction; different intersecting classes would be marked ambiguous. No ambiguous ACA predictions occurred among the retained supported references in the primary analysis.

After class harmonisation, we retained one reference per UQ native pixel, modelling region and classification. Pixels with conflicting reference labels were excluded rather than resolved using their mapped classes. We then removed unsupported reference classes and points within the ACA exclusion area. Points outside the UQ raster extent could not enter the primary native-pixel sample. Points inside the extent with NoData were retained for the coverage audit but not for thematic agreement.

Both products were scored only at locations with a valid UQ prediction and an unambiguous ACA prediction. UQ-only, ACA-only and neither-covered locations were counted separately. NoData was not treated as evidence of absent habitat or automatically scored as an incorrect class. Thus each regional agreement pair has exactly the same reference labels and denominator.

### 2.5 Agreement metrics and uncertainty

Overall reference agreement was the percentage of paired locations where the mapped class equalled the harmonised reference class. The paired difference was UQ agreement minus ACA agreement, expressed in percentage points. We also recorded locations where only UQ was correct and only ACA was correct. Their difference divided by the paired sample size reproduces the agreement difference.

Confusion matrices use reference classes as rows and mapped classes as columns. Per-class producer's agreement uses the reference row total, while user's agreement uses the mapped column total. These describe the selected reference sample. They are not area-weighted estimates of regional class accuracy or predictive value.

Uncertainty in the agreement difference was estimated using a paired spatial block bootstrap, a form of cluster bootstrap in which groups of observations are resampled together. Nearby reference points can share imagery, water conditions and interpretation, so treating them as independent observations could understate uncertainty. For each region and classification, retained paired locations were assigned to a fixed square grid with cells 5 km on a side in GDA94 Australian Albers (EPSG:3577). The term paired means that the UQ prediction, ACA prediction and reference label at each location remained together throughout resampling.

Only cells containing retained paired locations entered the bootstrap. If there were N occupied cells, each replicate selected N cells at random with replacement, giving each occupied cell equal probability on every draw. A replicate could therefore omit some cells and select others more than once. All reference points in a selected cell contributed together; a cell selected twice contributed all its observations twice. Individual points were not selected within cells, and map predictions were not extracted again. This preserves the observed grouping of points within cells while varying the contribution of spatial groups to the regional comparison.

Each replicate recalculated the agreement difference across all points in the selected cells, retaining the point-weighted comparison despite unequal numbers of points per cell. The central 95% of the differences from 1,999 replicates defined the reported interval. We also tested 1 and 10 km cells to assess sensitivity to the grouping scale. These intervals describe variation among the observed spatial groups, not uncertainty from reference-selection bias or reuse of calibration data.

### 2.6 Coverage of the ACA mapping

There are no boundary polygons describing the extent of either mapping. We therefore estimated coverage directly from the mapped habitat. Native UQ pixels were sampled on a systematic grid of every eighth pixel in each direction, approximately 80 m apart. Each sample was tested for a valid UQ class and for the presence of any ACA map polygon of the same classification, rasterised at the sample centres. Sample areas were calculated on the sphere and summed by IMCRA v4.0 meso-scale bioregion (Department of Climate Change, Energy, the Environment and Water, 2023). The geomorphic area includes the UQ Deep class, which is limited to deep reef banks. Total UQ areas from this sample were within 0.3% of the full-resolution areas reported elsewhere in the project. The estimate measures where ACA provides any mapping, not whether that mapping is correct.

## 3. Limitations and interpretation

The principal limitation for the UQ results is reference provenance. These observations were supplied as UQ calibration data, while known ACA reference areas were excluded. UQ may therefore benefit from training or subsequent correction using the retained labels, and its agreement values are optimistic. The comparison is a much stronger external reference check of ACA than of UQ. Neither a positive paired difference nor a bootstrap interval above zero removes that advantage. The analysis cannot quantify how much of the observed difference is attributable to improved generalisation rather than calibration dependence.

Excluding the published ACA polygons does not establish that all retained evidence was unseen by ACA. Their completeness for the map versions assessed is unconfirmed. References outside the 50 m buffer may share imagery, surveys or interpretation with excluded sites. The reverse issue also matters: exclusion can remove large portions of particular environments, so retained observations need not represent each region's original habitat distribution.

The references were not selected through a probability sample of the full landscape. Classes, geographic clusters and well-interpreted sites have unequal representation. Overall agreement is therefore conditional on the selected sample composition. It is not the percentage of the mapped marine area that is correct. We report regions separately rather than presenting a pooled landscape accuracy that would conceal these weighting differences.

The block bootstrap represents variation among observed spatial groups, not all sources of uncertainty. Block sizes were sensitivity choices, not estimated independence distances. Dependence can cross block boundaries. The intervals do not include training reuse, uncertain reference labels, incomplete overlap screening or systematic interpretation differences. Regions and classes with few retained observations require particular caution. Treating thousands of nearby pixels as independent field observations would overstate the strength of the evidence.

The maps differ in imagery, processing, spatial support and potentially habitat observation dates. Native point sampling is repeatable but is not a common-footprint comparison between a 10 m raster pixel and the finer boundaries represented by ACA polygons. Real habitat change and reference positional uncertainty may contribute to disagreement. Broad class harmonisation also removes some distinctions made by UQ, particularly between dense and sparse seagrass. This assessment does not evaluate every product-specific class or habitat component. Drift in expert interpretation between the two mapping programmes may also contribute to the measured ACA disagreement, and cannot be separated from map error with these data.

Shared coverage avoids penalising ACA simply for not mapping additional coastal and sediment areas. It also limits the agreement results to where both products provide predictions. ACA coverage is concentrated on clearer-water reefs, so the paired samples under-represent the turbid inshore coasts that make up much of the new mapping. The agreement values should therefore be read as applying to the parts of each region that ACA mapped. They do not describe ACA accuracy across each whole region, and they cannot say how well ACA would have performed in the areas it did not map.

## 4. Results

### 4.1 Coverage of the ACA mapping

ACA maps 32% of the 26,633 km² of benthic habitat and 26% of the 34,096 km² of geomorphic habitat mapped by UQ (Table 1). Coverage is uneven. ACA mapping is most complete on the clearer-water reefs of the Kimberley, Ningaloo, Tiwi Islands, Cobourg Peninsula and Wessel Islands, where it covers 64 to 84% of the UQ habitat area. It is largely absent from the turbid and sediment-dominated inshore coast. There is effectively no ACA mapping from Geraldton to southern Ningaloo (Central West Coast, Zuytdorp and Shark Bay bioregions), along Eighty Mile Beach, in the southern Joseph Bonaparte Gulf (Cambridge-Bonaparte), across the Sir Edward Pellew Group, or along western Cape York. Coverage is partial in the inshore Pilbara from north-eastern Exmouth Gulf to Dampier and Wickham, along the Dampier Peninsula and Port Smith coast (Canning), in King Sound and in Van Diemen Gulf, at 12 to 29%. In the Gulf of Carpentaria, ACA covers parts of the Wellesley Islands and Groote Eylandt but little else. Shark Bay contains a quarter of the UQ benthic habitat area, but only 0.1% of it is mapped by ACA, on the outer ocean edge.

**Table 1. UQ mapped habitat area and the percentage also mapped by ACA, by IMCRA v4.0 meso-scale bioregion.** Bioregions are listed approximately from south-west to east. Areas were estimated from a systematic sample of native UQ pixels at about 80 m spacing. The geomorphic area includes the UQ Deep class on deep reef banks, which ACA does not map; this accounts for most of the difference in Oceanic Shoals and Pilbara (offshore). Arafura and Torres Strait, each with less than 40 km² of UQ habitat, are included only in the total.

| IMCRA meso-scale bioregion | UQ benthic (km²) | Also mapped by ACA (%) | UQ geomorphic (km²) | Also mapped by ACA (%) |
|:---|---:|---:|---:|---:|
| Central West Coast | 245 | 0 | 457 | 0 |
| Abrolhos Islands | 807 | 38 | 998 | 32 |
| Zuytdorp | 370 | 1 | 417 | 2 |
| Shark Bay | 6,529 | <1 | 6,531 | <1 |
| Ningaloo | 753 | 77 | 939 | 64 |
| Pilbara (nearshore) | 2,355 | 29 | 2,511 | 29 |
| Pilbara (offshore) | 1,561 | 66 | 2,853 | 37 |
| Northwest Shelf | 14 | 72 | 142 | 7 |
| Eighty Mile Beach | 839 | 0 | 1,746 | 0 |
| Canning | 1,196 | 20 | 1,967 | 12 |
| King Sound | 187 | 29 | 197 | 27 |
| Kimberley | 2,785 | 70 | 2,860 | 69 |
| Bonaparte Gulf | 78 | 40 | 130 | 25 |
| Cambridge-Bonaparte | 298 | 0 | 298 | 0 |
| Oceanic Shoals | 3 | 0 | 672 | 0 |
| Anson Beagle | 723 | 66 | 727 | 66 |
| Tiwi | 135 | 78 | 135 | 78 |
| Van Diemens Gulf | 274 | 25 | 275 | 25 |
| Cobourg | 476 | 84 | 477 | 84 |
| Arnhem Wessel | 1,092 | 71 | 1,094 | 71 |
| Groote | 1,090 | 39 | 1,101 | 39 |
| Pellew | 944 | 0 | 958 | 0 |
| Wellesley | 1,439 | 35 | 1,476 | 34 |
| Karumba-Nassau | 368 | 1 | 372 | 1 |
| Carpentaria | 83 | 0 | 104 | 0 |
| West Cape York | 330 | 0 | 334 | 0 |
| Outside IMCRA meso-scale bioregions | 1,597 | 49 | 4,258 | 24 |
| **All** | **26,633** | **32** | **34,096** | **26** |

This lack of coverage is a limitation of the ACA mapping in its own right, separate from its accuracy. Users of ACA in this region would have had no habitat information for about two thirds of the shallow habitat area now mapped. The gaps are concentrated in particular environments rather than spread evenly. The agreement results that follow therefore describe ACA where it exists, mainly on clearer-water reefs, and are not representative of the whole of each region. The reverse also occurs to a lesser extent. ACA maps about 4,900 km² of habitat outside the UQ mapping, mainly in the Arnhem Wessel, Kimberley and Cobourg bioregions. This was not investigated further.

### 4.2 Reference screening and available comparisons

Only a subset of the supplied UQ reference points could be used to compare the two maps. We removed duplicate or conflicting references, restricted the comparison to shared habitat classes, excluded points within published ACA reference polygons or their 50 m buffers, and required both maps to provide a prediction at each location. This left 5,508 benthic and 7,594 geomorphic reference locations across the four compared regions. These retained locations form the common samples used to score both products in Table 2.

The exclusions affected regions unevenly. In Offshore, the ACA reference-area exclusion removed about nine tenths of the eligible references, leaving a much smaller sample for comparison. Screening therefore changed which locations and habitats were represented, not just the number of observations. The agreement results describe the retained locations and should not be assumed to represent the full range of habitats in each region.

### 4.3 Regional paired agreement

Regional agreement was assessed on the retained paired samples after the primary 50 m exclusion (Table 2). Both products were compared with the same reference labels at identical locations, so their agreement percentages have a common denominator within each region and classification. The intervals describe uncertainty in the UQ-minus-ACA difference under the spatial block-bootstrap procedure in Section 2.5. The occupied 5 km cell counts indicate the number of spatial groups available for resampling; they are not additional reference points or exclusion buffers.

UQ agreement exceeded ACA agreement in all eight comparisons (Table 2). Benthic agreement ranged from 70.3% to 92.0% for UQ and from 22.0% to 54.6% for ACA. Geomorphic agreement ranged from 54.2% to 82.4% for UQ and from 6.6% to 62.4% for ACA. These are newly calculated final-product results on the same reference samples, not the UQ chapter's historical validation percentages. Because the references were used to calibrate UQ, the UQ values are optimistic. The ACA values are the more informative figures in this table.

**Table 2. Paired reference agreement after the 50 m ACA-reference exclusion.** Shark Bay is excluded because ACA maps less than 1% of its habitat area. Differences are UQ minus ACA in percentage points (pp). Intervals are conditional 95% percentile intervals from 1,999 paired resamples of occupied 5 km blocks. These are UQ calibration references, not independent UQ validation observations. Intervals do not account for training-data asymmetry or reference-selection bias.

| Classification | Region | Paired points | UQ (%) | ACA (%) | Difference (pp) | 95% interval (pp) | 5 km blocks |
|:---|:---|---:|---:|---:|---:|:---|---:|
| Benthic | West | 1,472 | 70.3 | 54.6 | 15.7 | -1.7 to 39.4 | 104 |
| Benthic | North West | 1,951 | 78.3 | 33.1 | 45.2 | 38.5 to 50.9 | 243 |
| Benthic | Gulf | 1,722 | 92.0 | 22.0 | 70.0 | 53.9 to 80.6 | 44 |
| Benthic | Offshore | 363 | 81.8 | 37.2 | 44.6 | 33.7 to 56.5 | 33 |
| Geomorphic | West | 3,312 | 82.4 | 40.5 | 41.9 | 33.0 to 51.3 | 118 |
| Geomorphic | North West | 1,514 | 54.2 | 6.6 | 47.6 | 32.0 to 68.1 | 164 |
| Geomorphic | Gulf | 2,151 | 66.5 | 6.7 | 59.8 | 35.8 to 76.0 | 43 |
| Geomorphic | Offshore | 617 | 76.2 | 62.4 | 13.8 | 6.0 to 23.5 | 63 |

The primary interval was above zero in seven comparisons. West benthic mapping had a positive estimated difference of 15.7 pp, but its interval extended from -1.7 to 39.4 pp. Evidence for that regional advantage is therefore less conclusive under the primary uncertainty analysis. Differences in Table 2 were calculated before rounding, so subtracting displayed percentages may not reproduce the displayed difference exactly.

### 4.4 Coverage of the reference sample

Shared map coverage was a further constraint on the comparison. After class filtering and the ACA reference-area exclusion, fewer than half of the remaining references had predictions from both products: 39% for benthic mapping and 47% for geomorphic mapping. Most of the other references had only UQ coverage or no prediction from either product. They were not scored as classification errors because an absent prediction is different from an incorrect habitat label.

The agreement results therefore describe locations where both products provide mapping, not the full reference sample or mapped area. The mapped-area estimates in Table 1 address the separate question of how much habitat ACA covers. Detailed reference-coverage counts are retained in the working results and can be regenerated.

### 4.5 Sensitivity to exclusion distance

Increasing the exclusion distance around the ACA reference polygons from 50 to 100 m changed each regional agreement difference by less than 1.9 percentage points. UQ agreement remained higher in all eight comparisons at every tested distance. The results were therefore not highly sensitive to widening the primary 50 m exclusion. Adding the initial buffer had a larger effect on the Offshore benthic sample, so this limited sensitivity applies to extending the buffer rather than to exclusion as a whole.

### 4.6 Geomorphic class alignment

The Rocky Reef and Terrestrial Reef Flat classes account for much of the low accuracy in the geomorphic classification in the Gulf and North West (Table 3). UQ mapped Rocky Reef at 546 of the 2,151 Gulf points, which explains 546 of its 720 disagreements there. Most of these points were labelled Back Reef Slope or Sheltered Reef Slope in the references. This reflects the introduction of Rocky Reef in the final UQ maps, and illustrates that the class does not fit cleanly into the reef zone scheme. Terrestrial Reef Flat was involved at 739 Gulf points and 676 North West points, mostly where ACA mapped Terrestrial Reef Flat over references labelled as reef flat or reef crest.

Removing these points did not close the gap. ACA agreement in the remaining points was 2.3% in the Gulf and 9.8% in the North West. Most of the remaining ACA disagreement came from Back Reef Slope, which ACA mapped at 586 of 982 remaining Gulf disagreements and 449 of 683 remaining North West disagreements. These points were mostly labelled Inner Reef Flat in the Gulf and Reef Crest or Outer Reef Flat in the North West. This pattern is consistent with ACA having little local reference data on the turbid reefs of these regions. In contrast, Offshore and West were little affected by either class.

**Table 3. Geomorphic agreement after removing points affected by known class differences, 50 m exclusion.** Points were removed where UQ mapped Rocky Reef or where Terrestrial Reef Flat was the reference class or either mapped class. Some points meet both conditions.

| Region | Paired points | UQ mapped Rocky Reef | Terrestrial Reef Flat involved | Remaining points | UQ (%) | ACA (%) |
|:---|---:|---:|---:|---:|---:|---:|
| West | 3,312 | 258 | 128 | 2,948 | 89.8 | 38.9 |
| North West | 1,514 | 237 | 676 | 757 | 67.6 | 9.8 |
| Gulf | 2,151 | 546 | 739 | 1,005 | 86.7 | 2.3 |
| Offshore | 617 | 0 | 0 | 617 | 76.2 | 62.4 |

### 4.7 Class-specific qualifications

We examined agreement for individual habitat classes to assess whether UQ's higher overall agreement also applied to each class. It did not: ACA matched a greater proportion of the West Rubble references than UQ, at 58% compared with 33%. Seagrass showed a contrasting weakness in ACA, which identified relatively few of the seagrass references in the Gulf, North West and West, usually assigning them to Sand, Rubble or Coral/Algae. Overall agreement therefore conceals differences that matter when choosing a map for a particular habitat.

These class-level comparisons also require caution. Some apparent disagreements reflect changes in class definitions, particularly the introduction of Rocky Reef discussed in Section 4.6. Other classes had too few retained references to support conclusions: Offshore had no paired seagrass references, and Microalgal Mats had only a few observations. The findings describe agreement with the available references, not the accuracy of each habitat class across its full mapped extent.

## 5. Discussion and conclusion

The ACA mapping of this region has two separate limitations. Coverage is the more basic one. ACA maps about a third of the shallow habitat area now mapped by UQ, and almost none of Shark Bay, the coast from Geraldton to southern Ningaloo, Eighty Mile Beach, the southern Joseph Bonaparte Gulf, the Sir Edward Pellew Group or western Cape York. Accuracy is the second. Where ACA does provide mapping, it agrees with current expert interpretation at 22 to 55% of benthic reference points and 7 to 62% of geomorphic reference points, depending on region. Agreement is lowest in the Gulf and North West, where ACA had little local reference data. Some geomorphic disagreement comes from the Rocky Reef and Terrestrial Reef Flat classes, but most remains when these are removed.

The UQ maps reproduce the reference interpretation more closely in every regional comparison. This supports a broad improvement within shared coverage, rather than an advantage restricted to one illustrated site. However, these data do not support a statement that an independently validated accuracy increase of the reported magnitude has been established. UQ training dependence remains, spatial screening cannot eliminate all shared evidence, and classification drift between the two programmes cannot be separated from map error. A positive difference can contain both real map improvement and advantages arising from reference selection or calibration. Their contributions cannot be separated here.

The most defensible report statement is: **"The Allen Coral Atlas maps only about a third of the shallow habitat area mapped by the new UQ mapping, with large gaps along the inshore coast including Shark Bay. Within shared map coverage and outside a 50 m buffer of published ACA reference areas, ACA agreed with the expert-labelled reference dataset at 22 to 55% of benthic points and 7 to 62% of geomorphic points across four modelling regions. The final UQ maps showed higher agreement in all eight comparisons, with conditional spatial-block intervals supporting a positive difference in seven. Because the references were supplied as UQ calibration data, the UQ values are optimistic and this is comparative reference agreement rather than independent validation of the UQ product."**

Tables 1 and 2 are suitable for the main report provided their sample sizes and qualifications accompany them. An independent audit using blind interpretation or suitable field observations at new, spatially distributed sites would strengthen the assessment of generalisation. Sampling both map-agreement and disagreement sites with known selection probabilities would be preferable to selecting only apparent errors.

## 6. Reproducibility and data availability

The analysis ran on 17 October 2026 using the existing `habitat-mosaic` environment, GDAL 3.13.3, GeoPandas 1.2.0 and Shapely 2.1.2. [compare.py](compare.py) performs map sampling, exclusion and statistics. [verify_results.py](verify_results.py) reconstructs saved denominators, confusion counts, class metrics and paired effects from the point outputs and checks input fingerprints. [make_tables.py](make_tables.py) generates the report table and separate coverage, sensitivity and class-alignment tables. [coverage.py](coverage.py) estimates the ACA coverage of the UQ mapped area. [README.md](README.md) gives execution instructions, while [SPECIFICATION.md](SPECIFICATION.md) records the analysis decisions.

Only the tables presented in this paper are supplied under `data/out/stats/HA04-aca-compare` in the accompanying dataset download. These comprise mapped-area coverage, primary paired agreement and geomorphic class alignment. Point-level results, full scenario summaries, class metrics, confusion counts, bootstrap results, diagnostic tables and the run manifest are retained under `working/HA04-aca-compare`. These working files are not distributed or tracked in Git. They can be recreated by running the scripts. The manifest records source metadata, small-file SHA-256 hashes, file sizes, modification times and software settings. Large raster and GeoPackage inputs were checked using metadata fingerprints rather than full content hashes. Input fingerprints were unchanged during the analysis.

All seven synthetic tests passed. Consistency checks validated 73,233 point rows, 24 regional scenarios, 48 confusion matrices and 72 uncertainty estimates against the saved point table. These checks re-derive the summary statistics from the sampled points; they do not repeat the map sampling, exclusion or bootstrap. They support computational consistency but do not resolve scientific reference bias. The analysis does not use the prototype's cached results or the historical report matrices.

The project data bundle includes published outputs, mirrored ACA reference polygons with attribution metadata, and previews. The [global README](../README.md#mirrored-third-party-data-and-manual-downloads) records original source DOIs and manual rebuild instructions. ACA map inputs remain subject to their source terms. No licence for underlying contributed field data or source imagery is inferred from the CC BY 4.0 reference-polygon licences.

## AI use disclosure

Eric Lawrey formulated the research question, directed the methods and interpretation, provided regional and methodological knowledge, assisted with data acquisition, and reviewed the analysis and text. GitHub Copilot GPT-6.1 Sol assisted with the initial investigation, analysis code, computational checks and paper draft (1.4 hr). GitHub Copilot Claude Opus 5.5 subsequently reviewed and extended the analysis and revised the paper under Lawrey's direction (2.2 hr). A third Sol 6.1 session (2.4 hr), supported explanatory code review, clarification of the methods, output organisation and author-directed revision of the paper. AI assistance contributed substantially to coding and drafting; Lawrey reviewed the outputs and remains responsible for the content.

As a measure of human input, the three Copilot sessions contained 52 content-related requests totalling 3,524 words, excluding pasted Markdown table rows, attachments and automatic context. The initial GPT-6.1 Sol session contributed 16 requests (1,544 words), the Claude Opus 5.5 session two requests (672 words), and the review and revision session 34 requests (1,308 words). At the 18 October 2026 snapshot, this was about 71% of the paper's 4,964 prose words, placing it in the comparable-input band of the working convention described in [Measurement scope and counting method](INPUT-METRIC.md). These inputs include questions about the analysis, coding guidance and editorial direction, not just supplied paper prose. Seven disclosure and metric requests added 472 words and were excluded from the ratio. Work outside chat, such as data acquisition and review, is not included in the word count. The ratio describes text volume, not an authorship percentage or a measure of intellectual contribution.

The completed code was manually reviewed (1.25 hr) to determine if it met expectations. The generated point results were visualised and reviewed in QGIS. During the review and revision session, Lawrey questioned the spatial extraction and bootstrap calculations, requested explanatory comments, and directed the separation of publication tables from intermediate verification files. He also directed revisions to explain the purpose of each assessment and emphasise its main finding and qualification rather than lists of numerical details.

## References

Markey, K., Lyons, M., Borrego-Acevedo, R., Roe, M., Lawrey, E., Phinn, S., and Roelfsema, C. (2025). *Shallow benthic and geomorphic habitat maps for Northern and Western Australia (NESP MaC 3.17, UQ, UNSW, AIMS).* eAtlas. https://doi.org/10.26274/QEH6-P243

Allen Coral Atlas (n.d.). *Science and Methods.* https://allencoralatlas.org/methods/

Department of Climate Change, Energy, the Environment and Water (2023). *Integrated Marine and Coastal Regionalisation of Australia (IMCRA) v4.0 - Meso-scale Bioregions.* https://fed.dcceew.gov.au/datasets/erin::integrated-marine-and-coastal-regionalisation-of-australia-imcra-v4-0-meso-scale-bioregions/about

Roelfsema, C. M., et al. (2021). *Workflow for the Generation of Expert-Derived Training and Validation Data: A View to Global Scale Habitat Mapping.* Frontiers in Marine Science, 8, 643381. https://doi.org/10.3389/fmars.2021.643381

Borrego-Acevedo, R., Roelfsema, C., et al. (2021a). *Western Australia Benthic Type Reference Sample*, version 1. Figshare. https://doi.org/10.6084/m9.figshare.14622759.v1

Borrego-Acevedo, R., Roelfsema, C., et al. (2021b). *Western Australia Geomorphic Type Reference Sample*, version 1. Figshare. https://doi.org/10.6084/m9.figshare.14622750.v1

Tudman, P., Borrego-Acevedo, R., et al. (2021a). *Timor Sea Benthic Type Reference Sample*, version 1. Figshare. https://doi.org/10.6084/m9.figshare.14120894.v1

Tudman, P., Borrego-Acevedo, R., et al. (2021b). *Timor Sea Geomorphic Type Reference Sample*, version 1. Figshare. https://doi.org/10.6084/m9.figshare.14120891.v1