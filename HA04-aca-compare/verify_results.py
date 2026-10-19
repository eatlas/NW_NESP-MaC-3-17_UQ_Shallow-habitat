"""Independently reconstruct saved paired counts and agreement from point outputs."""

import hashlib
import json

import numpy as np
import pandas as pd

from compare import BASE, EXCLUDED_REGIONS, LABELS, ROOT, fingerprint, inputs


def main():
    output = BASE / "working" / "HA04-aca-compare"
    points = pd.read_csv(output / "points.csv")
    summary = pd.read_csv(output / "summary.csv")
    confusion = pd.read_csv(output / "confusion.csv")
    uncertainty = pd.read_csv(output / "uncertainty.csv")
    classes = pd.read_csv(output / "classes.csv")
    manifest = json.loads((output / "manifest.json").read_text())
    # The hash covers exact source bytes, including comments, not just executable code.
    assert manifest["code_sha256"] == hashlib.sha256((ROOT / "compare.py").read_bytes()).hexdigest(), "Analysis code changed after execution"
    assert manifest["files"] == fingerprint(inputs(BASE / "data")), "Inputs changed after analysis"
    # Four retained regions x two objectives x three buffers; three block sizes per scenario.
    assert len(summary) == 24 and len(uncertainty) == 72
    assert not summary.region.isin(EXCLUDED_REGIONS).any()
    assert not summary.duplicated(["buffer_m", "region", "objective"]).any()
    assert (~points.region.isin(EXCLUDED_REGIONS)).sum() == int(summary[summary.buffer_m == 50].input_n.sum())
    assert ((points.excluded_0m <= points.excluded_50m) & (points.excluded_50m <= points.excluded_100m)).all()
    for row in summary.itertuples():
        # Rebuild eligibility from saved point flags rather than trusting summary counts.
        raw = points[(points.region == row.region) & (points.objective == row.objective)]
        eligible = raw[raw.unique_pixel & raw.reference.isin(LABELS[row.objective])]
        retained = eligible[~eligible[f"excluded_{row.buffer_m}m"]]
        paired = retained[(retained.uq > 0) & (retained.aca > 0)]
        assert len(raw) == row.input_n and len(eligible) == row.eligible_n
        assert len(retained) == row.retained_n and len(paired) == row.paired_n
        assert len(eligible) - len(retained) == row.excluded_n
        assert row.uq_only_n + row.aca_only_n + row.neither_n + row.paired_n == row.retained_n
        unique_keys = ["region", "objective", "uq_row", "uq_col"]
        assert not paired.duplicated(unique_keys).any()
        for product in ["uq", "aca"]:
            saved = confusion[(confusion.buffer_m == row.buffer_m) & (confusion.region == row.region) & (confusion.objective == row.objective) & (confusion["product"] == product)]
            assert saved.n.sum() == len(paired)
            correct = int((paired.reference == paired[product]).sum())
            assert saved.loc[saved.reference == saved.prediction, "n"].sum() == correct
            if len(paired):
                assert np.isclose(100 * correct / len(paired), getattr(row, f"{product}_agreement_pct"))
            # Compare nonzero confusion cells; saved matrices also include empty combinations.
            expected = paired.groupby(["reference", product]).size().to_dict()
            assert {(int(item.reference), int(item.prediction)): int(item.n) for item in saved.itertuples() if item.n} == expected
            details = classes[(classes.buffer_m == row.buffer_m) & (classes.region == row.region) & (classes.objective == row.objective) & (classes["product"] == product)]
            assert details.reference_n.sum() == len(paired) and details.mapped_n.sum() == len(paired)
            # Producer agreement conditions on reference class; user agreement on mapped class.
            for item in details.itertuples():
                if item.reference_n:
                    assert np.isclose(100 * item.correct / item.reference_n, item.producer_agreement_pct)
                if item.mapped_n:
                    assert np.isclose(100 * item.correct / item.mapped_n, item.user_agreement_pct)
        if len(paired):
            assert np.isclose(row.difference_pp, row.uq_agreement_pct - row.aca_agreement_pct)
            assert np.isclose(row.difference_pp, 100 * (row.uq_only_correct - row.aca_only_correct) / row.paired_n)
    assert (uncertainty.low_pp.dropna() <= uncertainty.high_pp.dropna()).all()
    assert (uncertainty.replicates == 1999).all()
    print(f"PASS: {len(points):,} points, 24 regional scenarios, 48 confusion matrices, class metrics, 72 uncertainty estimates and input fingerprints.")


if __name__ == "__main__":
    main()