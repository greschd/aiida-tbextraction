# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Tests for running the DFT calculations needed as input for the tight-binding calculation.
"""

# pylint: disable=import-outside-toplevel

import pytest

from aiida.engine.launch import run_get_node


@pytest.mark.qe
def test_qe_fp_run(configure_with_daemon, assert_finished, get_fp_run_inputs):  # pylint: disable=unused-argument
    """Calculates the Wannier90 inputs and reference bands from QE."""

    from aiida_quantumespresso.calculations.pw import PwCalculation

    from aiida_tbextraction.fp_run import QuantumEspressoFirstPrinciplesRun

    result, node = run_get_node(
        QuantumEspressoFirstPrinciplesRun, **get_fp_run_inputs()
    )
    assert node.is_finished_ok
    assert all(
        key in result for key in [
            'wannier_input_folder', 'wannier_parameters', 'wannier_bands',
            'bands'
        ]
    )
    assert int(result['wannier_parameters'].get_attribute('num_wann')) == 14
    object_names = result['wannier_input_folder'].list_object_names()
    assert all(
        filename in object_names
        for filename in ['aiida.amn', 'aiida.mmn', 'aiida.eig']
    )

    # TODO: Check if this physically correct, or if the wave function
    # needs to be read as well.
    num_calc_checked = 0
    for descendant in node.called_descendants:
        if descendant.process_class == PwCalculation:
            if descendant.inputs.parameters.get_dict(
            )['CONTROL']['calculation'] != 'scf':
                num_calc_checked += 1
                retrieved_folder = descendant.outputs.retrieved
                with retrieved_folder.open('aiida.out') as f:
                    stdout = f.read()
                    assert 'The potential is recalculated from file' in stdout
    assert num_calc_checked == 2
