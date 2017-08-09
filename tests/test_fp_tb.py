#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools

import pytest
import pymatgen
import numpy as np

from insb_sample import get_insb_input

@pytest.mark.parametrize('slice', [True])
@pytest.mark.parametrize('symmetries', [True])
def test_runwindow(
    configure_with_daemon,
    sample,
    get_insb_input,
    slice,
    symmetries
):
    from aiida.orm import DataFactory
    from aiida.orm.data.base import List
    from aiida.orm.code import Code
    from aiida.work import run
    from aiida_tbextraction.work.reference_bands.vasp_hybrids import VaspHybridsBands
    from aiida_tbextraction.work.wannier_input.vasp import VaspToWannier90
    from aiida_tbextraction.work.first_principles_tb import FirstPrinciplesTbExtraction

    inputs = dict()

    inputs['reference_bands_workflow'] = VaspHybridsBands
    inputs['to_wannier90_workflow'] = VaspToWannier90

    vasp_inputs = get_insb_input()
    vasp_code = vasp_inputs.pop('code')
    inputs['reference_bands_code'] = vasp_code
    inputs['to_wannier90_code'] = vasp_code
    vasp_parameters = vasp_inputs.pop('parameters')
    inputs['reference_bands_parameters'] = vasp_parameters
    inputs['to_wannier90_parameters'] = vasp_parameters
    vasp_calculation_kwargs = vasp_inputs.pop('calculation_kwargs')
    inputs['reference_bands_calculation_kwargs'] = vasp_calculation_kwargs
    inputs['to_wannier90_calculation_kwargs'] = vasp_calculation_kwargs
    # structure, potentials
    inputs.update(vasp_inputs)
    kpoints = DataFactory('array.kpoints')()
    kpoints.set_kpoints_path([('G', (0, 0, 0), 'M', (0.5, 0.5, 0.5))])
    inputs['kpoints'] = kpoints
    kpoints_mesh = DataFactory('array.kpoints')()
    kpoints_mesh.set_kpoints_mesh([2, 2, 2])
    inputs['kpoints_mesh'] = kpoints_mesh

    inputs['wannier_code'] = Code.get_from_string('wannier90')
    inputs['tbmodels_code'] = Code.get_from_string('tbmodels')
    inputs['bands_inspect_code'] = Code.get_from_string('bands_inspect')

    window_values = DataFactory('parameter')(dict=dict(
        dis_win_min=[-10, -7, -4.5, -3.9, -3],
        dis_win_max=[15, 16., 17],
        dis_froz_min=[-4, -4, -3.8, -1],
        dis_froz_max=[2, 6, 6.5, 7]
    ))
    inputs['window_values'] = window_values

    wannier_parameters = DataFactory('parameter')(
        dict=dict(
            num_wann=14,
            num_bands=36,
            dis_num_iter=1000,
            num_iter=0,
            spinors=True,
        )
    )
    inputs['wannier_parameters'] = wannier_parameters
    wannier_projections = List()
    wannier_projections.extend(['In : s; px; py; pz', 'Sb : px; py; pz'])
    inputs['wannier_projections'] = wannier_projections
    inputs['wannier_calculation_kwargs'] = DataFactory('parameter')(dict=dict(
        _options={'resources': {'num_machines': 1, 'tot_num_mpiprocs': 1}, 'withmpi': False}
    ))
    inputs['symmetries'] = DataFactory('singlefile')(
        file=sample('symmetries.hdf5')
    )

    slice_idx = List()
    slice_idx.extend([0, 2, 3, 1, 5, 6, 4, 7, 9, 10, 8, 12, 13, 11])
    inputs['slice_idx'] = slice_idx

    result = run(
        FirstPrinciplesTbExtraction,
        **inputs
    )
    print(result)
    assert all(key in result for key in ['difference', 'tb_model', 'window'])
