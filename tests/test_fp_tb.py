# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Test for the workflow that optimizes DFT-based tight-binding models.
"""

import pytest


@pytest.mark.qe
def test_fp_tb(
    configure_with_daemon,  # pylint: disable=unused-argument
    get_fp_tb_inputs,
):
    """
    Runs the DFT tight-binding workflow on an InSb sample.
    """
    from aiida.engine import run
    from aiida_tbextraction.fp_tb import FirstPrinciplesTightBinding

    result = run(FirstPrinciplesTightBinding, **get_fp_tb_inputs())
    print(result)
    assert all(key in result for key in ['cost_value', 'tb_model'])
