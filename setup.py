#!/usr/bin/env python3
import os
from setuptools import setup, find_packages

repository_name = 'dataclasses_xargs'
module_name = 'dataclasses_xargs'
python_min_version = ">=3.7"

about = {}  # type: ignore
here = os.path.abspath(os.path.dirname(__file__))

with open('README.md', 'r') as f:
    readme = f.read()

setup(
    name="dataclasses_xargs",
    description="""
        An extension to the python dataclasses package that enables you to push the *args/*xargs
        to a specific field in the dataclass.
    """,
    long_description=readme,
    long_description_content_type='text/markdown',
    version="1.0.2",
    author="Lars Scheibling",
    author_email="it@scheibling.se",
    url="https://github.com/scheibling/dataclasses-xargs.git",
    py_modules=["dataclasses_xargs"],
    python_requires=python_min_version,
    install_requires=['dataclasses>=0.6'],
    license='GPLv3',
    zip_safe=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    keywords='python dataclass args xargs',
)