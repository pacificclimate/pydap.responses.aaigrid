#!/bin/bash
set -e
GDALVERSION=$(gdal-config --version) || exit 1
sed "s/gdal$/gdal ==$GDALVERSION/" -i requirements.txt
