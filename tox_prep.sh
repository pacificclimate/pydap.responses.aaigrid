#!/bin/bash
set -e
GDALVERSION=$(gdal-config --version) || exit 1
GDALVERSION=${GDALVERSION%.*} #trim bugfix version
sed "s/gdal$/gdal ==$GDALVERSION/" -i requirements.txt
