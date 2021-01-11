# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines a workflow that calculates the Wannier90 input files using Quantum ESPRESSO pw.x.
"""

import copy
import gc
import io
import re
import tempfile
import os
from collections import ChainMap

import numpy as np
import more_itertools

from w90utils.io import write_mmn
from aiida import orm
from aiida.orm import Int, List, SinglefileData, FolderData
from aiida.engine import WorkChain, calcfunction
from aiida_tools import check_workchain_step
from aiida_quantumespresso.calculations.pw2wannier90 import Pw2wannier90Calculation

__all__ = ("SplitPw2wannier90", )


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

    # The logic for combining parts only works if there are at least
    # two batches, because we do not explicitly cover the diagonal
    # calculation.
    if batch_size >= len(target_bands):
        return [target_bands]

    batched_bands = list(more_itertools.chunked(target_bands, batch_size))
    assert len(batched_bands) >= 2
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


# TODO: confirm this function should stay here
def load_mmn_file(mmn_file):
    """
    Parameters
    ----------
    mmn_file :
        Path to mmn output file.
    """
    with open(mmn_file, "r") as f:
        f.readline()

        re_int = re.compile(r"[\d]+")

        # read the first line
        num_bands, num_kpts, num_neighbors = (
            int(i) for i in re.findall(re_int, f.readline())
        )

        # read the rest of the file
        lines = (line for line in f if line)

        step = num_bands * num_bands + 1

        res = np.zeros((num_kpts, num_neighbors, num_bands, num_bands),
                       dtype=complex)

        def grouper(iterable, group_size):
            """Collect data into fixed-length chunks or blocks"""
            args = [iter(iterable)] * group_size
            return zip(*args)

        blocks = grouper(lines, step)

        re_float = re.compile(r"[0-9.\-E]+")
        for i, block in enumerate(blocks):
            k_idx = i // num_neighbors
            neighbor_idx = i % num_neighbors
            block = iter(block)
            next(block)  # skip index header

            def to_complex(blockline):
                real_part, imag_part = re.findall(re_float, blockline)
                return float(real_part) + 1j * float(imag_part)

            res[k_idx,
                neighbor_idx] = np.array([[
                    to_complex(next(block)) for _ in range(num_bands)
                ] for _ in range(num_bands)],
                                         dtype=complex).T  # Do we need the .T?
    return res


def get_pw2wann_mmn(pw2wann_calc, prefix="aiida"):
    """
    Parameters
    ----------
    pw2wann_calc :
         An AiiDA pw2wannier90 completed calcjob
    """
    filename = prefix + ".mmn"
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_file = os.path.join(tmp_dir, filename)
        pw2wann_calc.outputs.remote_folder.getfile(filename, output_file)
        mmn_content = load_mmn_file(output_file)
        return mmn_content


def get_nnkp_indexes(nnkp_file):
    """
    Parameters
    ----------
    nnkp_file :
        An AiiDA nnkp_file SingleFileData output from
        a pw2wannier90 calcjob.
    """
    nnkp_content = nnkp_file.get_content().splitlines()

    kpoint_line = nnkp_content.index('begin kpoints') + 1
    num_kpoints = int(nnkp_content[kpoint_line])

    nnkpts_line = nnkp_content.index('begin nnkpts')
    num_kpoints_neighbors = int(nnkp_content[nnkpts_line + 1])

    kpb_kidx = np.zeros([num_kpoints, num_kpoints_neighbors])
    kpb_g = np.zeros([num_kpoints, num_kpoints_neighbors, 3])

    start_line = nnkpts_line + 2
    for i in range(num_kpoints):
        for j in range(num_kpoints_neighbors):
            nnkp_shift = i * num_kpoints_neighbors + j
            nnkp_line = start_line + nnkp_shift
            nnkp_line_content = nnkp_content[nnkp_line]

            #pylint: disable=invalid-name
            _, kpt_nb, r0, r1, r2 = [int(x) for x in nnkp_line_content.split()]
            kpb_kidx[i][j] = kpt_nb - 1  #watch out forpython/fortran indexing
            kpb_g[i][j][0] = r0
            kpb_g[i][j][1] = r1
            kpb_g[i][j][2] = r2
            #pylint: enable=invalid-name
    return kpb_kidx, kpb_g


class SplitPw2wannier90(WorkChain):
    """
    Workchain for handling pw2wannier calculations
    """
    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.expose_inputs(
            Pw2wannier90Calculation,
            namespace='pw2wannier',
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
            'Each calculation will have at most bands_batchsize'
        )

        # Exposing inputs from a calculation incorrectly sets the
        # calcjob validator, see aiida-core issue #3449
        spec.inputs.validator = None

        spec.outline(cls.run_pw2wannier90, cls.get_result)
        spec.output('pw2wannier_collected', valid_type=FolderData)

    @check_workchain_step
    def run_pw2wannier90(self):
        """
        Run the pw2wannier90 calculation.
        """
        # 1. collect the inputs set at the beginning from the ctx
        self.report("Submitting pw2wannier90 calculation.")
        nnkp_file = self.inputs.pw2wannier.nnkp_file
        number_bands = self.inputs.number_bands
        bands_batchsize = self.inputs.bands_batchsize
        bands_groupsize = max(int(bands_batchsize / 2), 1)

        # 2. submit the amn-enabled calculation
        amn_settings = orm.Dict(dict={'PARENT_FOLDER_SYMLINK': True})
        amn_parameters = orm.Dict(dict={'INPUTPP': {'write_mmn': False}})
        key = 'pw2wann_no_mmn'
        future = self.submit(
            Pw2wannier90Calculation,
            **ChainMap(
                {
                    'parameters': amn_parameters,
                    'settings': amn_settings,
                    'nnkp_file': nnkp_file
                },
                self.exposed_inputs(
                    Pw2wannier90Calculation, namespace='pw2wannier'
                ),
            )
        )
        self.to_context(**{key: future})

        # 3. generate a list of nnkp files to permutate over
        mmn_settings = orm.Dict(dict={'PARENT_FOLDER_SYMLINK': True})
        mmn_parameters = orm.Dict(
            dict={'INPUTPP': {
                'write_amn': False,
                'write_unk': False
            }}
        )
        all_bands = range(1, int(number_bands) + 1)
        old_excludebands = get_old_excludebands(nnkp_file)
        target_bands = [x for x in all_bands if x not in old_excludebands]
        self.ctx.number_output_bands = len(target_bands)

        exclude_bandgroups, newindex_bandgroups = get_exclude_bands(
            all_bands, target_bands, bands_groupsize
        )
        self.ctx.newindex_bandgroups = newindex_bandgroups

        for i, exclude_band_group in enumerate(exclude_bandgroups):
            exclude_band_group = List(list=exclude_band_group)
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
                        Pw2wannier90Calculation, namespace='pw2wannier'
                    ),
                )
            )
            key = 'pw2wann_mmn_only_{}'.format(i)
            self.to_context(**{key: future})

    #pylint: disable=too-many-locals
    @check_workchain_step
    def get_result(self):
        """
        Get the pw2wannier90 result and create the necessary outputs.
        """
        newindex_bandgroups = self.ctx.newindex_bandgroups

        # get kpt indexing information
        nnkp_file = self.inputs.pw2wannier.nnkp_file
        kpb_kidx, kpb_g = get_nnkp_indexes(nnkp_file)
        # pylint: disable=unpacking-non-sequence
        nkpt, nkpt_neigh = kpb_kidx.shape

        # get a sorted list of mmn pw2wann calcs
        pw2wann_calcs = sorted([
            x for x in self.ctx if 'pw2wann_mmn_only_' in x
        ],
                               key=lambda x: int(x.split('_')[-1]))

        pw2wann_calcs = [self.ctx[x] for x in pw2wann_calcs]
        assert len(newindex_bandgroups) == len(pw2wann_calcs)

        # get number of bands and all bands
        number_output_bands = int(self.ctx.number_output_bands)

        # collect all the pw2wann mmn matrices in one spot
        mmn_collected = np.zeros([
            nkpt, nkpt_neigh, number_output_bands, number_output_bands
        ],
                                 dtype=complex)

        for (calc, band_group) in zip(pw2wann_calcs, newindex_bandgroups):
            mmn_collected[np.ix_(
                np.arange(nkpt), np.arange(nkpt_neigh), band_group, band_group
            )] = get_pw2wann_mmn(calc)

        # prep the output folder
        folder = FolderData()

        # Writing mmn file, unfortunately this is a bit messy because
        # write_mmn dumps to a file which must be read again later
        mmn_filename = "aiida.mmn"
        with tempfile.NamedTemporaryFile() as tmp_file:
            output_file = tmp_file.name
            write_mmn(output_file, mmn_collected, kpb_kidx, kpb_g)

            # mmn_collected might be very large so we want to remove
            # it from memory before reading in a copy
            del mmn_collected
            gc.collect()  # for paranoia's sake run garbage collection

            folder.put_object_from_file(output_file, path=mmn_filename)

        # writing .amn and .eig outputs
        # TODO: Write also any other outputs produced by the 'no MMN'
        # pw2wannier90 run.
        filenames = ['aiida.eig', 'aiida.amn']
        no_mmn_calc = self.ctx['pw2wann_no_mmn']
        r_folder = no_mmn_calc.outputs.remote_folder
        with tempfile.TemporaryDirectory() as tmp_dir:
            for filename in filenames:
                output_file = os.path.join(tmp_dir, filename)
                r_folder.getfile(filename, output_file)
            folder.put_object_from_tree(os.path.abspath(tmp_dir))

        folder.store()
        self.out('pw2wannier_collected', folder)
