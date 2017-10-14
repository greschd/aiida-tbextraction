from insb_sample import get_insb_input


def test_dft_run(configure_with_daemon, assert_finished, get_insb_input):
    from aiida.orm import DataFactory
    from aiida.orm.data.base import List
    from aiida.work.run import run
    from aiida_tbextraction.dft_run import SplitDFTRun
    from aiida_tbextraction.dft_run.wannier_input import VaspWannierInput
    from aiida_tbextraction.dft_run.reference_bands import VaspHybridsReferenceBands

    KpointsData = DataFactory('array.kpoints')

    kpoints_mesh = KpointsData()
    kpoints_mesh.set_kpoints_mesh([2, 2, 2])

    kpoints = KpointsData()
    kpoints.set_kpoints_path([('G', (0, 0, 0), 'M', (0.5, 0.5, 0.5))])

    wannier_projections = List()
    wannier_projections.extend(['In : s; px; py; pz', 'Sb : px; py; pz'])

    vasp_inputs = get_insb_input

    vasp_subwf_inputs = {
        'code': vasp_inputs.pop('code'),
        'parameters': vasp_inputs.pop('parameters'),
        'calculation_kwargs': vasp_inputs.pop('calculation_kwargs')
    }

    result, pid = run(
        SplitDFTRun,
        _return_pid=True,
        reference_bands_workflow=VaspHybridsReferenceBands,
        reference_bands=vasp_subwf_inputs,
        wannier_input_workflow=VaspWannierInput,
        wannier_input=vasp_subwf_inputs,
        kpoints=kpoints,
        kpoints_mesh=kpoints_mesh,
        wannier_parameters=DataFactory('parameter')(
            dict=dict(num_wann=14, num_bands=36, spinors=True)
        ),
        wannier_projections=wannier_projections,
        **vasp_inputs
    )
    assert_finished(pid)
    assert all(
        key in result
        for key in [
            'wannier_input_folder', 'wannier_parameters', 'wannier_bands',
            'bands'
        ]
    )
    folder_list = result['wannier_input_folder'].get_folder_list()
    assert all(
        filename in folder_list
        for filename in ['wannier90.amn', 'wannier90.mmn', 'wannier90.eig']
    )
