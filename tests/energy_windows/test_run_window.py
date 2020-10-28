# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Tests for the workflow which evaluates a single set of energy window values.
"""

import os
import itertools

import pytest
import pymatgen
import numpy as np

from aiida import orm
from aiida.engine import run_get_node
from aiida_bands_inspect.io import read

from aiida_tbextraction.model_evaluation import BandDifferenceModelEvaluation
from aiida_tbextraction.energy_windows.run_window import RunWindow


@pytest.fixture
def run_window_builder(test_data_dir, code_wannier90, insb_structure):
    """
    Returns a function that creates the input for RunWindow tests.
    """
    def inner(window_values, slice_, symmetries):
        builder = RunWindow.get_builder()

        input_folder = orm.FolderData()
        input_folder_path = test_data_dir / 'wannier_input_folder'
        for filename in os.listdir(input_folder_path):
            input_folder.put_object_from_file(
                str((input_folder_path / filename).resolve()), filename
            )
        builder.wannier.local_input_folder = input_folder

        builder.wannier.code = code_wannier90
        builder.code_tbmodels = orm.Code.get_from_string('tbmodels')
        builder.model_evaluation_workflow = BandDifferenceModelEvaluation
        builder.reference_structure = insb_structure
        builder.reference_bands = read(test_data_dir / 'bands.hdf5')
        builder.model_evaluation = {
            'code_bands_inspect': orm.Code.get_from_string('bands_inspect'),
        }

        window = orm.List(list=window_values)
        builder.window = window

        k_values = [
            x if x <= 0.5 else -1 + x
            for x in np.linspace(0, 1, 6, endpoint=False)
        ]
        k_points = [
            list(reversed(k)) for k in itertools.product(k_values, repeat=3)
        ]
        wannier_kpoints = orm.KpointsData()
        wannier_kpoints.set_kpoints(k_points)
        builder.wannier.kpoints = wannier_kpoints

        wannier_bands = orm.BandsData()
        wannier_bands.set_kpoints(k_points)
        # Just let every energy window be valid.
        wannier_bands.set_bands(
            np.array([[-20] * 10 + [-0.5] * 7 + [0.5] * 7 + [20] * 12] *
                     len(k_points))
        )
        builder.wannier_bands = wannier_bands

        a = 3.2395  # pylint: disable=invalid-name
        structure = orm.StructureData()
        structure.set_pymatgen_structure(
            pymatgen.Structure(
                lattice=[[0, a, a], [a, 0, a], [a, a, 0]],
                species=['In', 'Sb'],
                coords=[[0] * 3, [0.25] * 3]
            )
        )
        builder.structure = structure
        wannier_parameters = orm.Dict(
            dict=dict(
                num_wann=14,
                num_bands=36,
                dis_num_iter=1000,
                num_iter=0,
                spinors=True,
                mp_grid=[6, 6, 6],
            )
        )
        builder.wannier.parameters = wannier_parameters
        builder.wannier.metadata.options = {
            'resources': {
                'num_machines': 1,
                'tot_num_mpiprocs': 1
            },
            'withmpi': False
        }
        builder.parse.calc.distance_ratio_threshold = orm.Float(2.)
        if symmetries:
            builder.symmetries = orm.SinglefileData(
                file=str(test_data_dir / 'symmetries.hdf5')
            )
        if slice_:
            slice_idx = orm.List()
            slice_idx.extend([0, 2, 3, 1, 5, 6, 4, 7, 9, 10, 8, 12, 13, 11])
            builder.slice_idx = slice_idx
        return builder

    return inner


@pytest.mark.parametrize('slice_', [True, False])
@pytest.mark.parametrize('symmetries', [True, False])
def test_run_window(
    configure_with_daemon, run_window_builder, slice_, symmetries
):  # pylint:disable=unused-argument,redefined-outer-name
    """
    Runs the workflow which evaluates an energy window.
    """

    result, node = run_get_node(
        run_window_builder([-4.5, -4, 6.5, 16],
                           slice_=slice_,
                           symmetries=symmetries)
    )
    assert node.is_finished_ok
    assert all(key in result for key in ['cost_value', 'tb_model', 'plot'])


@pytest.mark.parametrize(
    'window_values',
    [
        [-4.5, 6.5, -4, 16],  # unsorted
        [-30, -30, 30, 30],  # inner window too big
        [0, 0, 0, 0],  # outer window too small
    ]
)
def test_run_window_invalid(
    configure_with_daemon, run_window_builder, window_values
):  # pylint:disable=unused-argument,redefined-outer-name
    """
    Runs an the run_window workflow with invalid window values.
    """
    result, node = run_get_node(
        run_window_builder(window_values, slice_=True, symmetries=True)
    )
    assert node.is_finished_ok
    assert result['cost_value'] > 1e10
