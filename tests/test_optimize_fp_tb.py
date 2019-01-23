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
    get_optimize_fp_tb_input,  # pylint: disable=redefined-outer-name
):
    """
    Runs the DFT tight-binding optimization workflow on an InSb sample.
    """
    from aiida.work import run
    from aiida.orm.querybuilder import QueryBuilder
    from aiida_bands_inspect.calculations.difference import DifferenceCalculation
    from aiida_tbextraction.optimize_fp_tb import OptimizeFirstPrinciplesTightBinding

    query = QueryBuilder()
    query.append(DifferenceCalculation)

    result = run(
        OptimizeFirstPrinciplesTightBinding, **get_optimize_fp_tb_input
    )
    print(result)
    assert all(key in result for key in ['cost_value', 'tb_model', 'window'])


@pytest.mark.vasp
def test_fp_tb_submit(
    configure_with_daemon,  # pylint: disable=unused-argument
    get_optimize_fp_tb_input,  # pylint: disable=redefined-outer-name
    wait_for,
):
    """
    Runs the DFT tight-binding optimization workflow on an InSb sample.
    """
    from aiida.orm import load_node
    from aiida.work.launch import submit
    from aiida.orm.querybuilder import QueryBuilder
    from aiida_bands_inspect.calculations.difference import DifferenceCalculation
    from aiida_tbextraction.optimize_fp_tb import OptimizeFirstPrinciplesTightBinding

    query = QueryBuilder()
    query.append(DifferenceCalculation)

    pk = submit(
        OptimizeFirstPrinciplesTightBinding, **get_optimize_fp_tb_input
    ).pk
    wait_for(pk)
    result = load_node(pk).get_outputs_dict()
    print(result)
    assert all(key in result for key in ['cost_value', 'tb_model', 'window'])
