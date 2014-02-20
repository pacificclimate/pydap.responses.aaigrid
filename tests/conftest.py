import os
from tempfile import NamedTemporaryFile

import pytest

import numpy as np
from pydap.model import GridType, BaseType
from pydap.responses.aaigrid import AAIGridResponse

@pytest.fixture
def app():
    return AAIGridResponse(None)

@pytest.fixture
def single_layer_dataset():
    dst = GridType('my_dataset')
    dst['my_var'] = BaseType('my_var', np.arange(6).reshape(2, 3), dimensions=('y', 'x'))
    dst['x'] = BaseType('x', np.arange(3), units='degrees_east')
    dst['y'] = BaseType('y', np.arange(2), units='degrees_north')
    return dst

@pytest.fixture
def multi_layer_dataset():
    dst = GridType('my_dataset')
    dst['my_var'] = BaseType('my_var', np.arange(24).reshape(2, 3, 4), dimensions=('y', 'x', 't'))
    dst['y'] = BaseType('y', np.arange(2), units='degrees_north')
    dst['x'] = BaseType('x', np.arange(3), units='degrees_east')
    dst['t'] = BaseType('t', np.arange(4), units='days since 1950-01-01')
    return dst

@pytest.fixture
def single_layer_app(single_layer_dataset):
    return AAIGridResponse(single_layer_dataset)

@pytest.fixture
def multi_layer_app(multi_layer_dataset):
    return AAIGridResponse(multi_layer_dataset)

@pytest.fixture(scope="function")
def temp_file(request):
    f = NamedTemporaryFile(delete=False)

    def fin():
        os.remove(f.name)
    request.addfinalizer(fin)

    return f
