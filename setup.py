from setuptools import setup, find_packages

version = '0.7'

install_requires = [
    'pydap_pdp >=3.2.3',
    'gdal'
]

setup(
    name='pydap.responses.aaigrid',
    version=version,
    description="Pydap response that returns an Arc/Info ASCII Grid "
                "representation of the dataset",
    keywords='arcinfo pydap opendap dods',
    author='James Hiebert',
    author_email='hiebert@uvic.ca',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['pydap', 'pydap.responses'],
    package_data={'pydap.responses.aaigrid': ['data/*.h5']},
    include_package_data=True,
    zip_safe=True,
    install_requires=install_requires,
    tests_require=['pytest', 'numpy', 'pydap.handlers.hdf5'],
    entry_points="""
    [pydap.response]
    aig = pydap.responses.aaigrid:AAIGridResponse
    """,
    classifiers="""Development Status :: 3 - Alpha
Intended Audience :: Developers
Intended Audience :: Science/Research
Operating System :: OS Independent
Programming Language :: Python :: 2.7
Topic :: Internet :: WWW/HTTP :: WSGI :: Server
License :: OSI Approved :: GNU General Public License v3 (GPLv3)
Topic :: Scientific/Engineering :: GIS""".splitlines(),
)
