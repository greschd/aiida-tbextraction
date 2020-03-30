# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Test for the workflow that optimizes DFT-based tight-binding models.
"""

import pytest

from aiida.engine import run
from aiida_tbextraction.optimize_fp_tb import OptimizeFirstPrinciplesTightBinding


@pytest.mark.qe
def test_fp_tb(
    configure_with_daemon,  # pylint: disable=unused-argument
    get_optimize_fp_tb_input,
):
    """
    Runs the DFT tight-binding optimization workflow on an InSb sample.
    """
    result = run(
        OptimizeFirstPrinciplesTightBinding, **get_optimize_fp_tb_input()
    )
    print(result)
    assert all(key in result for key in ['cost_value', 'tb_model', 'window'])
