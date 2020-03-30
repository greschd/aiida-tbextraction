# -*- coding: utf-8 -*-
"""
Implements evaluating the tight-binding model by checking the distance
between its orbitals and the atomic positions.
"""

import tbmodels
import numpy as np

from aiida import orm
from aiida.engine import calcfunction, run_get_node
from aiida.engine.processes import ExitCode

from ._base import ModelEvaluationBase


@calcfunction
def get_max_distance(tb_model, structure):
    """
    Get the maximum cartesian distance between model orbitals and the
    nearest atom.
    """

    with tb_model.open(mode='rb') as input_file:
        model = tbmodels.io.load(input_file)

    reference_structure_pmg = structure.get_pymatgen()

    if not np.allclose(model.uc, reference_structure_pmg.lattice.matrix):
        return ExitCode(
            300,
            "The model and reference structure unit cells do not match.",
            invalidates_cache=False
        )

    dist_per_orbital = np.min(
        reference_structure_pmg.lattice.get_all_distances(
            model.pos, reference_structure_pmg.frac_coords
        ),
        axis=-1
    )
    max_dist = np.max(dist_per_orbital)
    return orm.Float(max_dist)


class MaximumOrbitalDistanceEvaluation(ModelEvaluationBase):
    """
    Evaluate the maximum distance between model orbitals and crystal
    atoms.
    """
    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.outline(cls.run_evaluation)

    def run_evaluation(self):
        """Run the calcfunction to get the maximum distance.
        """
        res, node = run_get_node(
            get_max_distance,
            tb_model=self.inputs.tb_model,
            structure=self.inputs.reference_structure
        )
        # Propagate exit code
        if not node.is_finished_ok:
            return ExitCode(node.exit_status, node.exit_message)
        self.out('cost_value', res)
