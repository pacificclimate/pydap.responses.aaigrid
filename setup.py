from setuptools import setup, find_packages
from subprocess import check_output
import sys, os

version = '0.3'

def get_install_requires():
    install_requires = [
        # This isn't exactly a hard requirement (if you're not going to serve hdf5 base data), but you can't serve hdf5 data with a version _less_ than this
        # ... should probably become an "extras"
        'pydap.handlers.hdf5 >= 0.4',
        'pydap_pdp >=3.2.1'
        ]
    try:
        v = check_output(['gdal-config', '--version']).strip()
        v = v.rsplit('.', 1)[0] #Strip bugfix version
        gdal_requirement = 'gdal =={}'.format(v)
    except:
        gdal_requirement = 'gdal'
    install_requires.append(gdal_requirement)
    return install_requires

setup(name = 'pydap.responses.aaigrid',
    version = version,
    description = "Pydap response that returns an Arc/Info ASCII Grid representation of the dataset",
    keywords = 'arcinfo pydap opendap dods',
    author = 'James Hiebert',
    author_email = 'hiebert@uvic.ca',
    packages = find_packages('src'),
    package_dir = {'': 'src'},
    namespace_packages = ['pydap', 'pydap.responses'],
    package_data = {'pydap.responses.aaigrid': ['data/*.h5']},
    include_package_data = True,
    zip_safe = True,
    install_requires = get_install_requires(),
    tests_require = ['pytest', 'numpy', 'pydap.handlers.hdf5'],
    entry_points = """
        [pydap.response]
        aig = pydap.responses.aaigrid:AAIGridResponse
    """,
    classifiers = """Development Status :: 3 - Alpha
Intended Audience :: Developers
Intended Audience :: Science/Research
Operating System :: OS Independent
Programming Language :: Python :: 2.7
Topic :: Internet :: WWW/HTTP :: WSGI :: Server
License :: OSI Approved :: GNU General Public License v3 (GPLv3)
Topic :: Scientific/Engineering :: GIS""".splitlines(),
)
