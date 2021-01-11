# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>

# pylint: disable=unused-argument,redefined-outer-name
"""
Configuration file for pytest tests.
"""

import os
import pathlib

import pytest
import numpy as np

from ase.io.vasp import read_vasp
from aiida import orm

from aiida_tbextraction.model_evaluation import BandDifferenceModelEvaluation

pytest_plugins = [  # pylint: disable=invalid-name
    'aiida.manage.tests.pytest_fixtures', 'aiida_pytest',
    'aiida_testing.mock_code'
]


@pytest.fixture(scope='session', autouse=True)
def set_localhost_interval(configure):
    orm.Computer.get(label='localhost').set_minimum_job_poll_interval(0.)


def pytest_addoption(parser):  # pylint: disable=missing-function-docstring
    parser.addoption(
        '--skip-qe',
        action='store_true',
        help='Skip tests which require Quantum ESPRESSO.'
    )
    parser.addoption(
        '--skip-vasp',
        action='store_true',
        help='Skip tests which require VASP.'
    )


def pytest_configure(config):
    # register additional marker
    config.addinivalue_line("markers", "qe: mark tests which run with QE")
    config.addinivalue_line("markers", "vasp: mark tests which run with VASP")


def pytest_runtest_setup(item):  # pylint: disable=missing-function-docstring
    try:
        qe_marker = item.get_marker("qe")
        vasp_marker = item.get_marker("vasp")
    except AttributeError:
        qe_marker = item.get_closest_marker('qe')
        vasp_marker = item.get_closest_marker('vasp')
    if qe_marker is not None:
        if item.config.getoption("--skip-qe"):
            pytest.skip("Test needs Quantum ESPRESSO.")
    if vasp_marker is not None:
        if item.config.getoption("--skip-vasp"):
            pytest.skip("Test needs VASP.")


@pytest.fixture(scope='session')
def test_root_dir():
    return pathlib.Path(__file__).resolve().parent


@pytest.fixture(scope='session')
def mock_codes_data_dir(test_root_dir):  # pylint: disable=redefined-outer-name
    return test_root_dir / 'mock_codes_data'


@pytest.fixture(scope='session')
def test_data_dir(test_root_dir):  # pylint: disable=redefined-outer-name
    return test_root_dir / 'data'


@pytest.fixture
def code_wannier90(mock_code_factory, mock_codes_data_dir):  # pylint: disable=redefined-outer-name
    return mock_code_factory(
        label='wannier90',
        entry_point='wannier90.wannier90',
        data_dir_abspath=mock_codes_data_dir,
        ignore_files=(
            '_aiidasubmit.sh', 'aiida.amn', 'aiida.chk', 'aiida.mmn'
        )
    )


@pytest.fixture
def code_pw(mock_code_factory, mock_codes_data_dir):  # pylint: disable=redefined-outer-name
    return mock_code_factory(
        label="pw",
        entry_point="quantumespresso.pw",
        data_dir_abspath=mock_codes_data_dir,
        ignore_files=("_aiidasubmit.sh", 'pseudo')
    )


@pytest.fixture
def code_pw2wannier90(mock_code_factory, mock_codes_data_dir):  # pylint: disable=redefined-outer-name
    return mock_code_factory(
        label="pw2wannier90",
        entry_point="quantumespresso.pw2wannier90",
        data_dir_abspath=mock_codes_data_dir,
        ignore_files=("_aiidasubmit.sh", )
    )


@pytest.fixture
def code_vasp(mock_code_factory, mock_codes_data_dir):  # pylint: disable=redefined-outer-name
    return mock_code_factory(
        label='vasp',
        entry_point='vasp.vasp',
        data_dir_abspath=mock_codes_data_dir,
        ignore_files=('_aiidasubmit.sh')
    )


@pytest.fixture(scope='session')
def generate_upf_data(test_data_dir):  # pylint: disable=redefined-outer-name
    """Return a `UpfData` instance for the given element a file for which should exist in `./data/pseudos`."""

    pseudo_dir = test_data_dir / 'pseudos'

    def _generate_upf_data(element):
        """Return `UpfData` node."""

        return orm.UpfData(file=os.path.abspath(pseudo_dir / f'{element}.upf'))

    return _generate_upf_data


@pytest.fixture
def insb_pseudos_qe(configure, generate_upf_data):  # pylint: disable=unused-argument,redefined-outer-name
    """Fixture providing the pseudos input for QE InSb calculations."""
    return {'In': generate_upf_data('In'), 'Sb': generate_upf_data('Sb')}


