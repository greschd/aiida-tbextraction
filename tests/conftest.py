# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Configuration file for pytest tests.
"""

import os
import pytest

pytest_plugins = [  # pylint: disable=invalid-name
    'aiida.manage.tests.pytest_fixtures', 'aiida_pytest',
    'aiida_pytest_mock_codes'
]

MOCK_CODES_DATA_DIR = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'mock_codes_data'
)


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


@pytest.fixture
def code_wannier90(mock_code_factory):
    return mock_code_factory(
        label='wannier90',
        entry_point='wannier90.wannier90',
        data_dir_abspath=MOCK_CODES_DATA_DIR,
        ignore_files=(
            '_aiidasubmit.sh', 'aiida.amn', 'aiida.chk', 'aiida.mmn'
        )
    )
