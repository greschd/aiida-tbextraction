#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from ase.io.vasp import read_vasp

@pytest.fixture
def get_insb_input(configure, sample, queue_name):
    def inner():
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
                queue_name=queue_name,
                withmpi=True,
                max_wallclock_seconds=600
            )
        ))
        return res
    return inner
