import os
from os.path import basename, sep
import logging
from tempfile import gettempdir, SpooledTemporaryFile
from itertools import imap, izip, chain, izip_longest, repeat
from zipfile import ZipFile, ZIP_DEFLATED
import re

import gdal
import osr
import numpy
from numpy import ma
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

numpy_to_gdal = {'float32': gdal.GDT_Float32,
                 'float64': gdal.GDT_Float64,
                 'int64': gdal.GDT_Int32,
                 'int16': gdal.GDT_Int16,
                 'int8': gdal.GDT_Byte}

        
class AAIGridResponse(BaseResponse):
    '''A Pydap responder which uses GDAL to convert grids into Arc/Info ASCII Grid files
    '''
    def __init__(self, dataset):

        if not dataset:
            raise HTTPBadRequest("The ArcASCII Grid (aaigrid) response did not receive required dataset parameter")

        # We will (should?) always get a _DatasetType_ and should use pydap.lib.walk to walk through all of the Grids
        self.grids = walk(dataset, GridType)
        if not self.grids:
            raise HTTPBadRequest("The ArcASCII Grid (aaigrid) response only supports GridTypes, yet none are included in the requested dataset: {}".format(dataset))

        for grid in self.grids:
            l = len(grid.maps)
            if l not in (2, 3):
                raise HTTPBadRequest("The ArcASCII Grid (aaigrid) response only supports Grids with 2 or 3 dimensions, but one of the requested grids contains {} dimension{}".format(l, 's' if l > 1 else ''))
            try:
                detect_dataset_transform(grid)
            except Exception, e:
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

        grids = walk(self.dataset, GridType)

        def generate_aaigrid_files(grid):
            '''Generator that yields multiple file names for each layer of the grid parameter
               This function delegates the actual creation of the '.asc' files to _grid_array_to_gdal_files()
               Files get writted to temp space on disk (by the delegatee)
               and then filenames are yielded from this generator
            '''
            logger.debug("In generate_aaigrid_files for grid {}".format(grid))
            missval = find_missval(grid)
            srs = self.srs
            geo_transform = detect_dataset_transform(grid)

            output_fmt = grid.name + '_{i}.asc'
            for file_ in _grid_array_to_gdal_files(grid.array, srs, geo_transform, filename_fmt=output_fmt, missval=missval):
                yield file_

        # Send each of the grids through _grid_array_to_gdal_files
        # which will generate multiple files per grid
        logger.debug("__iter__: creating the file generator for grids {}".format(grids))
        file_generator = chain.from_iterable(imap(generate_aaigrid_files, grids))

        return ziperator(file_generator)


def named_file_generator(filename):
    '''Generator that yields pairs of (filename, file_content_generator)
       to be consumed by the ziperator
    '''
    def content():
        with open(filename, 'r') as my_file:
            for chunk in my_file:
                yield chunk
        logger.debug("deleting {}".format(filename))
        os.unlink(filename)
    return basename(filename), content()

def _grid_array_to_gdal_files(dap_grid_array, srs, geo_transform, filename_fmt='{i}.asc', missval=None):
    '''Generator which creates an Arc/Info ASCII Grid file for each "layer" (i.e. one step of X by Y) in a given grid

       :param dap_grid_array: Multidimensional arrary of rank 2 or 3
       :type dap_grid_array: numpy.ndarray
       :param srs: Spatial reference system
       :type srs: osr.SpatialReference
       :param geo_transform: GDAL affine transform which applies to this grid
       :type geo_transform: list
       :param filename_fmt: Proposed filename template for output files. "{i}" can be included and will be filled in with the layer number.
       :type filename_fmt: str
       :param missval: Value for which data should be identified as missing
       :type missval: numpy.array
       :returns: A generator which yields pairs of (filename, file_content_generator) of the created files. Note that there will likely be more than one file for layer (e.g. an .asc file and a .prj file).
    '''

    logger.debug("_grid_array_to_gdal_files: translating this grid {} of this srs {} transform {} to this file {}".format(dap_grid_array, srs, geo_transform, filename_fmt))

    logger.debug("Investigating the shape of this grid: {}".format(dap_grid_array))
    shp = dap_grid_array.shape
    if len(shp) == 2:
        ylen, xlen =  shp
        data = [ dap_grid_array ]
    elif len(shp) == 3:
        _, ylen, xlen = shp
        data = iter(dap_grid_array.data)
    else:
        raise ValueError("_grid_array_to_gdal_files received a grid of rank {} rather than the required 2 or 3".format(len(shp)))

    target_type = numpy_to_gdal[dap_grid_array.dtype.name]

    meta_ds = create_gdal_mem_dataset(xlen, ylen, geo_transform, srs, target_type, missval)

    for i, layer in enumerate(data):

        if missval:
            layer = ma.masked_equal(layer, missval)

        logger.debug("Data: {}".format(layer))
        meta_ds.GetRasterBand(1).WriteArray( numpy.flipud(layer) )
        
        driver = gdal.GetDriverByName('AAIGrid')

        outfile = gettempdir() + sep + filename_fmt.format(i=i)
        dst_ds = driver.CreateCopy(outfile, meta_ds, 0)
        
        file_list = dst_ds.GetFileList()

        # Once we're done, close properly the dataset
        dst_ds = None

        for filename in file_list:
            yield named_file_generator(filename)

    meta_ds = None

