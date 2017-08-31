from aiida.orm import DataFactory
from aiida.orm.code import Code
from aiida.orm.data.base import List
from aiida.work.workchain import WorkChain

from .reference_bands.base import ReferenceBandsBase
from .wannier_input.base import ToWannier90Base

class RunDFTBase(WorkChain):
    """
    """
    @classmethod
    def define(cls, spec):
        super(RunDFTBase, cls).define(spec)

        spec.expose_inputs(ReferenceBandsBase)
        spec.expose_inputs(ToWannier90Base)
        spec.output('bands', valid_type=DataFactory('array.bands'))

        spec.input(
            'wannier_parameters', valid_type=ParameterData,
            required=False
        )
        spec.input(
            'wannier_projections',
            valid_type=(DataFactory('orbital'), List), required=False
        )

        spec.output('wannier_input_folder', valid_type=DataFactory('folder'))
        spec.output('wannier_parameters', valid_type=ParameterData)
        spec.output('wannier_bands', valid_type=DataFactory('array.bands'))
        spec.output('wannier_settings', valid_type=ParameterData, required=False)
        spec.output('wannier_projections', valid_type=List, required=False)
