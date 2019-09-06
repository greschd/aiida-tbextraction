#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>

import os

from ase.io.vasp import read_vasp

from aiida.plugins import DataFactory
from aiida.orm import Code
from aiida.orm.nodes.data.list import List
from aiida.orm.nodes.data.float import Float
from aiida.orm import Dict
from aiida.engine.launch import submit

from aiida_vasp.data.potcar import PotcarData

from aiida_tbextraction.fp_run import VaspFirstPrinciplesRun
from aiida_tbextraction.model_evaluation import BandDifferenceModelEvaluation
from aiida_tbextraction.optimize_fp_tb import OptimizeFirstPrinciplesTightBinding


def create_builder():
    builder = OptimizeFirstPrinciplesTightBinding.get_builder()

    # Add the input structure
    builder.structure = DataFactory('structure')()
    builder.structure.set_ase(read_vasp('inputs/POSCAR'))

    # Load the potential files (if needed) and set them as input
    builder.potentials = dict(
        In=PotcarData.find_one(symbol='In_d'),
        Sb=PotcarData.find_one(symbol='Sb')
    )

    # Specify that VaspFirstPrinciplesRun should be used to run the first-principles calculations
    builder.fp_run_workflow = VaspFirstPrinciplesRun

    # Set the inputs for the VaspFirstPrinciplesRun workflow
    builder.fp_run = dict(
        code=Code.get_from_string('vasp'),
        parameters=Dict(dict=dict( # Parameters common to all VASP calculations
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
                queue_name='dphys_compute',
                withmpi=True,
                max_wallclock_seconds=60 * 60
            )
        )
    )

    # Setting the parameters specific for the bands calculation
    builder.fp_run['bands'] = dict(
        parameters=Dict(dict=dict(lwave=False, isym=0))
    )
    # Setting the parameters specific for the wannier input calculation
    builder.fp_run['to_wannier'] = dict(
        parameters=Dict(dict=dict(lwave=False, isym=0))
    )

    # Setting the k-points for the reference bandstructure
    builder.kpoints = DataFactory('array.kpoints')()
    builder.kpoints.set_kpoints_path([
        ('Z', (0.5, 0.5, 0), 'G', (0., 0., 0.), 21),
        ('G', (0., 0., 0.), 'X', (0., 0.5, 0.5), 21),
        ('X', (0., 0.5, 0.5), 'L', (0.5, 0.5, 0.5), 21),
        ('L', (0.5, 0.5, 0.5), 'G', (0., 0., 0.), 21),
        ('G', (0., 0., 0.), 'K', (0.375, 0.375, 0.75), 21),
    ])

    # Setting the k-points mesh used to run the SCF and Wannier calculations
    builder.kpoints_mesh = DataFactory('array.kpoints')()
    builder.kpoints_mesh.set_kpoints_mesh([6, 6, 6])

    # Setting the codes
    builder.wannier_code = Code.get_from_string('wannier90')
    builder.tbmodels_code = Code.get_from_string('tbmodels')

    # Setting the workflow to evaluate the tight-binding models
    builder.model_evaluation_workflow = BandDifferenceModelEvaluation

    # Setting the additional inputs for the model evaluation workflow
    builder.model_evaluation = dict(
        bands_inspect_code=Code.get_from_string('bands_inspect')
    )

    # Set the initial energy window value
    builder.initial_window = List(list=[-4.5, -4, 6.5, 16])

    # Tolerance for the energy window.
    builder.window_tol = Float(1.5)
    # Tolerance for the 'cost_value'.
    builder.cost_tol = Float(0.3)
    # The tolerances are set higher than might be appropriate for a 'production'
    # run to make the example run more quickly.

    # Setting the parameters for Wannier90
    builder.wannier_parameters = Dict(
        dict=dict(
            num_wann=14,
            num_bands=36,
            dis_num_iter=100,
            num_iter=0,
            spinors=True,
        )
    )
    # Choose the Wannier90 trial orbitals
    builder.wannier_projections = List(
        list=['In : s; px; py; pz', 'Sb : px; py; pz']
    )
    # Set the resource requirements for the Wannier90 run
    builder.wannier_calculation_kwargs = dict(
        options=dict(
            resources={
                'num_machines': 1,
                'tot_num_mpiprocs': 1
            },
            withmpi=False,
            queue_name='dphys_compute',
        )
    )
    # Set the symmetry file
    builder.symmetries = DataFactory('singlefile')(
        file=os.path.abspath('inputs/symmetries.hdf5')
    )

    # Pick the relevant bands from the reference calculation
    builder.slice_reference_bands = List(list=list(range(12, 26)))

    # Re-order the tight-binding basis to match the symmetry basis
    builder.slice_tb_model = List(
        list=[0, 2, 3, 1, 5, 6, 4, 7, 9, 10, 8, 12, 13, 11]
    )

    return builder


if __name__ == '__main__':
    builder = create_builder()
    node = submit(builder)
    print('Submitted workflow with pk={}'.format(node.pk))
