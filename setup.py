from setuptools import setup, find_packages

setup(
    name='tomo-align',
    version=open('VERSION').read().strip(),
    #version=__version__,
    author='Alan Kastengren',
    author_email='akastengren@anl.gov',
    url='https://github.com/aps-7bm/7bm-tomo',
    packages=find_packages(),
    include_package_data = True,
    scripts=['bin/tomo-align'],
    description='cli to align tomo scans at APS 7-BM',
    zip_safe=False,
)

