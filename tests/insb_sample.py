"""
Defines fixtures to create the InSb input for VASP and the optimization workflows.
"""

import pytest
from ase.io.vasp import read_vasp


@pytest.fixture
def get_insb_input(configure, sample, get_queue_name_from_code):  # pylint: disable=unused-argument
    """
    Create input for the VASP InSb sample.
    """
    from aiida.orm import DataFactory
    from aiida.orm.code import Code
    from aiida.orm.data.parameter import ParameterData

    res = dict()

    structure = DataFactory('structure')()
    structure.set_ase(read_vasp(sample('InSb/POSCAR')))
    res['structure'] = structure

    Paw = DataFactory('vasp.paw')  # pylint: disable=invalid-name
    res['potentials'] = {
        'In': Paw.load_paw(family='pbe', symbol='In_d')[0],
        'Sb': Paw.load_paw(family='pbe', symbol='Sb')[0]
    }

    res['parameters'] = ParameterData(
        dict=dict(
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
        )
    )

    res['code'] = Code.get_from_string('vasp')
    res['calculation_kwargs'] = dict(
        options=dict(
            resources={'num_machines': 2,
                       'num_mpiprocs_per_machine': 18},
            queue_name=get_queue_name_from_code('vasp'),
            withmpi=True,
            max_wallclock_seconds=1200
        )
    )
    return res


@pytest.fixture(params=['combined', 'split'])
def get_fp_tb_input(configure, get_insb_input, sample, request):  # pylint: disable=too-many-locals,unused-argument,redefined-outer-name,too-many-locals,too-many-statements
    """
    Returns the input for DFT-based tight-binding optimization workflows.
    """
    from aiida.orm import DataFactory
    from aiida.orm.data.base import List, Bool
    from aiida.orm.data.parameter import ParameterData
    from aiida.orm.code import Code
    from aiida_tools.workchain_inputs import get_fullname
    from aiida_tbextraction.fp_run import VaspFirstPrinciplesRun
    from aiida_tbextraction.fp_run import SplitFirstPrinciplesRun
    from aiida_tbextraction.fp_run.reference_bands import VaspReferenceBands
    from aiida_tbextraction.fp_run.wannier_input import VaspWannierInput
    from aiida_tbextraction.model_evaluation import BandDifferenceModelEvaluation

    inputs = dict()

    vasp_inputs = get_insb_input

    vasp_subwf_inputs = {
        'code': vasp_inputs.pop('code'),
        'parameters': vasp_inputs.pop('parameters'),
        'calculation_kwargs': vasp_inputs.pop('calculation_kwargs'),
    }
    if request.param == 'split':
        inputs['fp_run_workflow'] = SplitFirstPrinciplesRun
        inputs['fp_run'] = dict()
        inputs['fp_run']['reference_bands_workflow'
                         ] = get_fullname(VaspReferenceBands)
        inputs['fp_run']['reference_bands'] = dict(
            merge_kpoints=Bool(True), **vasp_subwf_inputs
        )
        inputs['fp_run']['wannier_input_workflow'
                         ] = get_fullname(VaspWannierInput)
        inputs['fp_run']['wannier_input'] = vasp_subwf_inputs

    else:
        assert request.param == 'combined'
        inputs['fp_run_workflow'] = VaspFirstPrinciplesRun
        inputs['fp_run'] = vasp_subwf_inputs
        inputs['fp_run']['scf'] = {
            'parameters': ParameterData(dict=dict(isym=2))
        },
        inputs['fp_run']['bands'] = {'merge_kpoints': Bool(True)},

    inputs.update(vasp_inputs)

    kpoints = DataFactory('array.kpoints')()
    kpoints.set_kpoints_path([('G', (0, 0, 0), 'M', (0.5, 0.5, 0.5))])
    inputs['kpoints'] = kpoints
    kpoints_mesh = DataFactory('array.kpoints')()
    kpoints_mesh.set_kpoints_mesh([2, 2, 2])
    inputs['kpoints_mesh'] = kpoints_mesh

    inputs['wannier_code'] = Code.get_from_string('wannier90')
    inputs['tbmodels_code'] = Code.get_from_string('tbmodels')

    inputs['model_evaluation_workflow'] = BandDifferenceModelEvaluation
    inputs['model_evaluation'] = {
        'bands_inspect_code': Code.get_from_string('bands_inspect')
    }

    initial_window = List()
    initial_window.extend([-4.5, -4, 6.5, 16])
    inputs['initial_window'] = initial_window

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
    inputs['wannier_calculation_kwargs'] = dict(
        options={
            'resources': {
                'num_machines': 1,
                'tot_num_mpiprocs': 1
            },
            'withmpi': False
        }
    )
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
