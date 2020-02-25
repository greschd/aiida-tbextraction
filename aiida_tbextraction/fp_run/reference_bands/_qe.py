# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines a workflow that calculates the reference bandstructure using Quantum ESPRESSO.
"""

from aiida import orm
from aiida.engine import ToContext

from aiida_tools import check_workchain_step
from aiida_quantumespresso.calculations.pw import PwCalculation

from . import ReferenceBandsBase
from ..._calcfunctions import merge_nested_dict
from .._helpers._calcfunctions import flatten_bands_inline

__all__ = ("QuantumEspressoReferenceBands", )


class QuantumEspressoReferenceBands(ReferenceBandsBase):
    """
    The WorkChain to calculate reference bands with Quantum ESPRESSO.
    """
    @classmethod
    def define(cls, spec):
        super().define(spec)

        # top-level inputs as defined by the base class
        spec.expose_inputs(PwCalculation, include=['structure', 'kpoints'])
        # The 'calcjob' validator is mistakenly assigned upon exposing,
        # see aiida-core issue #3449.
        spec.inputs.validator = None

        # cannot put everything at the top-level because 'metadata'
        # would then be interpreted at the workchain level
        spec.expose_inputs(
            PwCalculation, exclude=['structure', 'kpoints'], namespace='pw'
        )

        spec.outline(cls.run_calc, cls.get_bands)

    @check_workchain_step
    def run_calc(self):
        """
        Run the QE calculation.
        """

        self.report("Submitting pw.x bands calculation.")

        pw_inputs = self.exposed_inputs(PwCalculation, namespace='pw')
        pw_inputs['parameters'] = merge_nested_dict(
            orm.Dict(dict={'CONTROL': {
                'calculation': 'bands'
            }}), pw_inputs.get('parameters', orm.Dict())
        )

        return ToContext(pw_calc=self.submit(PwCalculation, **pw_inputs))

    @check_workchain_step
    def get_bands(self):
        """
        Get the bands from the  Quantum ESPRESSO calculation.
        """
        bands = self.ctx.pw_calc.outputs.output_band
        self.report(str(bands.get_bands().shape))
        self.report("Flattening the output bands.")
        self.out('bands', flatten_bands_inline(bands=bands))
