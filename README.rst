=======================
pydap.responses.aaigrid
=======================

This package implements a Pydap responder which returns Arc/Info ASCII Grid files for a certain subset of DAP requests. The package uses the `Geospatial Data Abstraction Library (GDAL) <http://www.gdal.org>`_ to perform the format conversion.

--------------
How to Install
--------------

One can install pydap.responses.aaigrid using the standard methods of any other Python package.

1. clone our repository and run the setup script

    $ git clone https://github.com/pacificclimate/pydap.responses.aaigrid
    $ cd pydap.responses.aaigrid
    $ python setup.py install

2. or just point `pip` to our `GitHub repo <https://github.com/pacificclimate/pydap.responses.aaigrid>`_:

    $ pip install git+https://github.com/pacificclimate/pydap.responses.aaigrid

------------
Requirements
------------

* numpy
* gdal
* `pydap_pdp <https://github.com/pacificclimate/pydap-pdp>`_ - This is the `Pacific Climate Impacts Consortium's <http://www.pacificclimate.org>`_ fork of Pydap version 3.1. When Pydap 3.2 is released, we hope to merge our fork and require Pydap's main line.

------------------
Installation Notes
------------------

Relying on setuptools/pip to install dependencies may produce some version inconsistencies. If this happens, make sure to install the correct versions of GDAL (and possibly h5py) before installing pydap.responses.aaigrid.

    virtualenv devenv
    devenv/bin/pip install GDAL==$(gdal-config --version)

Furthermore, h5py installation may fail until `this patch <https://github.com/h5py/h5py/commit/93377e41b6c8427fa71497431a03f53e85211bbf>'_ is included in the released version. Manually install cython first to fix this.

-----------
Limitations
-----------

ArcInfo/ASCII Grid files are not multidimensional, while DAP datasets *can* be. In fact, each of these files can only represent a map (lat vs. lon) at one single timestep. Because of this, the download response is a bit different than most other Pydap responses. Each response will consist of a Zip archive which contains one .asc file and one .prj (projection) file for each time step. Users of this format for long timeseries data should be forewarned that Arc will not perform well when attempting to load dozens (or hundreds, or thousands!) of layers in one session.

-----------
Development
-----------

1. Install a development version into a virtualenv

    git clone https://github.com/pacificclimate/pydap.responses.aaigrid
    cd pydap.responses.aaigrid
    virtualenv devenv
    export CPLUS_INCLUDE_PATH=/usr/include/gdal #GDAL may not correctly source its library paths
    export C_INCLUDE_PATH=/usr/include/gdal
    devenv/bin/pip install GDAL==$(gdal-config --version) cython
    devenv/bin/pip install -r requirements.txt -r test_requirements.txt -i http://tools.pacificclimate.org/pypiserver
    devenv/bin/python setup.py develop

2. Make changes
3. Run tests

    devenv/bin/py.test -vv --tb=short tests
