from data_downloader import DataDownloader

# Create an instance of the DataDownloader class
downloader = DataDownloader(download_path='data/in-3p')

# ACA reference polygons are supplied in data/in-3p-mirror/ACA-ref with source
# metadata. HA04-aca-compare/compare.py uses them for the 50 m reference exclusion.
# Automated source links are unreliable. For original sources, citations and manual
# download instructions, see README.md, "Mirrored third-party data and manual downloads".
print('ACA references: use the supplied data/in-3p-mirror/ACA-ref files. '
      'For a code-only rebuild, see README.md: Mirrored third-party data and manual downloads.')

print("Downloading source data files. This will take a while ...")


# --------------------------------------------------------
# Natural Earth. (2025). Natural Earth 1:10m Physical Vectors - Land [Shapefile]. https://www.naturalearthdata.com/downloads/10m-physical-vectors/
direct_download_url = 'https://naciscdn.org/naturalearth/10m/physical/ne_10m_land.zip'
downloader.download_and_unzip(direct_download_url, 'ne_10m_land')


# --------------------------------------------------------
# Australian Coastline 50K 2024 (NESP MaC 3.17, AIMS)
# https://eatlas.org.au/geonetwork/srv/eng/catalog.search#/metadata/c5438e91-20bf-4253-a006-9e9600981c5f
# Hammerton, M., & Lawrey, E. (2024). Australian Coastline 50K 2024 (NESP MaC 3.17, AIMS) (2nd Ed.) [Data set]. eAtlas. https://doi.org/10.26274/qfy8-hj59
# This is used for clipping out land areas from the manually edited reef boundaries
direct_download_url = 'https://nextcloud.eatlas.org.au/s/DcGmpS3F5KZjgAG/download?path=%2FV1-1%2F&files=Split'

downloader.download_and_unzip(direct_download_url, 'AU_AIMS_Coastline_50k_2024', subfolder_name='Split', flatten_directory=True)

# Use this version for overview maps and faster intermediate processing steps where the finest
# precision is not needed.
direct_download_url = 'https://nextcloud.eatlas.org.au/s/DcGmpS3F5KZjgAG/download?path=%2FV1-1%2F&files=Simp'
downloader.download_and_unzip(direct_download_url, 'AU_AIMS_Coastline_50k_2024', subfolder_name='Simp', flatten_directory=True)






