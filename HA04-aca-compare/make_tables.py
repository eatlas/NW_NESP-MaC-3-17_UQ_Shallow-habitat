"""Generate publication tables from verified regional comparison outputs."""

import pandas as pd

from compare import BASE, EXCLUDED_REGIONS, LABELS
from verify_results import main as verify_results


def markdown(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "|".join([":---"] + ["---:"] * (len(headers) - 1)) + "|"] + ["| " + " | ".join(map(str, row)) + " |" for row in rows]) + "\n"


def main():
    # Refuse to publish tables if saved counts or analysis provenance no longer verify.
    verify_results()
    output = BASE / "data" / "out" / "stats" / "HA04-aca-compare"
    output.mkdir(parents=True, exist_ok=True)
    working = BASE / "working" / "HA04-aca-compare"
    summary = pd.read_csv(working / "summary.csv")
    uncertainty = pd.read_csv(working / "uncertainty.csv")
    # The primary report uses a 50 m exclusion and 5 km bootstrap blocks.
    # Require exactly one uncertainty record per regional comparison when joining.
    primary = summary[summary.buffer_m == 50].merge(uncertainty[(uncertainty.buffer_m == 50) & (uncertainty.block_m == 5000)], on=["buffer_m", "region", "objective"], validate="one_to_one")
    primary["region_order"] = primary.region.map({"West": 1, "North West": 2, "Gulf": 3, "Offshore": 4})
    primary = primary.sort_values(["objective", "region_order"]).drop(columns="region_order")
    primary.to_csv(working / "report_table.csv", index=False)
    primary[["objective", "region", "paired_n", "uq_agreement_pct", "aca_agreement_pct", "difference_pp", "low_pp", "high_pp", "blocks"]].to_csv(output / "report_table.csv", index=False)
    rows = [[row.objective.title(), row.region, f"{row.paired_n:,}", f"{row.uq_agreement_pct:.1f}", f"{row.aca_agreement_pct:.1f}", f"{row.difference_pp:.1f}", f"{row.low_pp:.1f} to {row.high_pp:.1f}", row.blocks] for row in primary.itertuples()]
    caption = "**Table 2. Paired reference agreement after the 50 m ACA-reference exclusion.** Both products were evaluated at identical expert-labelled reference locations with valid coverage and harmonised classes. Shark Bay is excluded because ACA maps less than 1% of its habitat area. Differences are UQ minus ACA in percentage points (pp). Intervals are conditional 95% percentile intervals from 1,999 paired spatial cluster-bootstrap resamples of occupied 5 km blocks. These are UQ calibration references, not independent UQ validation observations. Intervals do not account for training-data asymmetry or reference-selection bias. Script: HA04-aca-compare/make_tables.py\n"
    (output / "report-table.md").write_text(caption + "\n" + markdown(["Classification", "Region", "Paired points", "UQ (%)", "ACA (%)", "Difference (pp)", "95% interval (pp)", "5 km blocks"], rows), encoding="utf-8")
    rows = [[row.objective.title(), row.region, f"{row.eligible_n:,}", f"{row.excluded_n:,}", f"{row.retained_n:,}", f"{row.paired_n:,}", f"{row.uq_only_n:,}", f"{row.aca_only_n:,}", f"{row.neither_n:,}"] for row in primary.itertuples()]
    (working / "coverage-table.md").write_text(markdown(["Classification", "Region", "Eligible", "Excluded", "Retained", "Both", "UQ only", "ACA only", "Neither"], rows), encoding="utf-8")
    rows = []
    for row in primary.itertuples():
        # Show buffer sensitivity as the paired difference with its changing sample count.
        scenarios = summary[(summary.objective == row.objective) & (summary.region == row.region)].set_index("buffer_m")
        rows.append([row.objective.title(), row.region] + [f"{scenarios.loc[distance, 'difference_pp']:.1f} ({int(scenarios.loc[distance, 'paired_n']):,})" for distance in [0, 50, 100]])
    (working / "sensitivity-table.md").write_text(markdown(["Classification", "Region", "0 m difference (n)", "50 m difference (n)", "100 m difference (n)"], rows), encoding="utf-8")
    points = pd.read_csv(working / "points.csv")
    # Reconstruct the primary geomorphic pairs before the class-alignment sensitivity check.
    paired = points[points.unique_pixel & ~points.excluded_50m & (points.objective == "geomorphic") & points.reference.isin(LABELS["geomorphic"]) & (points.uq > 0) & (points.aca > 0) & ~points.region.isin(EXCLUDED_REGIONS)]
    # Rocky Reef (27) has no ACA equivalent and Terrestrial Reef Flat (16) was applied inconsistently between the mapping programmes.
    aligned = paired[(paired.uq != 27) & (paired.reference != 16) & (paired.uq != 16) & (paired.aca != 16)]
    rows = []
    for region in ["West", "North West", "Gulf", "Offshore"]:
        full, subset = paired[paired.region == region], aligned[aligned.region == region]
        rows.append([region, f"{len(full):,}", f"{(full.uq == 27).sum():,}", f"{((full.reference == 16) | (full.uq == 16) | (full.aca == 16)).sum():,}", f"{len(subset):,}",
                     f"{100 * (subset.uq == subset.reference).mean():.1f}", f"{100 * (subset.aca == subset.reference).mean():.1f}"])
    caption = "**Table 3. Geomorphic agreement after removing points affected by known class differences, 50 m exclusion.** Points were removed where UQ mapped Rocky Reef or where Terrestrial Reef Flat was the reference class or either mapped class. Some points meet both conditions. UQ and ACA percentages are agreement with the reference labels among the remaining paired points. These are UQ calibration references, not independent UQ validation observations. Script: HA04-aca-compare/make_tables.py\n"
    (output / "class-alignment-table.md").write_text(caption + "\n" + markdown(["Region", "Paired points", "UQ mapped Rocky Reef", "Terrestrial Reef Flat involved", "Remaining points", "UQ (%)", "ACA (%)"], rows), encoding="utf-8")
    print((output / "report-table.md").read_text())


if __name__ == "__main__":
    main()