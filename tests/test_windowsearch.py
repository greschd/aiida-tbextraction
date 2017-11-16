import os
import itertools

import pytest
import pymatgen
import numpy as np


@pytest.mark.parametrize('slice', [True])
@pytest.mark.parametrize('symmetries', [True])
def test_windowsearch(configure_with_daemon, sample, slice, symmetries):
    from aiida.orm import DataFactory
    from aiida.orm.code import Code
    from aiida.orm.data.base import List
    from aiida.work import run
    from aiida_bands_inspect.io import read_bands
    from aiida_tbextraction.helpers.windowsearch import WindowSearch
    from aiida_tbextraction.model_evaluation import BandDifferenceModelEvaluation

    inputs = dict()

    input_folder = DataFactory('folder')()
    input_folder_path = sample('wannier_input_folder')
    for fn in os.listdir(input_folder_path):
        input_folder.add_path(
            os.path.abspath(os.path.join(input_folder_path, fn)), fn
        )
    inputs['wannier_input_folder'] = input_folder

    inputs['wannier_code'] = Code.get_from_string('wannier90')
    inputs['tbmodels_code'] = Code.get_from_string('tbmodels')

    inputs['model_evaluation_workflow'] = BandDifferenceModelEvaluation
    inputs['model_evaluation'] = {
        'bands_inspect_code': Code.get_from_string('bands_inspect'),
    }
    inputs['reference_bands'] = read_bands(sample('bands.hdf5'))

    window_values = DataFactory('parameter')(
        dict=dict(
            dis_win_min=[-4.5, -3.9],
            dis_win_max=[16.],
            dis_froz_min=[-4, -3.8],
            dis_froz_max=[6.5]
        )
    )
    inputs['window_values'] = window_values

    a = 3.2395
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
            spinors=True,
            mp_grid=[6, 6, 6],
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
    if slice:
        slice_idx = List()
        slice_idx.extend([0, 2, 3, 1, 5, 6, 4, 7, 9, 10, 8, 12, 13, 11])
        inputs['slice_idx'] = slice_idx

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
    inputs['wannier_bands'] = wannier_bands

    result = run(WindowSearch, **inputs)
    print(result)
    assert all(key in result for key in ['cost_value', 'tb_model', 'window'])
