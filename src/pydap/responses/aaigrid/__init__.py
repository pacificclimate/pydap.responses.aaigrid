import os
import logging
from tempfile import NamedTemporaryFile, SpooledTemporaryFile
from itertools import imap, izip, chain, izip_longest
from zipfile import ZipFile, ZIP_DEFLATED

import gdal
import osr
import numpy
import pytest
from webob.exc import HTTPBadRequest

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

        if type(dataset) != GridType:
            raise HTTPBadRequest("The ArcASCII Grid (aaigrid) response only supports GridTypes, not the requested {}".format(type(dataset)))

        if len(dataset.maps) not in (2, 3):
            raise HTTPBadRequest("The ArcASCII Grid (aaigrid) response only supports Grids with 2 or 3 dimensions, not the requested {}".format(len(dataset.maps)))

        try:
            self._geo_transform = detect_dataset_transform(dataset)
        except Exception, e:
            raise HTTPBadRequest("The ArcASCII Grid (aaigrid) response could not detect the grid transform: {}".format(e.message))

        # FIXME: Verify this
        self.srs = osr.SpatialReference()
        self.srs.SetWellKnownGeogCS('WGS84')

        BaseResponse.__init__(self, dataset)

        self.headers.extend([
            ('Content-type','application/zip'),
            ('Content-Disposition', 'filename="arc_ascii_grid.zip"')
        ])
        # Optionally set the filesize header if possible
        #self.headers.extend([('Content-length', self.nc.filesize)])

    @property
    def geo_transform(self):
        if not hasattr(self, '_geo_transform'):
            self._geo_transform = detect_dataset_transform(self.dataset)
        return self._geo_transform
        
    def __iter__(self):

        if len(self.dataset.maps) > 2:
            time_var = 'T' # FIXME: Is this true?
            dsts = [ self.dataset[:,:,i] for i in range(get_map(self.dataset, time_var).shape[0]) ]
        else:
            dsts = [ self.dataset ]

        file_generator = _bands_to_gdal_files(dsts, self.geo_transform, self.srs)

        def named_file_iterator(filename):
            def content():
                with open(filename, 'r') as my_file:
                    for chunk in my_file:
                        yield chunk
                os.unlink(filename)
            return filename, content()

        all_responders = imap(named_file_iterator, file_generator)
        return ziperator(all_responders)


# FIXME: This is essentially side-effect based
# It writes a file to disk and then returns the filenames
# Should we just bake the file generator into this method?
def _band_to_gdal_files(dap_grid, geo_transform, srs, filename=None):

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
        dst_ds.SetGeoTransform( geo_transform )
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

    for filename in file_list:
        yield filename

def _bands_to_gdal_files(dap_grid_iterable, geo_transform, srs, filename_iterable=[]):
    for dap_grid, filename in izip_longest(dap_grid_iterable, filename_iterable, fillvalue=None):
        for filename_to_yield in _band_to_gdal_files(dap_grid, geo_transform, srs, filename):
            yield filename_to_yield

def get_map(dst, axis):
    for map_name, map_ in dst.maps.iteritems():
        if map_.attributes.has_key('axis'):
            if map_.attributes['axis'] == axis:
                return map_
    return None

def detect_dataset_transform(dst):
    # Iterate through maps, searching for axis attributes
    xmap, ymap = get_map(dst, 'X'), get_map(dst, 'Y')

    if not (xmap and ymap):
        raise Exception("Dataset does not have a map for both the X and Y axes")

    xd = numpy.diff(xmap.data)
    pix_width = xd[0]
    assert (pix_width == xd).all() # No support for irregular grids

    yd = numpy.diff(ymap.data)
    pix_height = yd[0]
    assert (pix_height == yd).all() # No support for irregular grids

    ulx = xmap.data.min() - pix_width
    uly = ymap.data.max() + pix_height # north up
    return [ ulx, pix_width, 0, uly, 0, pix_height ]
