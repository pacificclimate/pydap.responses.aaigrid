import logging

import gdal
import osr
import numpy

from pydap.responses.lib import BaseResponse
from pydap.model import *
from pydap.lib import walk, get_var


class AAIGridResponse(BaseResponse):
    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)

        self.headers.extend([
            ('Content-type', 'application/x-arc-grid')
        ])
        # Optionally set the filesize header if possible
        #self.headers.extend([('Content-length', self.nc.filesize)])
        
    def __iter__(self):
        # The AAIGrid driver only works in CreateCopy mode,
        # so we have to create the dataset with something else first
        driver = gdal.GetDriverByName('NetCDF')
        metadata = driver.GetMetadata()
        assert metadata.has_key(gdal.DCAP_CREATE)
        assert metadata[gdal.DCAP_CREATE] == 'YES'
        dst_ds = driver.Create('my_file.netcdf', 10, 10, 1, gdal.GDT_Byte)
        dst_ds.SetGeoTransform( [ 444720, 30, 0, 3751320, 0, -30 ] )
        srs = osr.SpatialReference()
        srs.SetWellKnownGeogCS('WGS84')
        dst_ds.SetProjection( srs.ExportToWkt() )
        raster = numpy.zeros( (10, 10), dtype=numpy.uint8 )
        dst_ds.GetRasterBand(1).WriteArray( raster )

        src_ds = dst_ds
        
        driver = gdal.GetDriverByName('AAIGrid')
        metadata = driver.GetMetadata()

        dst_ds = driver.CreateCopy('my_file.aaigrid', src_ds, 0)
        
        # Once we're done, close properly the dataset
        dst_ds = None
        src_ds = None
        with open('my_file.aaigrid', 'r') as my_file:
            for chunk in my_file:
                yield chunk