@pytest.fixture
def insb_structure(configure, test_data_dir):  # pylint: disable=unused-argument,redefined-outer-name
    """Fixture providing the structure input for InSb calculations."""
    structure = orm.StructureData()
    with open(test_data_dir / 'InSb' / 'POSCAR') as poscar_file:
        structure.set_ase(read_vasp(poscar_file))
    return structure.store()


@pytest.fixture
def insb_common_qe_parameters(configure):  # pylint: disable=unused-argument
    """Fixture providing the common 'parameters' input for InSb QE calculations."""
    return orm.Dict(
        dict=dict(
            CONTROL=dict(etot_conv_thr=1e-3),
            SYSTEM=dict(noncolin=True, lspinorb=True, nbnd=36, ecutwfc=30),
        )
    ).store()


@pytest.fixture
def get_metadata_singlecore():
    """Callable fixture, returns the 'metadata' content for a single-core calulation."""
    def _get_metadata():
        return {
            "options": {
                "resources": {
                    'num_machines': 1,
                    'num_mpiprocs_per_machine': 1
                },
                "withmpi": False,
                "max_wallclock_seconds": 1200
            }
        }

    return _get_metadata


@pytest.fixture
def get_repeated_pw_input(
    configure, code_pw, insb_structure, insb_pseudos_qe,
    insb_common_qe_parameters, get_metadata_singlecore
):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Construct the part of the PW input that is not passed down from
    the top-level workchain.
    """
    def _get_repeated_pw_input():
        options = get_metadata_singlecore()
        return {
            'pw': {
                'pseudos': insb_pseudos_qe,
                'parameters': insb_common_qe_parameters,
                'metadata': options,
                'code': code_pw
            }
        }

    return _get_repeated_pw_input


@pytest.fixture
def get_top_level_insb_inputs(configure, insb_structure):
    """
    Constructs the part of the InSb inputs which are shared
    among different workflows and thus specified at the top-level.
    """
    def inner():
        kpoints_mesh = orm.KpointsData()
        kpoints_mesh.set_kpoints_mesh([2, 2, 2])

        kpoints = orm.KpointsData()
        kpoints.set_kpoints([[x, x, x] for x in np.linspace(0, 0.5, 6)],
                            labels=((0, 'G'), (5, 'M')))

        return {
            'structure':
            insb_structure,
            'kpoints_mesh':
            kpoints_mesh,
            'kpoints':
            kpoints,
            'wannier_parameters':
            orm.Dict(
                dict=dict(
                    num_wann=14,
                    num_bands=36,
                    spinors=True,
                    dis_num_iter=1000,
                    num_iter=0
                )
            ),
            'wannier_projections':
            orm.List(list=['In : s; px; py; pz', 'Sb : px; py; pz']),
        }

    return inner


# use very large batchsize to force one batch
_DEFAULT_PW2WANNIER_BANDS_BATCHSIZE = 10000


@pytest.fixture
def get_qe_specific_fp_run_inputs(
    configure, code_pw, code_wannier90, code_pw2wannier90,
    get_repeated_pw_input, get_metadata_singlecore
):
    """
    Creates the InSb inputs for the QE fp_run workflow. For the
    higher-level workflows (fp_tb, optimize_*), these are passed
    in the 'fp_run' namespace.
    """
    def inner(pw2wannier_bands_batchsize=_DEFAULT_PW2WANNIER_BANDS_BATCHSIZE):
        return {
            'scf': get_repeated_pw_input(),
            'bands': {
                'bands': get_repeated_pw_input()
            },
            'to_wannier': {
                'nscf': get_repeated_pw_input(),
                'wannier': {
                    'code': code_wannier90,
                    'metadata': get_metadata_singlecore()
                },
                'pw2wannier': {
                    'bands_batchsize': orm.Int(pw2wannier_bands_batchsize),
                    'pw2wannier': {
                        'code': code_pw2wannier90,
                        'metadata': get_metadata_singlecore()
                    },
                }
            }
        }

    return inner


# @pytest.fixture
# def get_vasp_specific_fp_run_inputs(code_vasp):
#     """
#     Creates the InSb inputs for the VASP fp_run workflow.
#     """
#     from aiida_vasp.data.potcar import PotcarData

