# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Tests for running the DFT calculations needed as input for the tight-binding calculation.
"""

# pylint: disable=import-outside-toplevel

import tempfile

import pytest

from numpy.testing import assert_allclose

from w90utils.io import read_mmn
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


@pytest.mark.qe
def test_qe_fp_run_batched_pw2wannier(
    configure_with_daemon, assert_finished, get_fp_run_inputs
):  # pylint: disable=unused-argument
    """Calculates the Wannier90 inputs and reference bands from QE."""

    from aiida_quantumespresso.calculations.pw import PwCalculation
    from aiida_quantumespresso.calculations.pw2wannier90 import Pw2wannier90Calculation

    from aiida_tbextraction.fp_run import QuantumEspressoFirstPrinciplesRun

    result_reference, _ = run_get_node(
        QuantumEspressoFirstPrinciplesRun, **get_fp_run_inputs()
    )
    result_batched, node_batched = run_get_node(
        QuantumEspressoFirstPrinciplesRun,
        **get_fp_run_inputs(pw2wannier_bands_batchsize=20)
    )
    assert node_batched.is_finished_ok
    assert all(
        key in result_batched for key in [
            'wannier_input_folder', 'wannier_parameters', 'wannier_bands',
            'bands'
        ]
    )
    assert int(
        result_batched['wannier_parameters'].get_attribute('num_wann')
    ) == 14
    object_names = result_batched['wannier_input_folder'].list_object_names()
    assert all(
        filename in object_names
        for filename in ['aiida.amn', 'aiida.mmn', 'aiida.eig']
    )

    # TODO: Check if this physically correct, or if the wave function
    # needs to be read as well.
    num_calc_checked = 0
    for descendant in node_batched.called_descendants:
        if descendant.process_class == PwCalculation:
            if descendant.inputs.parameters.get_dict(
            )['CONTROL']['calculation'] != 'scf':
                num_calc_checked += 1
                retrieved_folder = descendant.outputs.retrieved
                with retrieved_folder.open('aiida.out') as f:
                    stdout = f.read()
                    assert 'The potential is recalculated from file' in stdout
    assert num_calc_checked == 2

    # check that MMN are the same for reference and batched mode
    def _get_mmn(wann_input_folder):
        with tempfile.NamedTemporaryFile(mode='w') as tmpf:
            with wann_input_folder.open('aiida.mmn') as mmn_f:
                tmpf.write(mmn_f.read())
            return read_mmn(tmpf.name)

    mmn_reference = _get_mmn(result_reference['wannier_input_folder'])
    mmn_batched = _get_mmn(result_batched['wannier_input_folder'])

    assert_allclose(mmn_reference, mmn_batched)
    # 36 bands, max. batchsize 20 -> 4 band groups
    #       (4 * 3) / 2 = 6 MMN calculations
    #       one AMN calculation
    assert len([
        descendant for descendant in node_batched.called_descendants
        if descendant.process_class == Pw2wannier90Calculation
    ]) == 7