def create_gdal_mem_dataset(xlen, ylen, geo_transform, srs, target_type, missval=None):
    '''Create and return a single layer GDAL dataset in RAM.
       This dataset can have values repeatedly set to it with dst.GetRasterBand(1).WriteArray()
       and then can be written out to any GDAL format by creating a driver and then using
       `driver.CreateCopy([filename], dst)`

       :param xlen: Number of grid cells in the X (longitude) dimension
       :type xlen: int
       :param ylen: Number of grid cells in the Y (latitude) dimension
       :type ylen: int
       :param srs: Spatial reference system
       :type srs: osr.SpatialReference
       :param geo_transform: GDAL affine transform which applies to this grid
       :type geo_transform: list
       :param target_type: A known `gdal data type <http://gdal.org/gdal_8h.html#a22e22ce0a55036a96f652765793fb7a4>`_
       :type target_type: gdal.GDALDataType
       :param missval: Value for which data should be identified as missing
       :type missval: numpy.array
       :returns: A single layer gdal.Dataset driven by the MEM driver
    '''
    logger.debug("Creating a GDAL driver ({}, {}) of type {}".format(xlen, ylen, target_type))
    # Because we're using the MEM driver, we can use an empty filename and it will never go to disk

    # GDAL's AAIGrid driver only works in CreateCopy mode,
    # so we have to create the dataset with something else first
    driver = gdal.GetDriverByName('MEM')
    metadata = driver.GetMetadata()
    assert metadata.has_key(gdal.DCAP_CREATE)
    assert metadata[gdal.DCAP_CREATE] == 'YES'

    dst = driver.Create('', xlen, ylen, 1, target_type)

    dst.SetGeoTransform( geo_transform )
    dst.SetProjection( srs.ExportToWkt() )

    if missval:
        dst.GetRasterBand(1).SetNoDataValue(missval.astype('float'))
    else:
        # To clear the nodata value, set with an "out of range" value per GDAL docs
        dst.GetRasterBand(1).SetNoDataValue(-9999)

    return dst

def find_missval(grid):
    '''Search grid attributes for indications of a missing value

       :param grid: An instance of the Pydap GridType
       :type grid: GridType
       :returns: the missing value if available (None, otherwise)
    '''
    missval = None
    for key in ('missing_value', '_FillValue'):
        if key in grid.attributes:
            missval = grid.attributes[key][0]
    return missval

def get_map(dst, axis):
    '''Search grid attributes for the 'axis' attribute for a particular axis and return a mapping

       :param dst: An instance of a Pydap Dataset (typically a GridType)
       :type dst: GridType
       :param axis: The character abbreviation for the axis for which to search. E.g. 'X', 'Y', 'Z' or 'T'.
       :type axis: str
       :returns: The Pydap BaseType which corresponds to the mapping for the given axis
       :rtype: BaseType
    '''
    for map_name, map_ in dst.maps.iteritems():
        if map_.attributes.has_key('axis'):
            if map_.attributes['axis'] == axis:
                return map_
    return None

def get_time_map(dst):
    '''Search a grid for the time axis using a variety of hueristics.

       According to http://cf-pcmdi.llnl.gov/documents/cf-conventions/1.6/cf-conventions.html#time-coordinate
       the time coordinate is identifiable by its units alone,
       though optionally it can be indicated by using the standard_name and/or axis='T'

       This function searches for those in reverse order and returns the first match.

       :param dst: An instance of the Pydap Dataset (typically a GridType)
       :type dst: GridType
       :returns: The Pydap Basetype which corresponds to the time axis
       :rtype: BaseType
    '''
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
    '''Detects and calculates the affine transform for a given GridType dataset. See http://www.gdal.org/gdal_datamodel.html for more on the transform parameters.

       :param dst: An instance of a Pydap GridType for which to caculate an affine transform
       :type dst: GridType
       :returns: The GDAL affine transform in the form of [ upper_left_x, pixel_width, 0, upper_left_y, 0, pixel_height ]
       :rtype: list
    '''
    # dst must be a Grid
    if type(dst) != GridType:
        raise Exception("Dataset must be of type Grid, not {}".format(type(dst)))

    # Iterate through maps, searching for axis attributes
    xmap, ymap = get_map(dst, 'X'), get_map(dst, 'Y')

    if xmap is None or ymap is None:
        raise Exception("Dataset does not have a map for both the X and Y axes")

    if type(xmap.data) == numpy.ndarray:
        xarray = xmap.data
    else:
        xarray = iter(xmap.data).next() # Might to iterate over proxy objects to actually get the data

    xd = numpy.diff(xarray)
    pix_width = xd[0]
    assert numpy.isclose(pix_width, xd).all(), "No support for irregular grids"

    if type(ymap.data) == numpy.ndarray:
        yarray = ymap.data
    else:
        yarray = iter(ymap.data).next()

    yd = numpy.diff(yarray)
    pix_height = yd[0]
    assert numpy.isclose(pix_height, yd).all(), "No support for irregular grids"

    ulx = numpy.min(xarray) - pix_width
    uly = numpy.max(yarray) + pix_height # north up
    return [ ulx, pix_width, 0, uly, 0, pix_height ]
