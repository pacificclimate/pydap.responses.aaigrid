from setuptools import setup, find_packages
import sys, os

#here = os.path.abspath(os.path.dirname(__file__))
#README = open(os.path.join(here, 'README.rst')).read()
#NEWS = open(os.path.join(here, 'NEWS.txt')).read()

version = '0.1'

install_requires = [
    'pydap.handlers.hdf5 >= 0.4', # This isn't exactly a hard requirement (if you're not going to serve hdf5 base data), but you can't serve hdf5 data with a version _less_ than this
    'pydap >=3.2.1',
    'gdal'
]

setup(name='pydap.responses.aaigrid',
    version=version,
    description="Pydap response that returns an Arc/Info ASCII Grid representation of the dataset",
    long_description="",#README + '\n\n' + NEWS,
    classifiers=[
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    ],
    keywords='arcinfo pydap opendap dods',
    author='James Hiebert',
    author_email='james@hiebert.name',
    dependency_links = ['https://github.com/pacificclimate/pydap-pdp/tarball/master#egg=Pydap-3.2.2',
                        'https://github.com/pacificclimate/pydap.handlers.hdf5/tarball/master#egg=pydap.handlers.hdf5-0.5'],
    license='GPL',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    namespace_packages = ['pydap', 'pydap.responses'],
    package_data={'': ['pydap/responses/aaigrid/data/*.h5']},
    include_package_data=True,
    zip_safe=True,
    install_requires=install_requires,
    tests_require = ['pytest', 'numpy', 'pydap.handlers.hdf5'],
    entry_points="""
        [pydap.response]
        aig = pydap.responses.aaigrid:AAIGridResponse
    """,
)
