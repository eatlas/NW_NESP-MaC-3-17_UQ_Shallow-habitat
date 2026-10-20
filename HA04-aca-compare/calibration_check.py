"""Compare final UQ map agreement at its calibration points with UQ's reported validation accuracy."""

import numpy as np
import pandas as pd
import geopandas as gpd

from compare import BASE, ROOT
from make_tables import markdown


REGIONS = ["Shark Bay", "West", "North West", "Gulf", "Offshore"]
BLOCK_M = 5000
REPLICATES = 1999


def bootstrap(group, classes, weights):
    # Resample 5 km Albers blocks within each reference class, matching the class-stratified sampling design.
    locations = gpd.GeoSeries(gpd.points_from_xy(group.longitude, group.latitude), crs=4326).to_crs(3577)
    frame = pd.DataFrame(dict(block_x=np.floor(locations.x / BLOCK_M).astype(np.int64), block_y=np.floor(locations.y / BLOCK_M).astype(np.int64),
                              reference=group.reference.to_numpy(), correct=(group.reference == group.uq).to_numpy()))
    strata = [frame[frame.reference == code].groupby(["block_x", "block_y"]).correct.agg(["sum", "count"]).to_numpy() for code in classes]
    generator = np.random.default_rng(42)
    estimates = []
    for _ in range(REPLICATES):
        producer = []
        for blocks in strata:
            draw = blocks[generator.integers(0, len(blocks), len(blocks))]
            producer.append(draw[:, 0].sum() / draw[:, 1].sum())
        estimates.append(100 * np.dot(weights, producer))
    return frame.groupby(["block_x", "block_y"]).ngroups, np.quantile(estimates, [0.025, 0.975])


def main():
    working = BASE / "working" / "HA04-aca-compare"
    output = BASE / "data" / "out" / "stats" / "HA04-aca-compare"
    output.mkdir(parents=True, exist_ok=True)
    points = pd.read_csv(working / "points.csv")
    report = pd.read_csv(ROOT / "report-validation.csv")
    rows = []
    for (region, objective), matrix in report.groupby(["region", "objective"]):
        classes = matrix.class_num.to_numpy()
        weights = matrix.reference_n.to_numpy() / matrix.reference_n.sum()
        group = points[(points.region == region) & (points.objective == objective) & points.unique_pixel & (points.uq_raw > 0)].copy()
        # Use the report's class codes: legacy Coral/Algae codes pooled, Light seagrass kept separate.
        pool = {16: 15, 17: 15} if objective == "benthic" else {}
        group["reference"] = group.reference_raw.replace(pool)
        group["uq"] = group.uq_raw.replace(pool)
        group = group[group.reference.isin(classes)]
        # The report matrices have no columns for other mapped classes, so these points are set aside.
        outside = ~group.uq.isin(classes)
        strict_pct = 100 * (group.reference == group.uq).mean()
        group = group[~outside]
        producer = (group.reference == group.uq).groupby(group.reference).mean().reindex(classes)
        blocks, interval = bootstrap(group, classes, weights)
        rows.append(dict(region=region, objective=objective, report_n=int(matrix.reference_n.sum()), report_pct=100 * matrix.correct.sum() / matrix.reference_n.sum(),
                         calibration_n=len(group), outside_class_n=int(outside.sum()), blocks=blocks, unweighted_pct=100 * (group.reference == group.uq).mean(), strict_pct=strict_pct,
                         calibration_pct=100 * np.dot(weights, producer.to_numpy()), calibration_low=interval[0], calibration_high=interval[1]))
    result = pd.DataFrame(rows)
    result["difference_pp"] = result.calibration_pct - result.report_pct
    # The validation sample came from the same segment library with similar clustering, so its
    # sampling error is taken to match the calibration estimate's; the difference then has sqrt(2) times the spread.
    half = np.sqrt(2) * (result.calibration_high - result.calibration_low) / 2
    result["difference_low"], result["difference_high"] = result.difference_pp - half, result.difference_pp + half
    paired = pd.read_csv(working / "summary.csv").query("buffer_m == 50")[["region", "objective", "difference_pp"]].rename(columns={"difference_pp": "uq_minus_aca_pp"})
    result = result.merge(paired, on=["region", "objective"], how="left", validate="one_to_one")
    result["region_order"] = result.region.map({name: index for index, name in enumerate(REGIONS)})
    result = result.sort_values(["objective", "region_order"]).drop(columns="region_order")
    result.to_csv(working / "calibration-check.csv", index=False)
    result[["objective", "region", "report_pct", "calibration_n", "calibration_pct", "calibration_low", "calibration_high", "difference_pp", "difference_low", "difference_high", "uq_minus_aca_pp", "blocks"]].to_csv(output / "calibration-check.csv", index=False)
    table = [[row.objective.title(), row.region, f"{row.report_pct:.0f}", f"{row.calibration_n:,}", f"{row.calibration_pct:.0f}", f"{row.calibration_low:.0f} to {row.calibration_high:.0f}",
              f"{row.difference_pp:+.0f}", f"{row.difference_low:+.0f} to {row.difference_high:+.0f}", "" if np.isnan(row.uq_minus_aca_pp) else f"{row.uq_minus_aca_pp:+.0f}"] for row in result.itertuples()]
    caption = ("**Table 4. Final UQ map agreement at its calibration points compared with UQ's reported validation accuracy.** Validation accuracy is from the report's confusion matrices for the Stage 1 maps. "
               "Calibration agreement uses one point per UQ pixel and the report's class set, weighted to the report's class proportions. Points mapped to a class outside the report matrix are set aside. "
               "Calibration intervals are 95% percentile intervals from 1,999 resamples of 5 km blocks within each class. The difference interval assumes the validation estimate has the same sampling spread. "
               "The final column repeats the UQ minus ACA difference from Table 2. Script: HA04-aca-compare/calibration_check.py\n")
    (output / "calibration-check-table.md").write_text(caption + "\n" + markdown(["Classification", "Region", "Validation (%)", "Calibration points", "Calibration (%)", "95% interval (%)", "Difference (pp)", "Approx. 95% interval (pp)", "UQ minus ACA (pp)"], table), encoding="utf-8")
    print(result.drop(columns=["report_n"]).round(1).to_string(index=False))


if __name__ == "__main__":
    main()
