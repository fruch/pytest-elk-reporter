#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import codecs
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding="utf-8").read()


setup(
    name="pytest-elk-reporter",
    version="0.1.0",
    author="Israel Fruchter",
    author_email="israel.fruchter@gmail.com",
    maintainer="Israel Fruchter",
    maintainer_email="israel.fruchter@gmail.com",
    license="MIT",
    url="https://github.com/fruch/pytest-elk-reporter",
    description="A simple plugin to use with pytest",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    py_modules=["pytest_elk_reporter"],
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    install_requires=["pytest>=3.5.0", "requests", "six"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={"pytest11": ["elk-reporter = pytest_elk_reporter"]},
)
