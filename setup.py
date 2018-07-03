from __future__ import (absolute_import, division, print_function)

import setuptools

setuptools.setup(
    name='pygerm',
    version='0.0.1',
    author='NSLS-II',
    author_email=None,
    license="BSD (3-clause)",
    url="https://github.com/NSLS-II/GeRM",
    packages=setuptools.find_packages(),
    install_requires=['pyzmq', 'numpy', 'dask'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
)
