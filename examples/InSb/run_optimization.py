#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>

import os

import numpy as np
from ase.io.vasp import read_vasp

from aiida import orm
from aiida.engine.launch import submit

from aiida_tbextraction.fp_run import QuantumEspressoFirstPrinciplesRun
from aiida_tbextraction.model_evaluation import BandDifferenceModelEvaluation
from aiida_tbextraction.optimize_fp_tb import OptimizeFirstPrinciplesTightBinding


def create_builder():
    builder = OptimizeFirstPrinciplesTightBinding.get_builder()

    # Add the input structure
    builder.structure = orm.StructureData()
    builder.structure.set_ase(read_vasp('inputs/POSCAR'))

    # Specify that QuantumEspressoFirstPrinciplesRun should be used to run the first-principles calculations
    builder.fp_run_workflow = QuantumEspressoFirstPrinciplesRun

    # Set the inputs for the QuantumEspressoFirstPrinciplesRun workflow
    # common_qe_parameters =

    builder.fp_run = dict(
        code=orm.Code.get_from_string('pw-6.4.1'),
        parameters=orm.Dict(dict=dict( # Parameters common to all VASP calculations
            prec='N',
            lsorbit=True,
            ismear=0,
            sigma=0.05,
            gga='PE',
            magmom='600*0.0',
            nbands=36,
            kpar=4,
        )),
        calculation_kwargs=dict(
            options=dict( # Settings for the resource requirements
                resources={'num_machines': 2, 'num_mpiprocs_per_machine': 18},
                withmpi=True,
                max_wallclock_seconds=60 * 60
            )
        )
    )

    # Setting the parameters specific for the bands calculation
    builder.fp_run['bands'] = dict(
        parameters=orm.Dict(dict=dict(lwave=False, isym=0))
    )
    # Setting the parameters specific for the wannier input calculation
    builder.fp_run['to_wannier'] = dict(
        parameters=orm.Dict(dict=dict(lwave=False, isym=0))
    )

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

    builder.wannier.code = orm.Code.get_from_string('wannier90')
    builder.code_tbmodels = orm.Code.get_from_string('tbmodels')

    # Setting the workflow to evaluate the tight-binding models
    builder.model_evaluation_workflow = BandDifferenceModelEvaluation

    # Setting the additional inputs for the model evaluation workflow
    builder.model_evaluation = dict(
        code_bands_inspect=orm.Code.get_from_string('bands_inspect')
    )

    # Set the initial energy window value
    builder.initial_window = orm.List(list=[-4.5, -4, 6.5, 16])

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
        )
    )
    # Choose the Wannier90 trial orbitals
    builder.wannier_projections = orm.List(
        list=['In : s; px; py; pz', 'Sb : px; py; pz']
    )
    # Set the resource requirements for the Wannier90 run
    builder.wannier.metadata = dict(
        options=dict(
            resources={
                'num_machines': 1,
                'tot_num_mpiprocs': 1
            },
            withmpi=False,
        )
    )
    # Set the symmetry file
    builder.symmetries = orm.SinglefileData(
        file=os.path.abspath('inputs/symmetries.hdf5')
    )

    # Pick the relevant bands from the reference calculation
    builder.slice_reference_bands = orm.List(list=list(range(12, 26)))

    # Re-order the tight-binding basis to match the symmetry basis
    builder.slice_tb_model = orm.List(
        list=[0, 2, 3, 1, 5, 6, 4, 7, 9, 10, 8, 12, 13, 11]
    )

    return builder


if __name__ == '__main__':
    builder = create_builder()
    node = submit(builder)
    print('Submitted workflow with pk={}'.format(node.pk))
