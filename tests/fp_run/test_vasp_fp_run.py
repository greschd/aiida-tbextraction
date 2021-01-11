# # -*- coding: utf-8 -*-

# # © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# # Author: Dominik Gresch <greschd@gmx.ch>
# """
# Tests for running the DFT calculations needed as input for the tight-binding calculation, using VASP
# """

#

# import pytest

# from aiida.engine.launch import run_get_node

# @pytest.mark.vasp
# def test_combined_fp_run(
#     configure_with_daemon, assert_finished, get_vasp_fp_run_inputs
# ):
#     """
#     Calculates the Wannier90 inputs from VASP with hybrid functionals.
#     """
#     from aiida_tbextraction.fp_run import VaspFirstPrinciplesRun

#     result, node = run_get_node(
#         VaspFirstPrinciplesRun, **get_vasp_fp_run_inputs()
#     )
#     assert node.is_finished_ok
#     assert all(
#         key in result for key in [
#             'wannier_input_folder', 'wannier_parameters', 'wannier_bands',
#             'bands'
#         ]
#     )
#     assert int(result['wannier_parameters'].get_attribute('num_wann')) == 14
#     folder_list = result['wannier_input_folder'].get_folder_list()
#     assert all(
#         filename in folder_list
#         for filename in ['wannier90.amn', 'wannier90.mmn', 'wannier90.eig']
#     )

#     assert False, "rest of the test not implemented yet"

#     # sub_workchains = []
#     # for label, node in node.get_outputs(also_labels=True):
#     #     if label == 'CALL' and isinstance(node, WorkCalculation):
#     #         sub_workchains.append(node)

#     # for sub_wc in sub_workchains:
#     #     for label, node in sub_wc.get_outputs(also_labels=True):
#     #         if label == 'CALL' and isinstance(node, VaspCalculation):
#     #             retrieved_folder = node.get_retrieved_node()
#     #             with open(
#     #                 retrieved_folder.get_abs_path('_scheduler-stdout.txt')
#     #             ) as f:
#     #                 stdout = f.read()
#     #                 assert 'WAVECAR not read' not in stdout
#     #                 assert 'reading WAVECAR' in stdout
