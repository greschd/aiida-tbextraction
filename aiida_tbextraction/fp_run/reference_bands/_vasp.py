# # -*- coding: utf-8 -*-

# # © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# # Author: Dominik Gresch <greschd@gmx.ch>
# """
# Defines a workflow that calculates the reference bandstructure using VASP.
# """

# from fsc.export import export

# from aiida import orm
# from aiida.engine import ToContext

# from aiida_tools import check_workchain_step
# from aiida_vasp.calcs.vasp import VaspCalculation

# from ._base import ReferenceBandsBase
# from .._helpers._calcfunctions import (
#     flatten_bands, crop_bands, merge_kpoints
# )

# @export
# class VaspReferenceBands(ReferenceBandsBase):
#     """
#     The WorkChain to calculate reference bands with VASP.
#     """
#     @classmethod
#     def define(cls, spec):
#         super(VaspReferenceBands, cls).define(spec)
#         spec.input('code', valid_type=orm.Code, help='Code that runs VASP.')
#         spec.input(
#             'parameters',
#             valid_type=orm.Dict,
#             help='Parameters of the VASP calculation.'
#         )
#         spec.input_namespace(
#             'calculation_kwargs',
#             required=False,
#             dynamic=True,
#             help='Additional keyword arguments passed to the VASP calculation.'
#         )
#         spec.input(
#             'merge_kpoints',
#             valid_type=orm.Bool,
#             default=lambda: orm.Bool(False),
#             help=
#             'Defines whether the k-point mesh is added to the list of k-points for the reference band calculation. This is needed for hybrid functional calculations.'
#         )

#         spec.outline(cls.run_calc, cls.get_bands)

#     @check_workchain_step
#     def run_calc(self):
#         """
#         Run the VASP calculation.
#         """
#         if self.inputs.merge_kpoints:
#             self.report("Merging kpoints and kpoints_mesh.")
#             mesh_kpoints = self.inputs.kpoints_mesh
#             band_kpoints = self.inputs.kpoints
#             kpoints = merge_kpoints(
#                 mesh_kpoints=mesh_kpoints, band_kpoints=band_kpoints
#             )
#         else:
#             kpoints = self.inputs.kpoints

#         self.report("Submitting VASP calculation.")
#         return ToContext(
#             vasp_calc=self.submit(
#                 VaspCalculation,
#                 structure=self.inputs.structure,
#                 potential=self.inputs.potentials,
#                 kpoints=kpoints,
#                 parameters=self.inputs.parameters,
#                 code=self.inputs.code,
#                 settings=orm.Dict(
#                     dict=dict(parser_settings=dict(add_bands=True))
#                 ),
#                 **self.inputs.get('calculation_kwargs', {})
#             )
#         )

#     @check_workchain_step
#     def get_bands(self):
#         """
#         Get the bands from the VASP calculation and crop the 'mesh' k-points if necessary.
#         """
#         bands = self.ctx.vasp_calc.outputs.output_bands
#         self.report("Flattening the output bands.")
#         res_bands = flatten_bands(bands=bands)[1]['bands']
#         if self.inputs.merge_kpoints:
#             self.report("Cropping mesh eigenvalues from bands.")
#             res_bands = crop_bands(
#                 bands=res_bands, kpoints=self.inputs.kpoints
#             )
#         self.out('bands', res_bands)
