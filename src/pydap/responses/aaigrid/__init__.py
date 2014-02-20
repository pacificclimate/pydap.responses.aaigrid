import os
import logging
from tempfile import NamedTemporaryFile, SpooledTemporaryFile
from itertools import imap, izip, chain
from zipfile import ZipFile, ZIP_DEFLATED

import gdal
import osr
import numpy
import pytest

from pydap.responses.lib import BaseResponse
from pydap.model import *
from pydap.lib import walk, get_var

# FIXME: this code should be factored out... it's used in two places!
def ziperator(responders):
    '''This method creates and returns an iterator which yields bytes for a :py:class:`ZipFile` that contains a set of files from OPeNDAP requests. The method will spool the first one gigabyte in memory using a :py:class:`SpooledTemporaryFile`, after which it will use disk.

       :param responders: A list of (``name``, ``generator``) pairs where ``name`` is the filename to use in the zip archive and ``generator`` should yield all bytes for a single file.
       :rtype: iterator
    '''
    with SpooledTemporaryFile(1024*1024*1024) as f:
        yield 'PK' # Response headers aren't sent until the first chunk of data is sent.  Let's get this repsonse moving!
        z = ZipFile(f, 'w', ZIP_DEFLATED)

        for name, responder in responders:
            pos = 2 if f.tell() == 0 else f.tell()
            z.writestr(name, ''.join([x for x in responder]))
            f.seek(pos)
            yield f.read()
        pos = f.tell()
        z.close()
        f.seek(pos)
        yield f.read()

        
class AAIGridResponse(BaseResponse):
    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)

        self.headers.extend([
            ('Content-type','application/zip'),
            ('Content-Disposition', 'filename="arc_ascii_grid.zip"')
        ])
        # Optionally set the filesize header if possible
        #self.headers.extend([('Content-length', self.nc.filesize)])
        
    def __iter__(self):

        # Check that we have x and y maps

        # time_var = 't'
        # for i in range(self.dataset.maps['t'].shape):
        #     layer = self.dataset[:,:,i]

        dsts = [ self.dataset[:,:,i] for i in range(self.dataset.maps['t'].shape[0]) ]

        file_lists = imap(_band_to_gdal_files, dsts)
        file_list = chain(*file_lists)
        file_list = [x for x in file_list]

        def responder(filename):
            with open(filename, 'r') as my_file:
                for chunk in my_file:
                    yield chunk
            os.unlink(filename)

        all_responders = izip(file_list, imap(responder, file_list))
        return ziperator(all_responders)


def _band_to_gdal_files(dap_grid, filename=None):

    # FIXME: Arc Grid only supports 2 dimensions and a single band
    # ensure that this is only two dimensions

    # GDAL's AAIGrid driver only works in CreateCopy mode,
    # so we have to create the dataset with something else first
    driver = gdal.GetDriverByName('NetCDF')
    metadata = driver.GetMetadata()
    assert metadata.has_key(gdal.DCAP_CREATE)
    assert metadata[gdal.DCAP_CREATE] == 'YES'

    ylen, xlen = dap_grid.array.shape # FIXME: why are these backwards?
    
    with NamedTemporaryFile() as f:
        dst_ds = driver.Create(f.name, xlen, ylen, 1, gdal.GDT_Byte)
        dst_ds.SetGeoTransform( [ 444720, 30, 0, 3751320, 0, -30 ] ) # FIXME: get from geographic coordinates
        srs = osr.SpatialReference()
        srs.SetWellKnownGeogCS('WGS84')
        dst_ds.SetProjection( srs.ExportToWkt() )

        data = dap_grid.array.data
        dst_ds.GetRasterBand(1).WriteArray( dap_grid.array.data )
        
        src_ds = dst_ds
       
        driver = gdal.GetDriverByName('AAIGrid')

        if not filename:
            filename = NamedTemporaryFile(suffix='.asc', delete=False).name
        dst_ds = driver.CreateCopy(filename, src_ds, 0)
        
    # Once we're done, close properly the dataset
    file_list = dst_ds.GetFileList()

    dst_ds = None
    src_ds = None
    
    return file_list
