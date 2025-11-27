"""
Convert palette CSV files to QGIS CLR and GeoServer SLD formats.

This script:
1. Reads palette files with class_id, class_name, and hex colors
2. Reads class count files to determine which classes are actually used
3. Filters out class_id 0 (nodata) and Unknown_* classes
4. Converts hex colors to RGB
5. Generates CLR files for QGIS styling
6. Generates SLD files for GeoServer styling with discrete colors
"""

import csv
import os
from pathlib import Path


def hex_to_rgb(hex_color):
    """
    Convert hex color to RGB tuple.
    
    Args:
        hex_color: Hex color string (e.g., '#ffffff' or 'ffffff')
    
    Returns:
        Tuple of (red, green, blue) values (0-255)
    """
    # Remove '#' if present
    hex_color = hex_color.lstrip('#')
    
    # Convert to RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    return (r, g, b)


def read_palette(palette_file):
    """
    Read palette CSV file.
    
    Args:
        palette_file: Path to palette CSV file
    
    Returns:
        Dictionary mapping class_id to (class_name, hex_color)
    """
    palette = {}
    
    with open(palette_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            class_id = int(row['class_id'])
            class_name = row['class_name']
            hex_color = row['hex']
            palette[class_id] = (class_name, hex_color)
    
    return palette


def read_class_counts(counts_file):
    """
    Read class counts CSV file.
    
    Args:
        counts_file: Path to class counts CSV file
    
    Returns:
        Set of class_ids that have pixel counts
    """
    used_classes = set()
    
    with open(counts_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            class_id = int(row['class_id'])
            count = int(row['count'])
            if count > 0:
                used_classes.add(class_id)
    
    return used_classes


def filter_classes(palette, used_classes):
    """
    Filter palette to only include used classes, excluding class_id 0 and Unknown_* classes.
    
    Args:
        palette: Dictionary mapping class_id to (class_name, hex_color)
        used_classes: Set of class_ids that have pixel counts
    
    Returns:
        List of tuples (class_id, class_name, hex_color) for valid classes
    """
    filtered = []
    
    for class_id in sorted(palette.keys()):
        class_name, hex_color = palette[class_id]
        
        # Skip class_id 0 (nodata)
        if class_id == 0:
            continue
        
        # Skip Unknown_* classes
        if class_name.startswith('Unknown_'):
            continue
        
        # Only include classes that are actually used
        if class_id in used_classes:
            filtered.append((class_id, class_name, hex_color))
    
    return filtered


def write_clr_file(classes, output_file):
    """
    Write CLR file for QGIS.
    
    Args:
        classes: List of tuples (class_id, class_name, hex_color)
        output_file: Path to output CLR file
    """
    with open(output_file, 'w') as f:
        for class_id, class_name, hex_color in classes:
            r, g, b = hex_to_rgb(hex_color)
            # Format: class_id red green blue alpha class_name
            f.write(f"{class_id} {r} {g} {b} 255 {class_name}\n")
    
    print(f"Created CLR file: {output_file}")


def write_sld_file(classes, output_file, style_name, layer_name):
    """
    Write SLD file for GeoServer with discrete colors.
    
    Args:
        classes: List of tuples (class_id, class_name, hex_color)
        output_file: Path to output SLD file
        style_name: Name of the SLD style
        layer_name: Name of the associated layer
    """
    with open(output_file, 'w') as f:
        # Write SLD header
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<StyledLayerDescriptor version="1.0.0"\n')
        f.write('  xmlns="http://www.opengis.net/sld"\n')
        f.write('  xmlns:ogc="http://www.opengis.net/ogc"\n')
        f.write('  xmlns:xlink="http://www.w3.org/1999/xlink"\n')
        f.write('  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n')
        f.write('  xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">\n')
        f.write(f'  <NamedLayer>\n')
        f.write(f'    <Name>{layer_name}</Name>\n')
        f.write(f'    <UserStyle>\n')
        f.write(f'      <Name>{style_name}</Name>\n')
        f.write(f'      <Title>{style_name}</Title>\n')
        f.write(f'      <FeatureTypeStyle>\n')
        f.write(f'        <Rule>\n')
        f.write(f'          <RasterSymbolizer>\n')
        f.write(f'            <ColorMap type="values">\n')
        
        # Write color map entries
        for class_id, class_name, hex_color in classes:
            r, g, b = hex_to_rgb(hex_color)
            # Convert RGB to hex for SLD (including alpha)
            color_hex = f"#{hex_color.lstrip('#')}"
            f.write(f'              <ColorMapEntry color="{color_hex}" quantity="{class_id}" label="{class_name}" opacity="1.0"/>\n')
        
        # Write SLD footer
        f.write(f'            </ColorMap>\n')
        f.write(f'          </RasterSymbolizer>\n')
        f.write(f'        </Rule>\n')
        f.write(f'      </FeatureTypeStyle>\n')
        f.write(f'    </UserStyle>\n')
        f.write(f'  </NamedLayer>\n')
        f.write('</StyledLayerDescriptor>\n')
    
    print(f"Created SLD file: {output_file}")


def process_dataset(palette_file, counts_file, output_dir, dataset_name, layer_name):
    """
    Process a single dataset (benthic or geomorphic).
    
    Args:
        palette_file: Path to palette CSV file
        counts_file: Path to class counts CSV file
        output_dir: Directory to save output files
        dataset_name: Name of the dataset (for file naming)
        layer_name: Name of the layer (for SLD)
    """
    print(f"\nProcessing {dataset_name}...")
    
    # Read palette and class counts
    palette = read_palette(palette_file)
    used_classes = read_class_counts(counts_file)
    
    print(f"  Total classes in palette: {len(palette)}")
    print(f"  Classes with pixel counts: {len(used_classes)}")
    
    # Filter classes
    filtered_classes = filter_classes(palette, used_classes)
    
    print(f"  Classes after filtering: {len(filtered_classes)}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output file paths
    clr_file = os.path.join(output_dir, f"{dataset_name}.clr")
    sld_file = os.path.join(output_dir, f"{dataset_name}.sld")
    
    # Write output files
    write_clr_file(filtered_classes, clr_file)
    write_sld_file(filtered_classes, sld_file, dataset_name, layer_name)
    
    # Print summary
    print(f"  Classes included:")
    for class_id, class_name, hex_color in filtered_classes:
        r, g, b = hex_to_rgb(hex_color)
        print(f"    {class_id}: {class_name} (RGB: {r}, {g}, {b})")


def main():
    """Main function to process both benthic and geomorphic datasets."""
    
    # Define base paths
    base_dir = Path(__file__).parent
    
    # Process benthic dataset
    process_dataset(
        palette_file=base_dir / "Raw benthic raster files" / "benthic_palette.csv",
        counts_file=base_dir / "output_claude" / "benthic_class_counts.csv",
        output_dir=base_dir / "output_claude",
        dataset_name="NW_NESP-MaC-3-17_UQ_Shallow-habitat_Benthic_2025",
        layer_name="NW_NESP-MaC-3-17_UQ_Shallow-habitat_Benthic_2025"
    )
    
    # Process geomorphic dataset
    process_dataset(
        palette_file=base_dir / "Raw geomorphic raster tiles" / "geo_palette.csv",
        counts_file=base_dir / "output_claude" / "geomorphic_class_counts.csv",
        output_dir=base_dir / "output_claude",
        dataset_name="NW_NESP-MaC-3-17_UQ_Shallow-habitat_Geomorphic_2025",
        layer_name="NW_NESP-MaC-3-17_UQ_Shallow-habitat_Geomorphic_2025"
    )
    
    print("\n✓ Processing complete!")


if __name__ == "__main__":
    main()
