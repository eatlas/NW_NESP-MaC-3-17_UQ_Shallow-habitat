"""Generate CLR and SLD style files for benthic and geomorphic datasets.

Rules (per user specification):
 - Input palette CSVs (hex colours):
	 ../Raw benthic raster files/benthic_palette.csv
	 ../Raw geomorphic raster tiles/geo_palette.csv
 - Input class usage/count CSVs (already produced by prior script):
	 output_gpt5/benthic_class_counts.csv
	 output_gpt5/geomorphic_class_counts.csv
 - Exclude class_id == 0 (nodata) from outputs.
 - Exclude any class whose class_name starts with "Unknown_".
 - Only include classes with count > 0 (present in dataset).
 - If a palette entry has no count, omit it.
 - Remove trailing asterisk from names like "Temporal*" if present.
 - Order entries by ascending class_id.
 - Alpha channel fixed at 255.
 - Output files written into output_gpt5/:
	 NW_NESP-MaC-3-17_UQ_Shallow-habitat_Benthic.clr
	 NW_NESP-MaC-3-17_UQ_Shallow-habitat_Benthic.sld
	 NW_NESP-MaC-3-17_UQ_Shallow-habitat_Geomorphic.clr
	 NW_NESP-MaC-3-17_UQ_Shallow-habitat_Geomorphic.sld
 - Abort on malformed hex codes or missing required files.
 - No CLI arguments; simple script for clarity.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path


BASE_DIR = Path(__file__).parent  # derived/
REPO_ROOT = BASE_DIR.parent       # project root (sibling of Raw * dirs)


class Config:
	# Palette CSVs reside under the sibling 'original' directory per corrected relative paths.
	benthic_palette = REPO_ROOT / "original" / "Raw benthic raster files" / "benthic_palette.csv"
	geomorphic_palette = REPO_ROOT / "original" / "Raw geomorphic raster tiles" / "geo_palette.csv"
	benthic_counts = BASE_DIR / "output_gpt5" / "benthic_class_counts.csv"
	geomorphic_counts = BASE_DIR / "output_gpt5" / "geomorphic_class_counts.csv"
	out_dir = BASE_DIR / "output_gpt5"
	benthic_style_name = "NW_NESP-MaC-3-17_UQ_Shallow-habitat_Benthic"
	geomorphic_style_name = "NW_NESP-MaC-3-17_UQ_Shallow-habitat_Geomorphic"


def ensure_files_exist(paths: list[Path]):
	missing = [p for p in paths if not p.is_file()]
	if missing:
		for m in missing:
			print(f"ERROR: Required file not found: {m}", file=sys.stderr)
		sys.exit(1)


def read_palette(path: Path) -> dict[int, tuple[str, str]]:
	"""Return mapping class_id -> (clean_name, hex)."""
	mapping: dict[int, tuple[str, str]] = {}
	with path.open("r", newline="", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		for row in reader:
			try:
				cid = int(row["class_id"])
			except (KeyError, ValueError):
				print(f"ERROR: Invalid class_id in palette {path}: {row}", file=sys.stderr)
				sys.exit(1)
			name = row.get("class_name", "").strip()
			# Remove trailing asterisk only (per spec) if present.
			if name.endswith("*"):
				name = name.rstrip("*")
			hex_code = row.get("hex", "").strip()
			if not valid_hex_colour(hex_code):
				print(f"ERROR: Invalid hex colour '{hex_code}' for class_id {cid} in {path}", file=sys.stderr)
				sys.exit(1)
			mapping[cid] = (name, hex_code)
	return mapping


def read_counts(path: Path) -> dict[int, tuple[str, int]]:
	"""Return mapping class_id -> (class_name, count)."""
	result: dict[int, tuple[str, int]] = {}
	with path.open("r", newline="", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		for row in reader:
			try:
				cid = int(row["class_id"])
				cnt = int(row["count"])
			except (KeyError, ValueError):
				print(f"ERROR: Invalid row in counts {path}: {row}", file=sys.stderr)
				sys.exit(1)
			name = row.get("class_name", "").strip()
			result[cid] = (name, cnt)
	return result


def valid_hex_colour(s: str) -> bool:
	if len(s) != 7 or not s.startswith("#"):
		return False
	hex_digits = s[1:]
	return all(c in "0123456789abcdefABCDEF" for c in hex_digits)


def hex_to_rgb(s: str) -> tuple[int, int, int]:
	if not valid_hex_colour(s):  # defensive; should already be validated
		raise ValueError(f"Malformed hex colour: {s}")
	return int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16)


def build_used_classes(palette: dict[int, tuple[str, str]], counts: dict[int, tuple[str, int]]) -> list[tuple[int, str, str]]:
	"""Filter and return list of (class_id, name, hex) to include, ordered ascending class_id."""
	used: list[tuple[int, str, str]] = []
	for cid in sorted(palette.keys()):
		if cid == 0:
			continue  # nodata excluded
		if cid not in counts:
			continue  # palette entry unused in dataset
		name_counts, cnt = counts[cid]
		if cnt <= 0:
			continue
		# Exclude Unknown_* classes based on counts file naming OR palette naming both ways.
		if name_counts.startswith("Unknown_"):
			continue
		name_palette, hex_code = palette[cid]
		if name_palette.startswith("Unknown_"):
			continue
		used.append((cid, name_palette, hex_code))
	return used


def write_clr(path: Path, classes: list[tuple[int, str, str]]):
	lines = []
	for cid, name, hex_code in classes:
		r, g, b = hex_to_rgb(hex_code)
		line = f"{cid} {r} {g} {b} 255 {name}"
		lines.append(line)
	path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_sld(path: Path, style_name: str, classes: list[tuple[int, str, str]]):
	# Construct ColorMapEntry list
	entries = []
	for cid, name, hex_code in classes:
		entries.append(f"        <ColorMapEntry color=\"{hex_code}\" quantity=\"{cid}\" label=\"{escape_xml(name)}\" opacity=\"1.0\"/>")
	cmap = "\n".join(entries)
	xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:gml="http://www.opengis.net/gml">
  <NamedLayer>
	<Name>{style_name}</Name>
	<UserStyle>
	  <Title>{style_name}</Title>
	  <FeatureTypeStyle>
		<Rule>
		  <RasterSymbolizer>
			<ColorMap type="values">
{cmap}
			</ColorMap>
		  </RasterSymbolizer>
		</Rule>
	  </FeatureTypeStyle>
	</UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
"""
	path.write_text(xml, encoding="utf-8")


