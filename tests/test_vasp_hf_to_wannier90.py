#!/usr/bin/env python
# -*- coding: utf-8 -*-

from insb_sample import get_insb_input

def test_vasp_hf_to_wannier90(configure_with_daemon, assert_finished, get_insb_input):
    from aiida.orm import DataFactory
    from aiida.orm.data.base import List
    from aiida.work.run import run
    from aiida_tbextraction.work.wannier_input.vasp import VaspToWannier90

    kpoints = DataFactory('array.kpoints')()
    kpoints.set_kpoints_mesh([2, 2, 2])

    wannier_projections = List()
    wannier_projections.extend(['In : s; px; py; pz', 'Sb : px; py; pz'])

    result, pid = run(
        VaspToWannier90,
        _return_pid=True,
        kpoints=kpoints,
        wannier_parameters=DataFactory('parameter')(dict=dict(
            num_wann=14,
            num_bands=36,
            spinors=True
        )),
        wannier_projections=wannier_projections,
        **get_insb_input()
    )
    assert_finished(pid)
    assert 'wannier_input_folder' in result
    folder_list = result['wannier_input_folder'].get_folder_list()
    assert all(filename in folder_list for filename in ['wannier90.amn', 'wannier90.mmn', 'wannier90.eig'])
