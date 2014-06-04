from zipfile import ZipFile, ZIP_DEFLATED
from tempfile import NamedTemporaryFile

from webob.request import Request
from webob.exc import HTTPBadRequest
import numpy as np
import numpy.testing
import pytest

from pydap.model import GridType, BaseType, DatasetType
from pydap.responses.aaigrid import AAIGridResponse, find_missval, detect_dataset_transform, get_map

def test_bad_dataset_failure():
    with pytest.raises(HTTPBadRequest) as excinfo:
        app = AAIGridResponse(None)

    assert "did not receive required dataset parameter" in excinfo.value.message

def test_single_dimension_failure(single_dimension_dataset):
    with pytest.raises(HTTPBadRequest) as excinfo:
        app = AAIGridResponse(single_dimension_dataset)

    assert excinfo.value.message.endswith("supports Grids with 2 or 3 dimensions, but one of the requested grids contains 1 dimension")

def test_four_dimension_failure(four_dimension_dataset):
    with pytest.raises(HTTPBadRequest) as excinfo:
        app = AAIGridResponse(four_dimension_dataset)

    assert excinfo.value.message.endswith("supports Grids with 2 or 3 dimensions, but one of the requested grids contains 4 dimensions")


def notest_can_call(app, temp_file):
    req = Request.blank('/')
    resp = req.get_response(app)
    assert resp.status == '200 OK'
    for chunk in resp.app_iter:
        temp_file.write(chunk)

def test_single_layer_dataset(single_layer_app, temp_file):
    req = Request.blank('/')
    resp = req.get_response(single_layer_app)
    assert resp.status == '200 OK'

    for chunk in resp.app_iter:
        temp_file.write(chunk)
    temp_file.flush()
    
    z = ZipFile(temp_file.name, 'r', ZIP_DEFLATED)
    assert z

    # Should be 2 files .asc .prj
    assert len(z.namelist()) == 2

    # find the first asc file
    asc_filename = filter(lambda x: x.endswith('.asc'), z.namelist())[0]

    with z.open(asc_filename, 'r') as f:
        data = f.read()

    assert data == '''ncols        3
nrows        2
xllcorner    -122.500000000000
yllcorner    53.000000000000
dx           -0.500000000000
dy           1.000000000000
NODATA_value  -9999
 0 1 2
 3 4 5
'''


def test_multi_layer_dataset(multi_layer_app, temp_file):
    req = Request.blank('/')
    resp = req.get_response(multi_layer_app)
    assert resp.status == '200 OK'

    for chunk in resp.app_iter:
        temp_file.write(chunk)
    temp_file.flush()
    
    z = ZipFile(temp_file.name, 'r', ZIP_DEFLATED)
    assert z

    # Should be 2 files for each layer
    assert len(z.namelist()) == 2 * 4
    assert 'my_grid_0.asc' in z.namelist()


    # find the first asc file
    asc_filename = filter(lambda x: x.endswith('.asc'), z.namelist())[0]

    with z.open(asc_filename, 'r') as f:
        data = f.read()

    assert data == '''ncols        3
nrows        2
xllcorner    -122.500000000000
yllcorner    53.000000000000
dx           -0.500000000000
dy           1.000000000000
NODATA_value  -9999
 0 1 2
 3 4 5
'''

def test_real_data(real_data_test, temp_file):
    req = Request.blank('/pr+tasmax+tasmin_day_BCCA+ANUSPLIN300+ACCESS1-0_historical+rcp45_r1i1p1_19500101-21001231.h5.aig?tasmax&')
    resp = req.get_response(real_data_test)
    assert resp.status == '200 OK'
    print resp.body

    for chunk in resp.app_iter:
        temp_file.write(chunk)
    temp_file.flush()
    
    z = ZipFile(temp_file.name, 'r', ZIP_DEFLATED)
    assert z

    assert len(z.namelist()) == 2 # 1 layer (1 ascii file, 1 projection file)

def test_find_missval():
    grid = GridType('my_grid')

    assert find_missval(grid) == None

    grid.attributes['missing_value'] = np.array([9999])
    assert find_missval(grid) == 9999

    # _FillValue should take precendence over missing_value
    grid.attributes['_FillValue'] = np.array([0])
    assert find_missval(grid) == 0


def test_detect_dataset_transform(single_layer_dataset):

    with pytest.raises(Exception) as excinfo:
        detect_dataset_transform(single_layer_dataset)
    assert excinfo.value.message.startswith('Dataset must be of type Grid')

    assert detect_dataset_transform(single_layer_dataset['my_grid']) == [-122.5, -0.5, 0, 51.0, 0, 1.0]

def test_get_map(single_dimension_dataset):
    dst = DatasetType('my_dataset')

    with pytest.raises(Exception) as excinfo:
        get_map(dst, 'X')

    dst = GridType('my_grid')
    assert get_map(dst, 'X') == None

    grid = single_dimension_dataset['my_grid']
    numpy.testing.assert_array_equal(get_map(grid, 'X'), grid['x'])
    assert get_map(grid, 'does_not_exist') == None
