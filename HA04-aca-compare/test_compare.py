"""Focused checks for spatial extraction, exclusion, harmonisation and pairing."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import numpy as np
import pandas as pd
from osgeo import gdal, ogr, osr
from shapely.geometry import Polygon, box

import make_tables
from compare import bootstrap, class_metrics, exclusion_mask, harmonise, inputs, polygon_sample, raster_sample, select_pixels, summarise


class CompareTests(unittest.TestCase):
    def test_missing_inputs_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                inputs(Path(directory))

    def test_buffer_and_hole(self):
        # Build geometry in metres so the 50 m threshold has a known physical meaning.
        polygon = Polygon([(500000, 7500000), (500100, 7500000), (500100, 7500100), (500000, 7500100)],
                          holes=[[(500020, 7500020), (500080, 7500020), (500080, 7500080), (500020, 7500080)]])
        polygons = gpd.GeoSeries([polygon], crs=32750).to_crs(4326)
        points = gpd.GeoSeries(gpd.points_from_xy([500125, 500149, 500151, 500050], [7500050] * 4), crs=32750).to_crs(4326)
        # The last point starts in a hole, which disappears when the polygon expands 50 m.
        np.testing.assert_array_equal(exclusion_mask(points, polygons, 0), [False, False, False, False])
        np.testing.assert_array_equal(exclusion_mask(points, polygons, 50), [True, True, False, True])

    def test_harmonisation_and_conflict(self):
        values = pd.Series([11, 14, 15, 16, 17, 18, 19])
        self.assertEqual(harmonise(values, "benthic").tolist(), [11, 14, 15, 15, 15, 18, 14])
        self.assertEqual(harmonise(values, "geomorphic").tolist(), values.tolist())
        frame = pd.DataFrame(dict(region=["West"] * 4, objective=["benthic"] * 4, uq_row=[1, 1, 2, 2], uq_col=[1] * 4,
                                  reference=[14, 14, 11, 15], uq_inside_extent=[True] * 4))
        selected = select_pixels(frame)
        # Agreeing duplicates keep one row; conflicting labels discard the entire pixel.
        self.assertEqual(selected.unique_pixel.tolist(), [True, False, False, False])

    def test_raster_edges_and_nodata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.tif"
            dataset = gdal.GetDriverByName("GTiff").Create(str(path), 2, 2, 1, gdal.GDT_Byte)
            dataset.SetSpatialRef(osr.SpatialReference("EPSG:4326"))
            dataset.SetGeoTransform((110, 1, 0, -10, 0, -1))
            dataset.GetRasterBand(1).WriteArray(np.array([[11, 12], [0, 15]], dtype=np.uint8))
            dataset.GetRasterBand(1).SetNoDataValue(0)
            dataset = None
            # Exercise a pixel centre, an internal boundary, NoData and the outer right edge.
            frame = pd.DataFrame(dict(longitude=[110.5, 111, 110.5, 112], latitude=[-10.5, -10.5, -11.5, -10.5]))
            values, _, _, inside = raster_sample(path, frame)
            np.testing.assert_array_equal(values, [11, 12, 0, 0])
            np.testing.assert_array_equal(inside, [True, True, True, False])

    def test_polygon_ambiguity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.gpkg"
            # Differently labelled overlapping polygons must produce ambiguity, not first-match wins.
            gpd.GeoDataFrame({"class": ["Sand", "Rock"]}, geometry=[box(110, -11, 111, -10), box(110.5, -11, 111.5, -10)], crs=4326).to_file(path, driver="GPKG")
            frame = pd.DataFrame(dict(longitude=[110.25, 110.75, 111.25, 112], latitude=[-10.5] * 4))
            np.testing.assert_array_equal(polygon_sample([path], frame, "benthic"), [11, -2, 13, 0])

    def test_unexpected_prediction_and_empty(self):
        matrix, rows = class_metrics(np.array([11, 11, 12]), np.array([11, 27, 12]))
        self.assertEqual(matrix.to_numpy().sum(), 3)
        self.assertEqual(next(row for row in rows if row["class_num"] == 11)["producer_agreement_pct"], 50)
        self.assertEqual(class_metrics(np.array([], dtype=int), np.array([], dtype=int))[1], [])

    def test_publication_output_separation(self):
        frame = pd.DataFrame(dict(region=["West", "North West", "Gulf", "Offshore"] * 2,
                                  objective=["geomorphic"] * 8, unique_pixel=[True] * 8,
                                  conflicting_pixel=[False] * 8, reference=[11] * 8,
                                  uq=[11] * 8, aca=[12] * 8,
                                  longitude=[114, 115, 136, 123, 114.2, 115.2, 136.2, 123.2],
                                  latitude=[-22] * 8, excluded_0m=[False] * 8,
                                  excluded_50m=[False] * 8, excluded_100m=[False] * 8))
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            working = base / "working" / "HA04-aca-compare"
            working.mkdir(parents=True)
            summarise(frame, working, 99)
            with patch.object(make_tables, "BASE", base), patch.object(make_tables, "verify_results") as verify:
                make_tables.main()
                verify.assert_called_once_with()
            output = base / "data" / "out" / "stats" / "HA04-aca-compare"
            self.assertEqual({path.name for path in output.iterdir()},
                             {"report_table.csv", "report-table.md", "class-alignment-table.md"})
            for name, number in [("report-table.md", 2), ("class-alignment-table.md", 3)]:
                text = (output / name).read_text(encoding="utf-8")
                self.assertTrue(text.startswith(f"**Table {number}."))
                self.assertIn("Script: HA04-aca-compare/make_tables.py", text)
            self.assertEqual(pd.read_csv(output / "report_table.csv").columns.tolist(),
                             ["objective", "region", "paired_n", "uq_agreement_pct", "aca_agreement_pct",
                              "difference_pp", "low_pp", "high_pp", "blocks"])
            for name in ["points.csv", "manifest.json", "coverage-table.md", "sensitivity-table.md"]:
                self.assertFalse((output / name).exists())
            self.assertTrue((working / "points.csv").is_file())
            self.assertTrue((working / "sensitivity-table.md").is_file())

    def test_paired_denominators(self):
        # Only the first two points have both products; each product gets one of those right.
        # The remaining points test coverage counts without entering agreement denominators.
        frame = pd.DataFrame(dict(region=["West"] * 4, objective=["benthic"] * 4, unique_pixel=[True] * 4, conflicting_pixel=[False] * 4,
                                  reference=[11, 11, 11, 11], uq=[11, 12, 0, 11], aca=[12, 11, 11, 0],
                                  longitude=[114, 115, 116, 117], latitude=[-22] * 4,
                                  excluded_0m=[False] * 4, excluded_50m=[False] * 4, excluded_100m=[False] * 4))
        with tempfile.TemporaryDirectory() as directory:
            result = summarise(frame, Path(directory), 99)
            self.assertTrue((result.paired_n == 2).all())
            self.assertTrue((result.difference_pp == 0).all())
            self.assertTrue((result.uq_only_n == 1).all())
            self.assertTrue((result.aca_only_n == 1).all())
        empty = bootstrap(frame.iloc[:0], 5000, 99)
        self.assertEqual(empty["blocks"], 0)


if __name__ == "__main__":
    gdal.UseExceptions()
    ogr.UseExceptions()
    unittest.main()