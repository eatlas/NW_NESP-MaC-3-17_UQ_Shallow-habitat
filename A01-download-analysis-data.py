"""Download the third party regionalisations used by the habitat area statistics (A02).

Each dataset is saved to its own folder in data/in-3p/. A dataset whose folder
already exists is skipped. data/in-3p/ can be a symbolic link to a folder outside
the repository.
"""
from data_downloader import DataDownloader

downloader = DataDownloader(download_path='data/in-3p')

print("Downloading the regionalisations for the habitat area statistics ...")


# --------------------------------------------------------
# Lawrey, E. (2025). Supporting datasets for estimating reef counts in the Coral Sea and northern Australia
# (NESP MaC 3.17, AIMS) (Version 1) [Data set]. eAtlas. https://doi.org/10.26274/xr0r-tb19
# The NESP 3.17 Analysis-regions. Used to report habitat area by region and subregion, matching the
# reef count and area statistics of the NW Australian reef boundary mapping.
downloader.download_and_unzip(
    'https://nextcloud.eatlas.org.au/s/HmSS5bxxgKdDxEP/download?path=%2Fv1%2Fin%2Fanalysis-regions',
    'nesp-3-17-analysis-regions',
    flatten_directory=True
)


# --------------------------------------------------------
# Department of Climate Change, Energy, the Environment and Water. (2023).
# Integrated Marine and Coastal Regionalisation of Australia (IMCRA) v4.0 - Meso-scale Bioregions [Data set].
# https://fed.dcceew.gov.au/datasets/erin::integrated-marine-and-coastal-regionalisation-of-australia-imcra-v4-0-meso-scale-bioregions/about
# CC BY 3.0.
# Used to report habitat area by meso-scale bioregion. The long file names are shortened,
# which requires data-downloader v1.2.0.
downloader.download_and_unzip(
    'https://hub.arcgis.com/api/v3/datasets/7f83e6e00406487d88d52ac4c2d8c8d4_0/downloads/data?format=shp&spatialRefId=4283&where=1%3D1',
    'IMCRA-v4-0-Meso-Bioregions',
    flatten_directory=True,
    file_find=["Integrated_Marine_and_Coastal_Regionalisation_of_Australia_(IMCRA)_v4.0_-_Meso-scale_Bioregions"],
    file_replace=["IMCRA-v4-Mesoscale-Bioregions"]
)


# --------------------------------------------------------
# Department of Climate Change, Energy, the Environment and Water. (2025).
# Collaborative Australian Protected Areas Database (CAPAD) 2024 - Marine [Data set].
# https://fed.dcceew.gov.au/datasets/erin::collaborative-australian-protected-areas-database-capad-2024-marine/about
# CC BY. Attribution: 'Collaborative Australian Protected Areas Database (CAPAD) 2024, Commonwealth of Australia 2025'.
# Used to report habitat area within each protected area. The folder name is kept short
# because the file names are long and Windows limits path length.
downloader.download_and_unzip(
    'https://hub.arcgis.com/api/v3/datasets/0b6e7b6c48a64a3a82c225fa48aee13d_1/downloads/data?format=shp&spatialRefId=4283&where=1%3D1',
    'CAPAD-2024',
    flatten_directory=True
)
