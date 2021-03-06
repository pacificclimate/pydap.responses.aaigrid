import os
from tempfile import NamedTemporaryFile
from pkg_resources import resource_filename

import pytest

import numpy as np
from pydap.model import GridType, BaseType, DatasetType
from pydap.responses.aaigrid import AAIGridResponse
from pydap.handlers.hdf5 import HDF5Handler

@pytest.fixture
def single_dimension_dataset():
    dst = DatasetType('my_dataset')
    grid = GridType('my_grid')
    grid['my_var'] = BaseType('my_var', np.arange(6), dimensions=('x'))
    grid['x'] = BaseType('x', np.arange(6), units='degrees_north', axis='X')
    dst['my_grid'] = grid

    return dst

@pytest.fixture
def single_layer_dataset():
    dst = DatasetType('my_dataset')
    grid = GridType('my_grid')
    grid['my_var'] = BaseType('my_var', np.array([[3, 4, 5], [0, 1, 2]]), dimensions=('y', 'x'))
    grid['y'] = BaseType('y', np.arange(48.0, 51.0, 1.0), units='degrees_north', axis='Y')
    grid['x'] = BaseType('x', np.arange(-122.0, -123.5, -0.5), units='degrees_east', axis='X')
    dst['my_grid'] = grid

    return dst

@pytest.fixture
def multi_layer_dataset():
    dst = DatasetType('my_dataset')
    grid = GridType('my_grid')
    grid['my_var'] = BaseType('my_var', np.arange(24).reshape(4, 2, 3)[:,::-1,...], dimensions=('t', 'y', 'x'))
    grid['t'] = BaseType('t', np.arange(4), units='days since 1950-01-01', axis='T')
    grid['y'] = BaseType('y', np.arange(48.0, 51.0, 1.0), units='degrees_north', axis='Y')
    grid['x'] = BaseType('x', np.arange(-122.0, -123.5, -0.5), units='degrees_east', axis='X')
    dst['my_grid'] = grid
    return dst

@pytest.fixture
def four_dimension_dataset():
    dst = DatasetType('my_dataset')
    grid = GridType('my_grid')
    grid['my_var'] = BaseType('my_var', np.arange(24).reshape(2, 3, 2, 2), dimensions=('y', 'x', 'z', 't'))
    grid['y'] = BaseType('y', np.arange(2), axis='Y')
    grid['x'] = BaseType('x', np.arange(3), axis='X')
    grid['z'] = BaseType('z', np.arange(2))
    grid['t'] = BaseType('t', np.arange(2))
    dst['my_grid'] = grid
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

@pytest.fixture
def real_data_test():
    test_h5 = resource_filename('pydap.responses.aaigrid', 'data/bcca_canada.h5')
    return HDF5Handler(test_h5)
