from pkg_resources import resource_filename

import pytest
import numpy as np
from numpy.testing import assert_allclose

from pydap.handlers.hdf5 import HDF5Handler
from pydap.responses.aaigrid import detect_dataset_transform

def test_detect_dataset_transform(single_layer_dataset):
    xform = detect_dataset_transform(single_layer_dataset['my_grid'])
    assert xform == [-122.5, -0.5, 0, 51.0, 0, 1.0]

def test_dectect_transform_on_real_data():
    test_h5 = resource_filename('pydap.responses.aaigrid', 'data/bcca_canada.h5')
    handler = HDF5Handler(test_h5)
    xform = np.array(detect_dataset_transform(handler.dataset['tasmax']))
    expected = np.array([-141.041, 0.083, 0, 83.541, 0, 0.083])
    assert_allclose(xform, expected, rtol=1e-02)

def test_wrong_dataset_type(single_layer_dataset):
    with pytest.raises(Exception) as excinfo:
        xform = detect_dataset_transform(single_layer_dataset)

    assert excinfo.value.message.startswith("Dataset must be of type Grid")