def escape_xml(s: str) -> str:
	return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;").replace('"', "&quot;")


def process_one(kind: str, palette_path: Path, counts_path: Path, style_name: str):
	print(f"Processing {kind} (palette={palette_path.name}, counts={counts_path.name})")
	palette = read_palette(palette_path)
	counts = read_counts(counts_path)
	classes = build_used_classes(palette, counts)
	if not classes:
		print(f"WARNING: No classes produced for {kind} (after filtering).", file=sys.stderr)
	# Output paths
	clr_path = Config.out_dir / f"{style_name}.clr"
	sld_path = Config.out_dir / f"{style_name}.sld"
	write_clr(clr_path, classes)
	write_sld(sld_path, style_name, classes)
	print(f"Wrote {clr_path.name} ({len(classes)} entries) and {sld_path.name}")


def main():
	ensure_files_exist([
		Config.benthic_palette,
		Config.geomorphic_palette,
		Config.benthic_counts,
		Config.geomorphic_counts,
	])
	Config.out_dir.mkdir(parents=True, exist_ok=True)
	process_one("benthic", Config.benthic_palette, Config.benthic_counts, Config.benthic_style_name)
	process_one("geomorphic", Config.geomorphic_palette, Config.geomorphic_counts, Config.geomorphic_style_name)
	print("Done.")


if __name__ == "__main__":
	main()

