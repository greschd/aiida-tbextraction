#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import itertools

import pytest
import numpy as np

@pytest.mark.parametrize('slice', [True])
@pytest.mark.parametrize('symmetries', [True])
def test_runwindow(configure_with_daemon, sample, slice, symmetries):
    from aiida.orm import DataFactory
    from aiida.orm.code import Code
    from aiida.work import run
    from aiida_bandstructure_utils.io import read_bands
    from aiida_tbextraction.work.windowsearch import WindowSearch

    inputs = dict()

    input_archive = DataFactory('vasp.archive')()
    input_archive_path = sample('wannier_archive')
    for fn in os.listdir(input_archive_path):
        input_archive.add_file(os.path.abspath(os.path.join(input_archive_path, fn)), fn)
    inputs['wannier_data'] = input_archive

    inputs['wannier_code'] = Code.get_from_string('wannier90')
    inputs['tbmodels_code'] = Code.get_from_string('tbmodels')
    inputs['bandstructure_utils_code'] = Code.get_from_string('bandstructure_utils')

    window_values = DataFactory('parameter')(dict=dict(
        dis_win_min=[-4.5, -3.9],
        dis_win_max=[16.],
        dis_froz_min=[-4, -3.8],
        dis_froz_max=[6.5]
    ))
    inputs['window_values'] = window_values

    k_values = [x if x <= 0.5 else -1 + x for x in np.linspace(0, 1, 6, endpoint=False)]
    k_points = [list(reversed(k)) for k in itertools.product(k_values, repeat=3)]
    wannier_settings = DataFactory('parameter')(
        dict=dict(
            num_wann=14,
            num_bands=36,
            dis_num_iter=1000,
            num_iter=0,
            spinors=True,
            unit_cell_cart=[
                [0, 3.2395, 3.2395],
                [3.2395, 0, 3.2395],
                [3.2395, 3.2395, 0]
            ],
            atoms_cart=[
                ['In       0.0000000     0.0000000     0.0000000'],
                ['Sb       1.6197500     1.6197500     1.6197500']
            ],
            mp_grid='6 6 6',
            kpoints=k_points
        )
    )
    inputs['wannier_settings'] = wannier_settings
    inputs['wannier_calculation_kwargs'] = DataFactory('parameter')(dict=dict(_options={'resources': {'num_machines': 1, 'tot_num_mpiprocs': 1}, 'withmpi': False}))
    if symmetries:
        inputs['symmetries'] = DataFactory('singlefile')(file=sample('symmetries.hdf5'))
    if slice:
        inputs['slice_idx'] = DataFactory('tbmodels.list')(value=[0, 2, 3, 1, 5, 6, 4, 7, 9, 10, 8, 12, 13, 11])

    inputs['reference_bands'] = read_bands(sample('bands.hdf5'))

    result = run(
        WindowSearch,
        **inputs
    )
    print(result)
    assert all(key in result for key in ['difference', 'tb_model', 'window'])
