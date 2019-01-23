# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Configuration file for pytest tests.
"""

import pytest

from aiida_pytest import *  # pylint: disable=unused-wildcard-import,redefined-builtin
from aiida_pytest import pytest_addoption as _pytest_addoption


def pytest_addoption(parser):  # pylint: disable=function-redefined
    _pytest_addoption(parser)
    parser.addoption(
        '--skip-vasp',
        action='store_true',
        help='Skip tests which require VASP.'
    )


def pytest_configure(config):
    # register additional marker
    config.addinivalue_line("markers", "vasp: mark tests which run with VASP")


def pytest_runtest_setup(item):  # pylint: disable=missing-docstring
    try:
        vasp_marker = item.get_marker("vasp")
    except AttributeError:
        vasp_marker = item.get_closest_marker('vasp')
    if vasp_marker is not None:
        if item.config.getoption("--skip-vasp"):
            pytest.skip("Test runs only with VASP.")
