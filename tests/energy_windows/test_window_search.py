# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Test the workflow which searches for the optimal energy window.
"""

import os
import itertools

import pytest
import pymatgen
import numpy as np

from aiida import orm
from aiida.orm import load_node
from aiida.engine import run, submit
from aiida_bands_inspect.io import read

from aiida_tbextraction.energy_windows.window_search import WindowSearch
from aiida_tbextraction.model_evaluation import BandDifferenceModelEvaluation


@pytest.fixture
def window_search_builder(test_data_dir, code_wannier90, insb_structure):  # pylint: disable=too-many-locals,useless-suppression
    """
    Sets up the process builder for window_search tests, and adds the inputs.
    """

    builder = WindowSearch.get_builder()

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
    # print(builder.model_evaluation.dynamic)
    builder.model_evaluation = {
        'code_bands_inspect': orm.Code.get_from_string('bands_inspect'),
    }
    builder.reference_bands = read(test_data_dir / 'bands.hdf5')
    builder.reference_structure = insb_structure

    initial_window = orm.List()
    initial_window.extend([-4.5, -4, 6.5, 16])
    builder.initial_window = initial_window
    builder.window_tol = orm.Float(1.5)

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

    builder.symmetries = orm.SinglefileData(
        file=str((test_data_dir / 'symmetries.hdf5').resolve())
    )
    slice_idx = orm.List()
    slice_idx.extend([0, 2, 3, 1, 5, 6, 4, 7, 9, 10, 8, 12, 13, 11])
    builder.slice_idx = slice_idx

    k_values = [
        x if x <= 0.5 else -1 + x
        for x in np.linspace(0, 1, 6, endpoint=False)
    ]
    k_points = [
        list(reversed(k)) for k in itertools.product(k_values, repeat=3)
    ]
    wannier_bands = orm.BandsData()
    wannier_bands.set_kpoints(k_points)
    # Just let every energy window be valid.
    wannier_bands.set_bands(np.array([[0] * 14] * len(k_points)))
    builder.wannier_bands = wannier_bands
    return builder


def test_window_search(configure_with_daemon, window_search_builder):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Run a window_search on the sample wannier input folder.
    """
    result = run(window_search_builder)
    assert all(
        key in result for key in ['cost_value', 'tb_model', 'window', 'plot']
    )


def test_window_search_submit(
    configure_with_daemon, window_search_builder, wait_for, assert_finished
):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Submit a window_search workflow.
    """
    pk = submit(window_search_builder).pk
    wait_for(pk)
    assert_finished(pk)
    node = load_node(pk)
    assert all(
        key in node.outputs
        for key in ['cost_value', 'tb_model', 'window', 'plot']
    )
