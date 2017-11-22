"""
Tests the workflow which calculates the tight-binding model from a complete Wannier90 input folder and symmetry + slice inputs.
"""

import os
import itertools

import pytest
import pymatgen
import numpy as np


@pytest.mark.parametrize('slice_', [True, False])
@pytest.mark.parametrize('symmetries', [True, False])
def test_tbextraction(configure_with_daemon, sample, slice_, symmetries):  # pylint: disable=too-many-locals,unused-argument
    """
    Run the tight-binding calculation workflow, optionally including symmetrization and slicing of orbitals.
    """
    from aiida.orm import DataFactory
    from aiida.orm.code import Code
    from aiida.orm.data.base import List
    from aiida.work import run
    from aiida_tbextraction.calculate_tb import TightBindingCalculation

    inputs = dict()

    input_folder = DataFactory('folder')()
    input_folder_path = sample('wannier_input_folder')
    for filename in os.listdir(input_folder_path):
        input_folder.add_path(
            os.path.abspath(os.path.join(input_folder_path, filename)),
            filename
        )
    inputs['wannier_input_folder'] = input_folder

    inputs['wannier_code'] = Code.get_from_string('wannier90')
    inputs['tbmodels_code'] = Code.get_from_string('tbmodels')

    k_values = [
        x if x <= 0.5 else -1 + x
        for x in np.linspace(0, 1, 6, endpoint=False)
    ]
    k_points = [
        list(reversed(k)) for k in itertools.product(k_values, repeat=3)
    ]
    wannier_kpoints = DataFactory('array.kpoints')()
    wannier_kpoints.set_kpoints(k_points)
    inputs['wannier_kpoints'] = wannier_kpoints

    a = 3.2395  # pylint: disable=invalid-name
    structure = DataFactory('structure')()
    structure.set_pymatgen_structure(
        pymatgen.Structure(
            lattice=[[0, a, a], [a, 0, a], [a, a, 0]],
            species=['In', 'Sb'],
            coords=[[0] * 3, [0.25] * 3]
        )
    )
    inputs['structure'] = structure

    wannier_parameters = DataFactory('parameter')(
        dict=dict(
            num_wann=14,
            num_bands=36,
            dis_num_iter=1000,
            num_iter=0,
            dis_win_min=-4.5,
            dis_win_max=16.,
            dis_froz_min=-4,
            dis_froz_max=6.5,
            spinors=True,
            mp_grid=[6, 6, 6]
        )
    )
    inputs['wannier_parameters'] = wannier_parameters
    inputs['wannier_calculation_kwargs'] = DataFactory('parameter')(
        dict=dict(
            _options={
                'resources': {
                    'num_machines': 1,
                    'tot_num_mpiprocs': 1
                },
                'withmpi': False
            }
        )
    )
    if symmetries:
        inputs['symmetries'] = DataFactory('singlefile')(
            file=sample('symmetries.hdf5')
        )
    if slice_:
        slice_idx = List()
        slice_idx.extend([0, 2, 3, 1, 5, 6, 4, 7, 9, 10, 8, 12, 13, 11])
        inputs['slice_idx'] = slice_idx

    result = run(TightBindingCalculation, **inputs)
    assert 'tb_model' in result
