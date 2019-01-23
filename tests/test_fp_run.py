# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Tests for running the DFT calculations needed as input for the tight-binding calculation.
"""

import pytest

from insb_sample import get_insb_input  # pylint: disable=unused-import


@pytest.mark.vasp
def test_split_fp_run(configure_with_daemon, assert_finished, get_insb_input):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Calculates the Wannier90 inputs from VASP with hybrid functionals.
    """
    from aiida.orm import DataFactory
    from aiida.orm.data.base import List, Bool
    from aiida.work.launch import run_get_pid
    from aiida_tbextraction.fp_run import SplitFirstPrinciplesRun
    from aiida_tbextraction.fp_run.wannier_input import VaspWannierInput
    from aiida_tbextraction.fp_run.reference_bands import VaspReferenceBands

    KpointsData = DataFactory('array.kpoints')

    kpoints_mesh = KpointsData()
    kpoints_mesh.set_kpoints_mesh([2, 2, 2])

    kpoints = KpointsData()
    kpoints.set_kpoints_path([('G', (0, 0, 0), 'M', (0.5, 0.5, 0.5))])

    wannier_projections = List()
    wannier_projections.extend(['In : s; px; py; pz', 'Sb : px; py; pz'])

    vasp_inputs = get_insb_input

    vasp_subwf_inputs = {
        'code': vasp_inputs.pop('code'),
        'parameters': vasp_inputs.pop('parameters'),
        'calculation_kwargs': vasp_inputs.pop('calculation_kwargs')
    }

    num_wann = 14
    result, pid = run_get_pid(
        SplitFirstPrinciplesRun,
        reference_bands_workflow=VaspReferenceBands,
        reference_bands=dict(merge_kpoints=Bool(True), **vasp_subwf_inputs),
        wannier_input_workflow=VaspWannierInput,
        wannier_input=vasp_subwf_inputs,
        kpoints=kpoints,
        kpoints_mesh=kpoints_mesh,
        wannier_parameters=DataFactory('parameter')(
            dict=dict(num_wann=num_wann, num_bands=36, spinors=True)
        ),
        wannier_projections=wannier_projections,
        **vasp_inputs
    )
    assert_finished(pid)
    assert all(
        key in result for key in [
            'wannier_input_folder', 'wannier_parameters', 'wannier_bands',
            'bands'
        ]
    )
    assert int(result['wannier_parameters'].get_attr('num_wann')) == num_wann
    folder_list = result['wannier_input_folder'].get_folder_list()
    assert all(
        filename in folder_list
        for filename in ['wannier90.amn', 'wannier90.mmn', 'wannier90.eig']
    )


def test_combined_fp_run(
    configure_with_daemon, assert_finished, get_insb_input
):  # pylint: disable=unused-argument,redefined-outer-name,too-many-locals
    """
    Calculates the Wannier90 inputs from VASP with hybrid functionals.
    """
    from aiida.orm import DataFactory, load_node
    from aiida.orm.data.base import List, Bool
    from aiida.orm.data.parameter import ParameterData
    from aiida.orm.calculation.work import WorkCalculation
    from aiida.work.launch import run_get_pid
    from aiida_tbextraction.fp_run import VaspFirstPrinciplesRun
    from aiida_vasp.calcs.vasp import VaspCalculation  # pylint: disable=import-error,useless-suppression

    KpointsData = DataFactory('array.kpoints')

    kpoints_mesh = KpointsData()
    kpoints_mesh.set_kpoints_mesh([2, 2, 2])

    kpoints = KpointsData()
    kpoints.set_kpoints_path([('G', (0, 0, 0), 'M', (0.5, 0.5, 0.5))])

    wannier_projections = List()
    wannier_projections.extend(['In : s; px; py; pz', 'Sb : px; py; pz'])

    vasp_inputs = get_insb_input

    num_wann = 14
    result, pid = run_get_pid(
        VaspFirstPrinciplesRun,
        kpoints=kpoints,
        kpoints_mesh=kpoints_mesh,
        wannier_parameters=DataFactory('parameter')(
            dict=dict(num_wann=num_wann, num_bands=36, spinors=True)
        ),
        wannier_projections=wannier_projections,
        scf={'parameters': ParameterData(dict=dict(isym=2))},
        bands={'merge_kpoints': Bool(True)},
        **vasp_inputs
    )
    assert_finished(pid)
    assert all(
        key in result for key in [
            'wannier_input_folder', 'wannier_parameters', 'wannier_bands',
            'bands'
        ]
    )
    assert int(result['wannier_parameters'].get_attr('num_wann')) == num_wann
    folder_list = result['wannier_input_folder'].get_folder_list()
    assert all(
        filename in folder_list
        for filename in ['wannier90.amn', 'wannier90.mmn', 'wannier90.eig']
    )

    sub_workchains = []
    for label, node in load_node(pid).get_outputs(also_labels=True):
        if label == 'CALL' and isinstance(node, WorkCalculation):
            sub_workchains.append(node)

    for sub_wc in sub_workchains:
        for label, node in sub_wc.get_outputs(also_labels=True):
            if label == 'CALL' and isinstance(node, VaspCalculation):
                retrieved_folder = node.get_retrieved_node()
                with open(
                    retrieved_folder.get_abs_path('_scheduler-stdout.txt')
                ) as f:
                    stdout = f.read()
                    assert 'WAVECAR not read' not in stdout
                    assert 'reading WAVECAR' in stdout
