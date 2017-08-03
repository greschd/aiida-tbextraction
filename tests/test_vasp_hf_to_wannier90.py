#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ase.io.vasp import read_vasp

def test_vasp_hf_to_wannier90(configure_with_daemon, sample, assert_finished):
    from aiida.orm import DataFactory
    from aiida.orm.code import Code
    from aiida.orm.data.base import List
    from aiida.work.run import run
    from aiida_tbextraction.work.wannier_input.vasp import VaspToWannier90

    structure = DataFactory('structure')()
    structure.set_ase(read_vasp(sample('InSb/POSCAR')))

    Paw = DataFactory('vasp.paw')
    potentials = {
        'In': Paw.load_paw(family='pbe', symbol='In_d')[0],
        'Sb': Paw.load_paw(family='pbe', symbol='Sb')[0]
    }

    kpoints = DataFactory('array.kpoints')()
    kpoints.set_kpoints_mesh([2, 2, 2])

    wannier_projections = List()
    wannier_projections.extend(['In : s; px; py; pz', 'Sb : px; py; pz'])

    result, pid = run(
        VaspToWannier90,
        _return_pid=True,
        structure=structure,
        potentials=potentials,
        kpoints=kpoints,
        parameters=DataFactory('parameter')(dict=dict(
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
        )),
        code=Code.get_from_string('vasp'),
        wannier_parameters=DataFactory('parameter')(dict=dict(
            num_wann=14,
            num_bands=36,
            spinors=True
        )),
        wannier_projections=wannier_projections,
        calculation_kwargs=DataFactory('parameter')(dict=dict(
            _options=dict(
                resources={'num_machines': 2, 'num_mpiprocs_per_machine': 18},
                queue_name='dphys_compute',
                withmpi=True
            )
        ))
    )
    assert_finished(pid)
    assert 'wannier_input_folder' in result
    folder_list = result['wannier_input_folder'].get_folder_list()
    assert all(filename in folder_list for filename in ['wannier90.amn', 'wannier90.mmn', 'wannier90.eig'])
