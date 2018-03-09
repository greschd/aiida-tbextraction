"""
Test the workflow which searches for the optimal energy window.
"""

from __future__ import print_function

import os
import itertools

import pytest
import pymatgen
import numpy as np


@pytest.fixture
def windowsearch_builder(sample):  # pylint: disable=too-many-locals
    from aiida.orm import DataFactory
    from aiida.orm.code import Code
    from aiida.orm.data.base import List, Float
    from aiida_bands_inspect.io import read_bands
    from aiida_tbextraction.energy_windows.windowsearch import WindowSearch
    from aiida_tbextraction.model_evaluation import BandDifferenceModelEvaluation

    builder = WindowSearch.get_builder()

    input_folder = DataFactory('folder')()
    input_folder_path = sample('wannier_input_folder')
    for filename in os.listdir(input_folder_path):
        input_folder.add_path(
            os.path.abspath(os.path.join(input_folder_path, filename)),
            filename
        )
    builder.wannier_input_folder = input_folder

    builder.wannier_code = Code.get_from_string('wannier90')
    builder.tbmodels_code = Code.get_from_string('tbmodels')

    builder.model_evaluation_workflow = BandDifferenceModelEvaluation
    builder.model_evaluation = {
        'bands_inspect_code': Code.get_from_string('bands_inspect'),
    }
    builder.reference_bands = read_bands(sample('bands.hdf5'))

    initial_window = List()
    initial_window.extend([-4.5, -4, 6.5, 16])
    builder.initial_window = initial_window
    builder.window_tol = Float(0.5)

    a = 3.2395  # pylint: disable=invalid-name
    structure = DataFactory('structure')()
    structure.set_pymatgen_structure(
        pymatgen.Structure(
            lattice=[[0, a, a], [a, 0, a], [a, a, 0]],
            species=['In', 'Sb'],
            coords=[[0] * 3, [0.25] * 3]
        )
    )
    builder.structure = structure
    wannier_parameters = DataFactory('parameter')(
        dict=dict(
            num_wann=14,
            num_bands=36,
            dis_num_iter=1000,
            num_iter=0,
            spinors=True,
            mp_grid=[6, 6, 6],
        )
    )
    builder.wannier_parameters = wannier_parameters
    builder.wannier_calculation_kwargs = dict(
        options={
            'resources': {
                'num_machines': 1,
                'tot_num_mpiprocs': 1
            },
            'withmpi': False
        }
    )

    builder.symmetries = DataFactory('singlefile')(
        file=sample('symmetries.hdf5')
    )
    slice_idx = List()
    slice_idx.extend([0, 2, 3, 1, 5, 6, 4, 7, 9, 10, 8, 12, 13, 11])
    builder.slice_idx = slice_idx

    k_values = [
        x if x <= 0.5 else -1 + x
        for x in np.linspace(0, 1, 6, endpoint=False)
    ]
    k_points = [
        list(reversed(k)) for k in itertools.product(k_values, repeat=3)
    ]
    wannier_bands = DataFactory('array.bands')()
    wannier_bands.set_kpoints(k_points)
    # Just let every energy window be valid.
    wannier_bands.set_bands(np.array([[0] * 14] * len(k_points)))
    builder.wannier_bands = wannier_bands
    return builder


def test_windowsearch(configure_with_daemon, windowsearch_builder):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Run a windowsearch on the sample wannier input folder.
    """
    from aiida.work.launch import run

    result = run(windowsearch_builder)
    assert all(
        key in result for key in ['cost_value', 'tb_model', 'window', 'plot']
    )


def test_windowsearch_submit(
    configure_with_daemon, windowsearch_builder, wait_for, assert_finished
):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Submit a windowsearch workflow.
    """
    from aiida.orm import load_node
    from aiida.work.launch import submit

    pk = submit(windowsearch_builder).pk
    wait_for(pk)
    assert_finished(pk)
    result = load_node(pk).get_outputs_dict()
    assert all(
        key in result for key in ['cost_value', 'tb_model', 'window', 'plot']
    )
