# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Test for the workflow that optimizes DFT-based tight-binding models.
"""

from __future__ import print_function

import pytest

from insb_sample import *  # pylint: disable=unused-wildcard-import


@pytest.mark.vasp
def test_fp_tb(
    configure_with_daemon,  # pylint: disable=unused-argument
    get_fp_tb_input,  # pylint: disable=redefined-outer-name
):
    """
    Runs the DFT tight-binding workflow on an InSb sample.
    """
    from aiida.engine import run
    from aiida.orm.querybuilder import QueryBuilder
    from aiida_bands_inspect.calculations.difference import DifferenceCalculation
    from aiida_tbextraction.fp_tb import FirstPrinciplesTightBinding

    query = QueryBuilder()
    query.append(DifferenceCalculation)

    result = run(FirstPrinciplesTightBinding, **get_fp_tb_input)
    print(result)
    assert all(key in result for key in ['cost_value', 'tb_model'])


@pytest.mark.vasp
def test_fp_tb_submit(
    configure_with_daemon,  # pylint: disable=unused-argument
    get_fp_tb_input,  # pylint: disable=redefined-outer-name
    wait_for,
):
    """
    Submits the DFT tight-binding workflow on an InSb sample.
    """
    from aiida.orm import load_node
    from aiida.engine.launch import submit
    from aiida.orm.querybuilder import QueryBuilder
    from aiida_bands_inspect.calculations.difference import DifferenceCalculation
    from aiida_tbextraction.fp_tb import FirstPrinciplesTightBinding

    query = QueryBuilder()
    query.append(DifferenceCalculation)

    pk = submit(FirstPrinciplesTightBinding, **get_fp_tb_input).pk
    wait_for(pk)
    result = load_node(pk).get_outputs_dict()
    print(result)
    assert all(key in result for key in ['cost_value', 'tb_model'])
