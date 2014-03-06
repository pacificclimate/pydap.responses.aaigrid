import os
import logging
from tempfile import NamedTemporaryFile, SpooledTemporaryFile
from itertools import imap, izip, chain, izip_longest
from zipfile import ZipFile, ZIP_DEFLATED
import re

import gdal
import osr
import numpy
import pytest
from webob.exc import HTTPBadRequest

from pydap.responses.lib import BaseResponse
from pydap.model import *
from pydap.lib import walk, get_var

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

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

        if not dataset:
            raise HTTPBadRequest("The ArcASCII Grid (aaigrid) response did not receive required dataset parameter")

        # We will (should?) always get a _DatasetType_ and should use pydap.lib.walk to walk through all of the Grids
        self.grids = [x for x in walk(dataset, GridType)]
        if not self.grids:
            raise HTTPBadRequest("The ArcASCII Grid (aaigrid) response only supports GridTypes, yet none are included in the requested dataset: {}".format(dataset))

        for grid in self.grids:
            l = len(grid.maps)
            if l not in (2, 3):
                raise HTTPBadRequest("The ArcASCII Grid (aaigrid) response only supports Grids with 2 or 3 dimensions, but one of the requested grids contains {} dimension{}".format(l, 's' if l > 1 else ''))
            try:
                import pytest
                detect_dataset_transform(grid)
            except Exception, e:
                pytest.set_trace()
                raise HTTPBadRequest("The ArcASCII Grid (aaigrid) response could not detect the grid transform for grid {}: {}".format(grid.name, e.message))

        # FIXME: Verify this
        self.srs = osr.SpatialReference()
        self.srs.SetWellKnownGeogCS('WGS84')

        BaseResponse.__init__(self, dataset)

        self.headers.extend([
            ('Content-type','application/zip'),
            ('Content-Disposition', 'filename="arc_ascii_grid.zip"')
        ])
        
    def __iter__(self):

        grids = [ grid for grid in walk(self.dataset, GridType) ]

        # FIXME: There's may still be some problems with implicit dimension ordering
        def generate_grid_layers(grid):
            if len(grid.maps) > 2:
                for i in range(get_time_map(grid).shape[0]):
                    logger.debug("generate_grid_layers: yielding grid[{i}:{i}+1,:,:]".format(i=i))
                    subgrid = grid[i,:,:]
                    logger.debug(subgrid)
                    yield subgrid
            else:
                logger.debug("generate_grid_layers: grid '{}' has 2 or less maps, so I'm just yielding the whole thing")
                yield grid

        logger.debug("__iter__: creating the grid layers iterable")
        grid_layers = chain.from_iterable( [ generate_grid_layers(grid) for grid in grids ] )

        logger.debug("__iter__: creating the file generator")
        file_generator = _bands_to_gdal_files(grid_layers, self.srs)

        def named_file_iterator(filename):
            def content():
                with open(filename, 'r') as my_file:
                    for chunk in my_file:
                        yield chunk
                os.unlink(filename)
            return filename, content()

        logger.debug("__iter__: creating the all_responders iterator")
        all_responders = imap(named_file_iterator, file_generator)
        return ziperator(all_responders)


# FIXME: This is essentially side-effect based
# It writes a file to disk and then returns the filenames
# Should we just bake the file generator into this method?
def _band_to_gdal_files(dap_grid, srs, filename=None):

    logger.debug("_band_to_gdal_files: translating this grid {} of this srs {} to this file {}".format(dap_grid, srs, filename))

    geo_transform = detect_dataset_transform(dap_grid)
    # FIXME: Arc Grid only supports 2 dimensions and a single band
    # ensure that this is only two dimensions

    # GDAL's AAIGrid driver only works in CreateCopy mode,
    # so we have to create the dataset with something else first
    driver = gdal.GetDriverByName('NetCDF')
    metadata = driver.GetMetadata()
    assert metadata.has_key(gdal.DCAP_CREATE)
    assert metadata[gdal.DCAP_CREATE] == 'YES'

    logger.debug("Investigating the shape of this grid: {}".format(dap_grid.array))

    shp = dap_grid.array.shape
    if len(shp) == 2:
        ylen, xlen =  shp
        data = dap_grid.array.data
    elif len(shp) == 3:
        ylen, xlen, _ = shp
        data = iter(dap_grid.array.data).next()
    else:
        raise ValueError("_band_to_gdal_files received a grid of rank {} rather than the required 2 (or 3?)".format(len(shp)))

    logger.debug("_band_to_gdal_files: shape checking complete... proceeding with this grid: {}".format(data))
    
    with NamedTemporaryFile() as f:
        dst_ds = driver.Create(f.name, xlen, ylen, 1, gdal.GDT_Byte)
        dst_ds.SetGeoTransform( geo_transform )
        dst_ds.SetProjection( srs.ExportToWkt() )

        data = dap_grid.array.data
        dst_ds.GetRasterBand(1).WriteArray( data )
        
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

def _bands_to_gdal_files(dap_grid_iterable, srs, filename_iterable=[]):
    for dap_grid, filename in izip_longest(dap_grid_iterable, filename_iterable):
        for filename_to_yield in _band_to_gdal_files(dap_grid, srs, filename):
            yield filename_to_yield

def get_map(dst, axis):
    for map_name, map_ in dst.maps.iteritems():
        if map_.attributes.has_key('axis'):
            if map_.attributes['axis'] == axis:
                return map_
    return None

def get_time_map(dst):
    # according to http://cf-pcmdi.llnl.gov/documents/cf-conventions/1.6/cf-conventions.html#time-coordinate
    # the time coordinate is identifiable by its units alone
    # though optionally it can be indicated by using the standard_name and/or axis='T'
    # We'll search for those in reverse order
    for map_name, map_ in dst.maps.iteritems():
        attrs = map_.attributes
        if attrs.has_key('axis') and attrs['axis'] == 'T':
            return map_
        if attrs.has_key('standard_name') and attrs['standard_name'] == 'time':
            return map_
        if attrs.has_key('units') and re.match('(day|d|hour|h|hr|minute|min|second|sec|s)s? since .+', attrs['units']):
            return map_
    return None

def detect_dataset_transform(dst):
    # dst must be a Grid
    if type(dst) != GridType:
        raise Exception("Dataset must be of type Grid, not {}".format(type(dst)))

    # Iterate through maps, searching for axis attributes
    xmap, ymap = get_map(dst, 'X'), get_map(dst, 'Y')

    if xmap is None or ymap is None:
        raise Exception("Dataset does not have a map for both the X and Y axes")

    xarray = numpy.array([x for x in xmap.data]) # Have to iterate over HDF5Data objects to actually get the data
    xd = numpy.diff(xarray)
    pix_width = xd[0]
    assert numpy.isclose(pix_width, xd).all(), "No support for irregular grids"

    yarray = numpy.array([y for y in ymap.data])
    yd = numpy.diff(yarray)
    pix_height = yd[0]
    assert numpy.isclose(pix_height, yd).all(), "No support for irregular grids"

    ulx = numpy.min(xarray) - pix_width
    uly = numpy.max(yarray) + pix_height # north up
    return [ ulx, pix_width, 0, uly, 0, pix_height ]
