# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines a workflow that calculates the Wannier90 input files using Quantum ESPRESSO pw.x.
"""

import more_itertools
import copy
import io

from collections import ChainMap
from aiida import orm
from aiida.orm import Int, List, SinglefileData
from aiida.engine import WorkChain, calcfunction

from aiida_tools import check_workchain_step
from aiida_quantumespresso.calculations.pw2wannier90 import Pw2wannier90Calculation

__all__ = ("Pw2Wannier90Chain", )


@calcfunction
def get_new_nnkpfile(nnkp_file, new_excludebands):
    """
    Generates a new nnkp_file replacing the contents of the original
    file with the new exclude bands list.

    Parameters
    ----------
    nnkp_file :
        The SingleFileData for the nnkp output.
    new_excludebands :
        The new list of bands to exclude.
    """
    nnkp_content = nnkp_file.get_content().splitlines()
    s_exlbnd = nnkp_content.index('begin exclude_bands')
    f_exlbnd = nnkp_content.index('end exclude_bands')

    new_nnkpcontent = copy.deepcopy(nnkp_content)
    del new_nnkpcontent[s_exlbnd + 1:f_exlbnd]
    new_excludebands = list(new_excludebands)
    new_excludebands.sort(reverse=True)  # sort backwards to display in order
    new_nnkpcontent.insert(s_exlbnd + 1, " {}".format(len(new_excludebands)))
    for bnd in new_excludebands:
        new_nnkpcontent.insert(s_exlbnd + 2, " {}".format(bnd))

    new_nnkpcontent = "\n".join(new_nnkpcontent)
    new_nnkpcontent = new_nnkpcontent.encode()

    return SinglefileData(io.BytesIO(new_nnkpcontent))


def get_old_excludebands(nnkp_file):
    """
    Parses the nnkp_file for the 'old' exclude bands list.

    Parameters
    ----------
    nnkp_file :
        The SingleFileData for the nnkp output.
    """
    nnkp_content = nnkp_file.get_content().splitlines()

    s_exlbnd = nnkp_content.index('begin exclude_bands')
    f_exlbnd = nnkp_content.index('end exclude_bands')

    original_excludebands = [
        int(x) for x in nnkp_content[s_exlbnd + 2:f_exlbnd]
    ]
    return original_excludebands


def get_combinations(target_bands, batch_size):
    """
    Parameters
    ----------
    target_bands :
        The bands for which the MMN matrix should be computed.
    batch_size :
        Bands are grouped into "subgroups" of length `batch_size`.
        Each individual pw2wannier90 calculation will have at most
        `2 * batch_size` bands.
    """
    target_bands = list(target_bands)
    batch_size = int(batch_size)
    batched_bands = list(more_itertools.chunked(target_bands, batch_size))
    run_bands = []
    for i, part_a in enumerate(batched_bands):
        for part_b in batched_bands[i + 1:]:
            run_bands.append(part_a + part_b)
    return run_bands


def get_exclude_bands(all_bands, target_bands, batch_size):
    """
    Parameters
    ----------
    all_bands :
        All bands that are contained in the parent calculation.
    target_bands :
        The bands for which the MMN matrix should be computed.
    batch_size :
        Bands are grouped into "subgroups" of length `batch_size`.
        Each individual pw2wannier90 calculation will have at most
        `2 * batch_size` bands.
    """
    all_bands = set(all_bands)
    run_bands_list = get_combinations(target_bands, batch_size)
    index_mapping = {
        old_index: new_index
        for new_index, old_index in enumerate(target_bands)
    }
    run_bands_indices = [[index_mapping[old_idx] for old_idx in rb]
                         for rb in run_bands_list]
    exclude_bands = [
        sorted(all_bands - set(run_bands)) for run_bands in run_bands_list
    ]
    return exclude_bands, run_bands_indices


class Pw2Wannier90Chain(WorkChain):
    """
    Workchain for handling pw2wannier calculations
    """
    @classmethod
    def define(cls, spec):
        super().define(spec)

        #TODO: discuss metadata
        spec.expose_inputs(
            Pw2wannier90Calculation,
            namespace='pw2wann',
        )
        spec.input(
            'number_bands',
            valid_type=Int,
            help='The number of bands for the calculation'
        )
        #TODO: make this an optional argument and if it is not specified don't parallelize
        spec.input(
            'bands_batchsize',
            valid_type=Int,
            help='The batch size for creating groups of bands to calculate. '
            'Each calculation will have at most 2*bands_batchsize'
        )

        # Exposing inputs from a calculation incorrectly sets the
        # calcjob validator, see aiida-core issue #3449
        spec.inputs.validator = None

        spec.outline(cls.run_pw2wannier90, cls.get_result)

    @check_workchain_step
    def run_pw2wannier90(self):
        """
        Run the pw2wannier90 calculation.
        """
        # 1. collect the inputs set at the beginning from the ctx
        self.report("Submitting pw2wannier90 calculation.")
        nnkp_file = self.inputs.pw2wann.nnkp_file
        number_bands = self.inputs.number_bands
        bands_batchsize = self.inputs.bands_batchsize

        # 2. submit the amn-enabled calculation
        amn_settings = orm.Dict(
            dict={
                'ADDITIONAL_RETRIEVE_LIST': ['aiida.eig', 'aiida.amn'],
                'PARENT_FOLDER_SYMLINK': True
            }
        )
        amn_parameters = orm.Dict(dict={'INPUTPP': {'write_mmn': False}})
        key = 'pw2wann_amn_only'
        future = self.submit(
            Pw2wannier90Calculation,
            **ChainMap(
                {
                    'parameters': amn_parameters,
                    'settings': amn_settings,
                    'nnkp_file': nnkp_file
                },
                self.exposed_inputs(
                    Pw2wannier90Calculation, namespace='pw2wann'
                ),
            )
        )
        self.to_context(**{key: future})

        # 3. generate a list of nnkp files to permutate over
        mmn_settings = orm.Dict(
            dict={
                'ADDITIONAL_RETRIEVE_LIST': ['aiida.mmn'],
                'PARENT_FOLDER_SYMLINK': True
            }
        )
        mmn_parameters = orm.Dict(
            dict={'INPUTPP': {
                'write_amn': False,
                'write_unk': False
            }}
        )
        all_bands = range(1, int(number_bands) + 1)
        old_excludebands = get_old_excludebands(nnkp_file)
        target_bands = [x for x in all_bands if x not in old_excludebands]

        exclude_bandgroups, newindex_bandgroups = get_exclude_bands(
            all_bands, target_bands, bands_batchsize
        )
        self.ctx.exclude_band_groups = newindex_bandgroups

        for i, exclude_band_group in enumerate(exclude_bandgroups):
            exclude_band_group = List(list=exclude_bandgroups)
            new_nnkp_file = get_new_nnkpfile(nnkp_file, exclude_band_group)
            # 4. submit all the mmn calculations
            #from aiida_msq.tools.pprint_aiida import pprint_aiida
            #pprint_aiida(

            future = self.submit(
                Pw2wannier90Calculation,
                **ChainMap(
                    {
                        'parameters': mmn_parameters,
                        'settings': mmn_settings,
                        'nnkp_file': new_nnkp_file
                    },
                    self.exposed_inputs(
                        Pw2wannier90Calculation, namespace='pw2wann'
                    ),
                )
            )
            key = 'pw2wann_mmn_only_{}'.format(i)
            self.to_context(**{key: future})

    @check_workchain_step
    def get_result(self):
        """
        Get the pw2wannier90 result and create the necessary outputs.
        """
        # TODO: replace this with something that works

        # pw2wann_retrieved_folder = self.ctx.pw2wannier90.outputs.retrieved
        # pw2wann_folder_list = pw2wann_retrieved_folder.list_object_names()
        # assert all(
        # filename in pw2wann_folder_list
        # for filename in ['aiida.amn', 'aiida.mmn', 'aiida.eig']
        # )
        # self.report("Adding Wannier90 inputs to output.")
        # self.out('wannier_input_folder', pw2wann_retrieved_folder)

        # # The bands in aiida.eig are the same as the NSCF output up to
        # # writing / parsing error.
        # # NOTE: If this ends up being problematic for the 'invalid window'
        # # detection, maybe add fuzzing there, since it is not possible
        # # to always perfectly map aiida.eig to a floating-point value.
        # # Discrepancy should be roughly ~< 1e-06
        # self.out('wannier_bands', self.ctx.nscf.outputs.output_band)
        # if 'wannier_projections' in self.inputs:
        # self.out('wannier_projections', self.inputs.wannier_projections)
