# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Tests that the entrypoints defined by aiida-tbextraction work.
"""

import pkg_resources

import pytest


@pytest.fixture
def check_entrypoints(configure):  # pylint: disable=unused-argument
    """
    Fixture to check that loading of all the workflow, calculation and parser
    entrypoints through the corresponding factory works for the given (base)
    module name.
    """

    def inner(module_name):  # pylint: disable=missing-docstring
        from aiida.parsers import ParserFactory
        from aiida.plugins.factory import WorkflowFactory, CalculationFactory
        for entrypoint_name, factory in [
            ('aiida.workflows', WorkflowFactory),
            ('aiida.calculations', CalculationFactory),
            ('aiida.parsers', ParserFactory)
        ]:
            for entry_point in pkg_resources.iter_entry_points(
                entrypoint_name
            ):
                if entry_point.module_name.split('.')[0] == module_name:
                    factory(entry_point.name)

    return inner


def test_entrypoints(check_entrypoints):  # pylint: disable=redefined-outer-name
    """
    Check that the aiida-tbextraction entrypoints are valid.
    """
    check_entrypoints('aiida_tbextraction')
