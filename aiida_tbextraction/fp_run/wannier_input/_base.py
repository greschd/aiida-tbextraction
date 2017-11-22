from fsc.export import export

from aiida.orm import DataFactory
from aiida.orm.data.base import List
from aiida.work.workchain import WorkChain


@export  # pylint: disable=abstract-method
class WannierInputBase(WorkChain):
    """
    The base class for WorkChains which can be used to calculate the Wannier90 input files. It defines the inputs required by these WorkChains.
    """

    @classmethod
    def define(cls, spec):
        super(WannierInputBase, cls).define(spec)

        ParameterData = DataFactory('parameter')
        spec.input('structure', valid_type=DataFactory('structure'))
        spec.input('kpoints_mesh', valid_type=DataFactory('array.kpoints'))
        spec.input_group('potentials')

        spec.input(
            'wannier_parameters', valid_type=ParameterData, required=False
        )
        spec.input(
            'wannier_projections',
            valid_type=(DataFactory('orbital'), List),
            required=False
        )

        spec.output('wannier_input_folder', valid_type=DataFactory('folder'))
        spec.output('wannier_parameters', valid_type=ParameterData)
        spec.output('wannier_bands', valid_type=DataFactory('array.bands'))
        spec.output(
            'wannier_settings', valid_type=ParameterData, required=False
        )
        spec.output('wannier_projections', valid_type=List, required=False)
