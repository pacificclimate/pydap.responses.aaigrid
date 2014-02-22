from zipfile import ZipFile, ZIP_DEFLATED
from tempfile import NamedTemporaryFile

from webob.request import Request
from webob.exc import HTTPBadRequest
import pytest

from pydap.responses.aaigrid import AAIGridResponse

def test_bad_dataset_failure():
    with pytest.raises(HTTPBadRequest) as excinfo:
        app = AAIGridResponse(None)

    assert "only supports GridType" in excinfo.value.message

def test_single_dimension_failure(single_dimension_dataset):
    with pytest.raises(HTTPBadRequest) as excinfo:
        app = AAIGridResponse(single_dimension_dataset)

    assert "supports Grids with 2 or 3 dimensions, not the requested 1" in excinfo.value.message

def test_four_dimension_failure(four_dimension_dataset):
    with pytest.raises(HTTPBadRequest) as excinfo:
        app = AAIGridResponse(four_dimension_dataset)

    assert "supports Grids with 2 or 3 dimensions, not the requested 4" in excinfo.value.message

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

    # Should be 3 files .aux.xml .asc .prj
    assert len(z.namelist()) == 3

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
NODATA_value      0
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

    # Should be 3 files for each layer
    assert len(z.namelist()) == 3 * 4

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
NODATA_value      0
 0 4 8
 12 16 20
'''
