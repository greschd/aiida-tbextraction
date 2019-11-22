# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Configuration file for pytest tests.
"""

import pytest

pytest_plugins = ['aiida_pytest']  # pylint: disable=invalid-name


def pytest_addoption(parser):
    parser.addoption(
        '--skip-qe',
        action='store_true',
        help='Skip tests which require Quantum ESPRESSO.'
    )


def pytest_configure(config):
    # register additional marker
    config.addinivalue_line("markers", "qe: mark tests which run with QE")


def pytest_runtest_setup(item):  # pylint: disable=missing-docstring
    try:
        vasp_marker = item.get_marker("qe")
    except AttributeError:
        vasp_marker = item.get_closest_marker('qe')
    if vasp_marker is not None:
        if item.config.getoption("--skip-qe"):
            pytest.skip("Test runs only with QE.")
