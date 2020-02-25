#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>

import os
import pathlib

import numpy as np
from ase.io.vasp import read_vasp

from aiida import orm
from aiida.engine.launch import submit

from aiida_tbextraction.fp_run import QuantumEspressoFirstPrinciplesRun
from aiida_tbextraction.model_evaluation import BandDifferenceModelEvaluation
from aiida_tbextraction.optimize_fp_tb import OptimizeFirstPrinciplesTightBinding

# Define constants for Code and metadata
# Modify these to match your configured codes, and adapt the metadata
# as needed.
METADATA_PW = {
    'options': {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 4
        },
        'withmpi': True,
        'max_wallclock_seconds': 1200
    }
}
CODE_PW = orm.Code.get_from_string('pw')
METADATA_WANNIER = {
    'options': {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'withmpi': False,
        'max_wallclock_seconds': 1200
    }
}
CODE_WANNIER = orm.Code.get_from_string('wannier90')
METADATA_PW2WANNIER = METADATA_WANNIER
CODE_PW2WANNIER = orm.Code.get_from_string('pw2wannier90')


def create_builder():
    builder = OptimizeFirstPrinciplesTightBinding.get_builder()

    # Add the input structure
    builder.structure = orm.StructureData()
    builder.structure.set_ase(read_vasp('inputs/POSCAR'))

    # Specify that QuantumEspressoFirstPrinciplesRun should be used to run the first-principles calculations
    builder.fp_run_workflow = QuantumEspressoFirstPrinciplesRun

    # Set the inputs for the QuantumEspressoFirstPrinciplesRun workflow
    common_qe_parameters = orm.Dict(
        dict=dict(
            CONTROL=dict(etot_conv_thr=1e-3),
            SYSTEM=dict(noncolin=True, lspinorb=True, nbnd=36, ecutwfc=30),
        )
    )

    pseudo_dir = pathlib.Path(__file__
                              ).parent.absolute() / 'inputs' / 'pseudos'
    pseudos = {
        'In':
        orm.UpfData(
            file=str(pseudo_dir / 'In.rel-pbe-dn-kjpaw_psl.1.0.0.UPF')
        ),
        'Sb':
        orm.UpfData(file=str(pseudo_dir / 'Sb.rel-pbe-n-kjpaw_psl.1.0.0.UPF'))
    }

    # We use the same general Quantum ESPRESSO parameters for the
    # scf, nscf, and bands calculations. The calculation type and
    # k-points will be set by the workflow.
    repeated_pw_inputs = {
        'pseudos': pseudos,
        'parameters': common_qe_parameters,
        'metadata': METADATA_PW,
        'code': CODE_PW
    }

    builder.fp_run = {
        'scf': repeated_pw_inputs,
        'bands': {
            'pw': repeated_pw_inputs
        },
        'to_wannier': {
            'nscf': repeated_pw_inputs,
            'pw2wannier': {
                'code': CODE_PW2WANNIER,
                'metadata': METADATA_PW2WANNIER
            },
            'wannier': {
                'code': CODE_WANNIER,
                'metadata': METADATA_WANNIER
            }
        }
    }

    # Setting the k-points for the reference bandstructure
    kpoints_list = []
    kvals = np.linspace(0, 0.5, 20, endpoint=False)
    kvals_rev = np.linspace(0.5, 0, 20, endpoint=False)
    for k in kvals_rev:
        kpoints_list.append((k, k, 0))  # Z to Gamma
    for k in kvals:
        kpoints_list.append((0, k, k))  # Gamma to X
    for k in kvals:
        kpoints_list.append((k, 0.5, 0.5))  # X to L
    for k in kvals_rev:
        kpoints_list.append((k, k, k))  # L to Gamma
    for k in np.linspace(0, 0.375, 21, endpoint=True):
        kpoints_list.append((k, k, 2 * k))  # Gamma to K
    builder.kpoints = orm.KpointsData()
    builder.kpoints.set_kpoints(
        kpoints_list,
        labels=[(i * 20, label)
                for i, label in enumerate(['Z', 'G', 'X', 'L', 'G', 'K'])]
    )

    # Setting the k-points mesh used to run the SCF and Wannier calculations
    builder.kpoints_mesh = orm.KpointsData()
    builder.kpoints_mesh.set_kpoints_mesh([6, 6, 6])

    builder.wannier.code = CODE_WANNIER
    builder.code_tbmodels = orm.Code.get_from_string('tbmodels')

    # Setting the workflow to evaluate the tight-binding models
    builder.model_evaluation_workflow = BandDifferenceModelEvaluation

    # Setting the additional inputs for the model evaluation workflow
    builder.model_evaluation = dict(
        code_bands_inspect=orm.Code.get_from_string('bands_inspect')
    )

    # Set the initial energy window value
    builder.initial_window = orm.List(list=[-1, 3, 10, 18])

    # Tolerance for the energy window.
    builder.window_tol = orm.Float(1.5)
    # Tolerance for the 'cost_value'.
    builder.cost_tol = orm.Float(0.3)
    # The tolerances are set higher than might be appropriate for a 'production'
    # run to make the example run more quickly.

    # Setting the parameters for Wannier90
    builder.wannier_parameters = orm.Dict(
        dict=dict(
            num_wann=14,
            num_bands=36,
            dis_num_iter=100,
            num_iter=0,
            spinors=True,
            # exclude_bands=range(1, )
        )
    )
    # Choose the Wannier90 trial orbitals
    builder.wannier_projections = orm.List(
        list=['In : s; pz; px; py', 'Sb : pz; px; py']
    )
    # Set the resource requirements for the Wannier90 run
    builder.wannier.metadata = METADATA_WANNIER

    # Set the symmetry file
    builder.symmetries = orm.SinglefileData(
        file=os.path.abspath('inputs/symmetries.hdf5')
    )

    # Pick the relevant bands from the reference calculation
    builder.slice_reference_bands = orm.List(list=list(range(12, 26)))

    return builder


if __name__ == '__main__':
    builder = create_builder()
    node = submit(builder)
    print('Submitted workflow with pk={}'.format(node.pk))
