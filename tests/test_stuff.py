from tempfile import NamedTemporaryFile
from webob.request import Request

def test_can_instantiate(app):
    assert True

def test_can_call(app):
    req = Request.blank('/')
    resp = req.get_response(app)
    assert resp.status == '200 OK'
    with NamedTemporaryFile(delete=False) as f:
        for chunk in resp.app_iter:
            f.write(chunk)
