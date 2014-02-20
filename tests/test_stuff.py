from zipfile import ZipFile, ZIP_DEFLATED
from tempfile import NamedTemporaryFile
from webob.request import Request

def test_can_instantiate(app):
    assert True

def test_can_call(app, temp_file):
    req = Request.blank('/')
    resp = req.get_response(app)
    assert resp.status == '200 OK'
    for chunk in resp.app_iter:
        temp_file.write(chunk)

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
        assert f.read() == '''ncols        3
nrows        2
xllcorner    444720.000000000000
yllcorner    3751260.000000000000
cellsize     30.000000000000
NODATA_value      0
 0 4 8
 12 16 20
'''
