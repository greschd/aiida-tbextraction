#!/usr/bin/env runaiida

import os

from ase.io.vasp import read_vasp

from aiida.orm import DataFactory
from aiida.orm.code import Code
from aiida.orm.data.list import List
from aiida.orm.data.parameter import ParameterData
from aiida.work.launch import submit

from aiida_vasp.data.paw import PawData

from aiida_tbextraction.fp_run import VaspFirstPrinciplesRun
from aiida_tbextraction.model_evaluation import BandDifferenceModelEvaluation
from aiida_tbextraction.optimize_fp_tb import OptimizeFirstPrinciplesTightBinding

POTENTIAL_DIR = 'inputs/potentials'


def load_potential(name, md5):
    """
    Helper function that gets the potentials or loads them from a folder.
    """
    try:
        return PawData.load_paw(symbol=name, md5=md5)[0]
    except ValueError:
        try:
            pot_dir = os.path.join(POTENTIAL_DIR, name)
            potential = PawData.from_folder(pot_dir)
            potential.store()
            return potential
        except ValueError:
            raise ValueError(
                "Cannot load potential, check that the potential directory '{}' exists.".
                format(pot_dir)
            )


def create_builder():
    builder = OptimizeFirstPrinciplesTightBinding.get_builder()

    # Add the input structure
    builder.structure = DataFactory('structure')()
    builder.structure.set_ase(read_vasp('inputs/POSCAR'))

    # Load the potential files (if needed) and set them as input
    builder.potentials = dict(
        In=load_potential('In_d', md5='56da6eefc0cb43d3911b1d06307691ae'),
        Sb=load_potential('Sb', md5='80003a45f175e1686bbf2743defcf331')
    )

    # Specify that VaspFirstPrinciplesRun should be used to run the first-principles calculations
    builder.fp_run_workflow = VaspFirstPrinciplesRun

    # Set the inputs for the VaspFirstPrinciplesRun workflow
    builder.fp_run = dict(
        code=Code.get_from_string('vasp'),
        parameters=dict( # Parameters common to all VASP calculations
            prec='N',
            lsorbit=True,
            ismear=0,
            sigma=0.05,
            gga='PE',
            magmom='600*0.0',
            nbands=36,
            kpar=4,
        ),
        calculation_kwargs=dict(
            options=dict( # Settings for the resource requirements
                resources={'num_machines': 2, 'num_mpiprocs_per_machine': 18},
                queue_name='dphys_compute',
                withmpi=True,
                max_wallclock_seconds=60
            )
        )
    )

    # Setting the parameters specific for the bands calculation
    builder.fp_run['bands'] = dict(
        parameters=ParameterData(dict=dict(lwave=False, isym=0.))
    )
    # Setting the parameters specific for the wannier input calculation
    builder.fp_run['to_wannier'] = dict(
        parameters=ParameterData(dict=dict(lwave=False, isym=0.))
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

    # Setting the parameters for Wannier90
    builder.wannier_parameters = ParameterData(
        dict=dict(
            num_wann=14,
            num_bands=36,
            dis_num_iter=1000,
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
            resources={'num_machines': 1,
                       'tot_num_mpiprocs': 1},
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
