#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ase.io.vasp import read_vasp

def test_vasp_hybrid_bands(configure_with_daemon, sample, assert_finished):
    from aiida.orm import DataFactory
    from aiida.orm.code import Code
    from aiida.work.run import run
    from aiida_tbextraction.work.reference_bands.vasp_hybrids import VaspHybridsBands

    structure = DataFactory('structure')()
    structure.set_ase(read_vasp(sample('InSb/POSCAR')))

    Paw = DataFactory('vasp.paw')
    potentials = {
        'In': Paw.load_paw(family='pbe', symbol='In_d')[0],
        'Sb': Paw.load_paw(family='pbe', symbol='Sb')[0]
    }

    kpoints_mesh = DataFactory('array.kpoints')()
    kpoints_mesh.set_kpoints_mesh([2, 2, 2])

    kpoints = DataFactory('array.kpoints')()
    kpoints.set_kpoints_path([('G', (0, 0, 0), 'M', (0.5, 0.5, 0.5))])

    result, pid = run(
        VaspHybridsBands,
        _return_pid=True,
        structure=structure,
        potentials=potentials,
        kpoints=kpoints,
        kpoints_mesh=kpoints_mesh,
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
        calculation_kwargs=DataFactory('parameter')(dict=dict(
            _options=dict(
                resources={'num_machines': 2, 'num_mpiprocs_per_machine': 18},
                queue_name='dphys_compute',
                withmpi=True
            )
        ))
    )
    assert_finished(pid)
    assert 'bands' in result