#     def inner():
#         return {
#             'potentials': {
#                 'In': PotcarData.find_one(family='pbe', symbol='In_d'),
#                 'Sb': PotcarData.find_one(family='pbe', symbol='Sb')
#             },
#             'parameters':
#             orm.Dict(
#                 dict=dict(
#                     ediff=1e-3,
#                     lsorbit=True,
#                     isym=0,
#                     ismear=0,
#                     sigma=0.05,
#                     gga='PE',
#                     encut=380,
#                     magmom='600*0.0',
#                     nbands=36,
#                     kpar=4,
#                     nelmin=0,
#                     lwave=False,
#                     aexx=0.25,
#                     lhfcalc=True,
#                     hfscreen=0.23,
#                     algo='N',
#                     time=0.4,
#                     precfock='normal',
#                 )
#             ),
#             'code':
#             code_vasp,
#             'calculation_kwargs':
#             dict(
#                 options=dict(
#                     resources={
#                         'num_machines': 2,
#                         'num_mpiprocs_per_machine': 18
#                     },
#                     withmpi=True,
#                     max_wallclock_seconds=1200
#                 )
#             ),
#             'scf': {
#                 'parameters': orm.Dict(dict=dict(isym=2))
#             }
#         }

#     return inner


@pytest.fixture
def get_fp_run_inputs(
    configure, get_top_level_insb_inputs, get_qe_specific_fp_run_inputs,
    test_data_dir
):
    """
    Create input for the QE InSb sample.
    """
    def inner(pw2wannier_bands_batchsize=_DEFAULT_PW2WANNIER_BANDS_BATCHSIZE):

        return dict(
            **get_top_level_insb_inputs(),
            **get_qe_specific_fp_run_inputs(
                pw2wannier_bands_batchsize=pw2wannier_bands_batchsize
            )
        )

    return inner


@pytest.fixture
def get_vasp_fp_run_inputs(
    configure, get_top_level_insb_inputs, get_vasp_specific_fp_run_inputs,
    test_data_dir
):
    """
    Create input for the VASP InSb sample.
    """
    def inner():
        return dict(
            **get_top_level_insb_inputs(), **get_vasp_specific_fp_run_inputs()
        )

    return inner


@pytest.fixture
def get_fp_tb_inputs(
    configure, get_top_level_insb_inputs, get_qe_specific_fp_run_inputs,
    get_metadata_singlecore, test_data_dir, code_wannier90
):
    """
    Returns the input for DFT-based tight-binding workflows (without optimization).
    """
    def inner():
        from aiida_tbextraction.fp_run import QuantumEspressoFirstPrinciplesRun  # pylint: disable=import-outside-toplevel

        inputs = get_top_level_insb_inputs()

        inputs['fp_run_workflow'] = QuantumEspressoFirstPrinciplesRun
        inputs['fp_run'] = get_qe_specific_fp_run_inputs()

        inputs['code_tbmodels'] = orm.Code.get_from_string('tbmodels')

        inputs['model_evaluation_workflow'] = BandDifferenceModelEvaluation
        inputs['model_evaluation'] = {
            'code_bands_inspect': orm.Code.get_from_string('bands_inspect')
        }

        inputs['wannier_parameters'] = orm.Dict(
            dict=dict(
                num_wann=14,
                num_bands=36,
                dis_num_iter=1000,
                num_iter=0,
                spinors=True,
            )
        )
        inputs['wannier_projections'] = orm.List(
            list=['In : s; px; py; pz', 'Sb : px; py; pz']
        )
        inputs['wannier'] = dict(
            code=code_wannier90, metadata=get_metadata_singlecore()
        )

        inputs['parse'] = {
            'calc': {
                'distance_ratio_threshold': orm.Float(1.5)
            }
        }

        inputs['symmetries'] = orm.SinglefileData(
            file=str((test_data_dir / 'symmetries.hdf5').resolve())
        )
        inputs['slice_reference_bands'] = orm.List(list=list(range(12, 26)))

        inputs['slice_tb_model'] = orm.List(
            list=[0, 2, 3, 1, 5, 6, 4, 7, 9, 10, 8, 12, 13, 11]
        )
        return inputs

    return inner


@pytest.fixture
def get_optimize_fp_tb_input(get_fp_tb_inputs):  # pylint: disable=redefined-outer-name
    """
    Get the input for the first-principles tight-binding workflow with optimization.
    """
    def inner():
        inputs = get_fp_tb_inputs()
        inputs['initial_window'] = orm.List(list=[-4.5, -4, 6.5, 16])
        inputs['window_tol'] = orm.Float(1.5)

        return inputs

    return inner
