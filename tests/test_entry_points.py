# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Tests that the entrypoints defined by aiida-tbextraction work.
"""


def test_entrypoints(check_entrypoints):
    """
    Check that the aiida-tbextraction entrypoints are valid.
    """
    check_entrypoints('aiida_tbextraction')
