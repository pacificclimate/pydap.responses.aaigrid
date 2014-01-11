from setuptools import setup, find_packages
import sys, os

#here = os.path.abspath(os.path.dirname(__file__))
#README = open(os.path.join(here, 'README.rst')).read()
#NEWS = open(os.path.join(here, 'NEWS.txt')).read()

version = '0.1dev'

install_requires = [
    'pydap >=3.2.1',
    'gdal'
]

sw_path = 'hg+ssh://medusa.pcic.uvic.ca//home/data/projects/comp_support/software'

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
    dependency_links = ['{0}/Pydap-3.2@3.2.1#egg=Pydap-3.2.1'.format(sw_path)],
    license='GPL',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    namespace_packages = ['pydap', 'pydap.responses'],
    include_package_data=True,
    zip_safe=True,
    install_requires=install_requires,
    entry_points="""
        [pydap.response]
        aig = pydap.responses.aaigrid:AAIGridResponse
    """,
)
