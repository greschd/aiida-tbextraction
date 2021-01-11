# # -*- coding: utf-8 -*-

# # © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# # Author: Dominik Gresch <greschd@gmx.ch>
# """
# Defines a workflow for running the first-principles calculations using VASP.
# """

# import copy
# from collections import ChainMap

# from fsc.export import export

# from aiida import orm
# from aiida.engine import ToContext

# from aiida_tools import check_workchain_step

# from aiida_vasp.calcs.vasp import VaspCalculation

# from .._calcfunctions import merge_nested_dict
# from .wannier_input import VaspWannierInput
# from .reference_bands import VaspReferenceBands
# from ._base import FirstPrinciplesRunBase

# @export
# class VaspFirstPrinciplesRun(FirstPrinciplesRunBase):
#     """
#     Workflow for calculating the inputs needed for tight-binding calculation and evaluation with VASP. The workflow first performs an SCF step, and then passes the WAVECAR file to the bandstructure and Wannier90 input calculations.
#     """
#     @classmethod
#     def define(cls, spec):
#         super(VaspFirstPrinciplesRun, cls).define(spec)

#         # Top-level parameters
#         spec.input('code', valid_type=orm.Code, help='Code that runs VASP.')
#         spec.input(
#             'parameters',
#             valid_type=orm.Dict,
#             help=
#             'Parameters passed to all VASP calculations, unless explicitly overwritten.'
#         )
#         spec.input_namespace(
#             'calculation_kwargs',
#             required=False,
#             dynamic=True,
#             help=
#             'Keyword arguments passed to all VASP calculations, unless explicitly overwritten.'
#         )

#         # Optional parameters to override for specific calculations.
#         # TODO: Use expose for the sub-workflows.
#         for sub_calc in ['scf', 'bands', 'to_wannier']:
#             spec.input_namespace(
#                 sub_calc,
#                 required=False,
#                 dynamic=True,
#                 help="Inputs passed to the '{}' sub-workflow / calculation".
#                 format(sub_calc)
#             )

#         spec.input(
#             'bands.merge_kpoints',
#             valid_type=orm.Bool,
#             default=lambda: orm.Bool(False),
#             help=
#             'Determines whether the k-point mesh needs to be added for the bandstructure calculation. This is needed for hybrid functional calculations.'
#         )

#         spec.expose_outputs(VaspReferenceBands)
#         spec.expose_outputs(VaspWannierInput)

#         spec.outline(cls.run_scf, cls.run_bands_and_wannier, cls.finalize)

#     def _collect_common_inputs(
#         self, namespace, expand_kwargs=False, force_parameters=None
#     ):
#         """
#         Join the top-level inputs and inputs set in a specific namespace.
#         """
#         ns_inputs = self.inputs.get(namespace, {})
#         ns_parameters = ns_inputs.get('parameters')
#         if ns_parameters is None:
#             parameters = self.inputs.parameters
#         else:
#             parameters = merge_nested_dict(
#                 dict_primary=ns_parameters,
#                 dict_secondary=self.inputs.parameters
#             )
#             if force_parameters:
#                 parameters = merge_nested_dict(
#                     dict_primary=orm.Dict(dict=force_parameters).store(),
#                     dict_secondary=parameters
#                 )
#         calculation_kwargs = copy.deepcopy(
#             dict(
#                 ChainMap(
#                     ns_inputs.get('calculation_kwargs', {}),
#                     self.inputs.calculation_kwargs
#                 )
#             )
#         )
#         res = dict(
#             code=self.inputs.code,
#             structure=self.inputs.structure,
#             parameters=parameters,
#         )
#         if expand_kwargs:
#             res.update(calculation_kwargs)
#         else:
#             res['calculation_kwargs'] = calculation_kwargs
#         return res

#     @check_workchain_step
#     def run_scf(self):
#         """
#         Run the SCF calculation step.
#         """
#         self.report('Launching SCF calculation.')

#         return ToContext(
#             scf=self.submit(
#                 VaspCalculation,
#                 potential={(kind, ): pot
#                            for kind, pot in self.inputs.potentials.items()},
#                 kpoints=self.inputs.kpoints_mesh,
#                 settings=orm.Dict(
#                     dict={
#                         'ADDITIONAL_RETRIEVE_LIST': ['WAVECAR'],
#                         'parser_settings': {
#                             'add_wavecar': True
#                         }
#                     }
#                 ),
#                 **self._collect_common_inputs(
#                     'scf',
#                     force_parameters={'lwave': True},
#                     expand_kwargs=True
#                 )
#             )
#         )

#     def _collect_process_inputs(self, namespace):
#         """
#         Helper to collect the inputs for the reference bands and wannier input workflows.
#         """
#         scf_wavefun = self.ctx.scf.outputs.output_wavecar
#         res = self._collect_common_inputs(namespace)
#         res['potentials'] = self.inputs.potentials
#         res['calculation_kwargs']['wavefunctions'] = scf_wavefun
#         self.report('Collected inputs: {}'.format(res))
#         return res

#     @check_workchain_step
#     def run_bands_and_wannier(self):
#         """
#         Run the reference bands and wannier input workflows.
#         """

#         self.report('Launching bands workchain.')
#         bands_run = self.submit(
#             VaspReferenceBands,
#             kpoints=self.inputs.kpoints,
#             kpoints_mesh=self.inputs.kpoints_mesh,
#             merge_kpoints=self.inputs.bands['merge_kpoints'],
#             **self._collect_process_inputs('bands')
#         )
#         self.report('Launching to_wannier workchain.')
#         to_wannier_run = self.submit(
#             VaspWannierInput,
#             kpoints_mesh=self.inputs.kpoints_mesh,
#             wannier_parameters=self.inputs.get('wannier_parameters', None),
#             wannier_projections=self.inputs.get('wannier_projections', None),
#             **self._collect_process_inputs('to_wannier')
#         )
#         return ToContext(bands=bands_run, to_wannier=to_wannier_run)

#     @check_workchain_step
#     def finalize(self):
#         """
#         Add outputs of the bandstructure and wannier input calculations.
#         """
#         self.report('Checking that the bands calculation used WAVECAR.')
#         self.check_read_wavecar(self.ctx.bands)

#         self.report(
#             'Checking that the wannier input calculation used WAVECAR.'
#         )
#         self.check_read_wavecar(self.ctx.to_wannier)

#         self.report('Retrieving outputs.')
#         self.out_many(self.exposed_outputs(self.ctx.bands, VaspReferenceBands))
#         self.out_many(
#             self.exposed_outputs(self.ctx.to_wannier, VaspWannierInput)
#         )

#     @staticmethod
#     def check_read_wavecar(sub_workflow):
#         """
#         Check that the calculation in the given sub-workflow uses the
#         wavefunctions input.
#         """
#         for label, node in sub_workflow.get_outputs(also_labels=True):
#             if label == 'CALL' and isinstance(node, VaspCalculation):
#                 retrieved_folder = node.get_retrieved_node()
#                 with open(
#                     retrieved_folder.get_abs_path('_scheduler-stdout.txt')
#                 ) as f:
#                     stdout = f.read()
#                     assert 'WAVECAR not read' not in stdout
#                     assert 'reading WAVECAR' in stdout
