#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from ase.io.vasp import read_vasp

@pytest.fixture
def get_insb_input(configure, sample, get_queue_name_from_code):
    from aiida.orm import DataFactory
    from aiida.orm.code import Code

    res = dict()

    structure = DataFactory('structure')()
    structure.set_ase(read_vasp(sample('InSb/POSCAR')))
    res['structure'] = structure

    Paw = DataFactory('vasp.paw')
    res['potentials'] = {
        'In': Paw.load_paw(family='pbe', symbol='In_d')[0],
        'Sb': Paw.load_paw(family='pbe', symbol='Sb')[0]
    }

    res['parameters'] = DataFactory('parameter')(dict=dict(
        ediff=1e-3,
        lsorbit=True,
        isym=0,
        ismear=0,
        sigma=0.05,
        gga='PE',
        encut=380,
        magmom='600*0.0',
        nbands=36,
        kpar=4,
        nelmin=0,
        lwave=False,
        aexx=0.25,
        lhfcalc=True,
        hfscreen=0.23,
        algo='N',
        time=0.4,
        precfock='normal',
    ))

    res['code'] = Code.get_from_string('vasp')
    res['calculation_kwargs'] = DataFactory('parameter')(dict=dict(
        _options=dict(
            resources={'num_machines': 2, 'num_mpiprocs_per_machine': 18},
            queue_name=get_queue_name_from_code('vasp'),
            withmpi=True,
            max_wallclock_seconds=600
        )
    ))
    return res

@pytest.fixture
def get_fp_tb_input(configure, get_insb_input, sample):
    from aiida.orm import DataFactory
    from aiida.orm.data.base import List
    from aiida.orm.code import Code
    from aiida_tbextraction.work.reference_bands.vasp_hybrids import VaspHybridsBands
    from aiida_tbextraction.work.wannier_input.vasp import VaspToWannier90
    from aiida_tbextraction.work.evaluate_model.band_difference import BandDifferenceModelEvaluation

    inputs = dict()

    vasp_inputs = get_insb_input

    vasp_subwf_inputs = {
        'code': vasp_inputs.pop('code'),
        'parameters': vasp_inputs.pop('parameters'),
        'calculation_kwargs': vasp_inputs.pop('calculation_kwargs')
    }
    inputs['reference_bands_workflow'] = VaspHybridsBands
    inputs['reference_bands'] = vasp_subwf_inputs
    inputs['to_wannier90_workflow'] = VaspToWannier90
    inputs['to_wannier90'] = vasp_subwf_inputs

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

    inputs['evaluate_model_workflow'] = BandDifferenceModelEvaluation
    inputs['evaluate_model'] = {
        'bands_inspect_code': Code.get_from_string('bands_inspect')
    }

    window_values = DataFactory('parameter')(dict=dict(
        dis_win_min=[-10, -4.5, -3.9],
        dis_win_max=[16.],
        dis_froz_min=[-4, -3.8],
        dis_froz_max=[6.5]
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

    slice_reference_bands = List()
    slice_reference_bands.extend(list(range(12, 26)))
    inputs['slice_reference_bands'] = slice_reference_bands

    slice_tb_model = List()
    slice_tb_model.extend([0, 2, 3, 1, 5, 6, 4, 7, 9, 10, 8, 12, 13, 11])
    inputs['slice_tb_model'] = slice_tb_model

    return inputs
