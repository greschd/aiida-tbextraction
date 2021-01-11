# # -*- coding: utf-8 -*-

# # © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# # Author: Dominik Gresch <greschd@gmx.ch>
# """
# Defines a workflow that calculates the Wannier90 input files using VASP.
# """

# from fsc.export import export
# import numpy as np

# from aiida import orm
# from aiida.engine import ToContext

# from aiida_tools import check_workchain_step
# from aiida_vasp.calcs.vasp2w90 import Vasp2w90Calculation
# from aiida_vasp.parsers.file_parsers.win import WinParser

# from ._base import WannierInputBase
# from .._helpers._calcfunctions import reduce_num_bands

# @export
# class VaspWannierInput(WannierInputBase):
#     """
#     Calculates the Wannier90 input files using VASP.
#     """
#     @classmethod
#     def define(cls, spec):
#         super(VaspWannierInput, cls).define(spec)

#         spec.input('code', valid_type=orm.Code, help='Code that runs VASP.')
#         spec.input(
#             'parameters',
#             valid_type=orm.Dict,
#             help='Parameters for the Vasp2w90 calculation.'
#         )
#         spec.input_namespace(
#             'calculation_kwargs',
#             required=False,
#             dynamic=True,
#             help='Keyword arguments passed to the Vasp2w90 calculation.'
#         )

#         spec.outline(cls.submit_calculation, cls.get_result)

#     @check_workchain_step
#     def submit_calculation(self):
#         """
#         Run the Vasp2w90 calculation.
#         """
#         self.report("Submitting VASP2W90 calculation.")
#         return ToContext(
#             vasp_calc=self.submit(
#                 Vasp2w90Calculation,
#                 structure=self.inputs.structure,
#                 potential={(kind, ): pot
#                            for kind, pot in self.inputs.potentials.items()},
#                 kpoints=self.inputs.kpoints_mesh,
#                 parameters=self.inputs.parameters,
#                 code=self.inputs.code,
#                 wannier_parameters=self.inputs.get('wannier_parameters', None),
#                 wannier_projections=self.inputs.
#                 get('wannier_projections', None),
#                 **self.inputs.get('calculation_kwargs', {})
#             )
#         )

#     @check_workchain_step
#     def get_result(self):
#         """
#         Get the VASP result and create the necessary outputs.
#         """
#         self.out('wannier_settings', orm.Dict(dict={'seedname': 'wannier90'}))
#         vasp_calc_output = self.ctx.vasp_calc.out
#         retrieved_folder = vasp_calc_output.retrieved
#         folder_list = retrieved_folder.get_folder_list()
#         assert all(
#             filename in folder_list for filename in
#             ['wannier90.amn', 'wannier90.mmn', 'wannier90.eig']
#         )
#         self.report("Adding Wannier90 inputs to output.")
#         self.out('wannier_input_folder', retrieved_folder)
#         # reduce 'num_wann' if 'exclude_bands' is given
#         self.out(
#             'wannier_parameters',
#             reduce_num_bands(vasp_calc_output.wannier_parameters)
#         )
#         self.out('wannier_bands', self.parse_wannier_bands(retrieved_folder))
#         self.out('wannier_projections', vasp_calc_output.wannier_projections)

#     def parse_wannier_bands(self, retrieved_folder):
#         """
#         Parse the Wannier90 bands from the .win and .eig files.
#         """
#         bands = orm.BandsData()
#         bands.set_kpoints(
#             self.parse_kpts(retrieved_folder.get_abs_path('wannier90.win'))
#         )
#         bands.set_bands(
#             self.parse_eig(retrieved_folder.get_abs_path('wannier90.eig'))
#         )
#         return bands

#     # TODO: Replace with tools from aiida-wannier90, or integrate in vasp2w90
#     @staticmethod
#     def parse_kpts(win_file):
#         """
#         Parse the k-points used by Wannier90 from the .win file.
#         """
#         kpoints = []
#         for line in WinParser(win_file).result['kpoints']:
#             kpoints.append([float(x) for x in line.split()])
#         return np.array(kpoints)

#     # TODO: Replace with tools from aiida-wannier90, or integrate in vasp2w90
#     @staticmethod
#     def parse_eig(eig_file):
#         """
#         Parse the eigenvalues used by Wannier90 from the .eig file.
#         """
#         idx = 1
#         bands = []
#         bands_part = []
#         with open(eig_file, 'r') as in_file:
#             for line in in_file:
#                 _, idx_new, val = line.split()
#                 idx_new = int(idx_new)
#                 val = float(val)
#                 if idx_new > idx:
#                     idx = idx_new
#                     bands.append(bands_part)
#                     bands_part = []
#                 bands_part.append(val)
#             bands.append(bands_part)
#             return np.array(bands)
