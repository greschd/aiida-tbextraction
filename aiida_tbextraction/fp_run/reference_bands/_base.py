from fsc.export import export

from aiida.orm import DataFactory
from aiida.work.workchain import WorkChain


@export  # pylint: disable=abstract-method
class ReferenceBandsBase(WorkChain):
    """
    The base class for WorkChains which can be used to calculate the reference bandstructure. It defines the inputs required by these WorkChains.
    """

    @classmethod
    def define(cls, spec):
        super(ReferenceBandsBase, cls).define(spec)

        spec.input('structure', valid_type=DataFactory('structure'))
        spec.input('kpoints', valid_type=DataFactory('array.kpoints'))
        spec.input(
            'kpoints_mesh',
            valid_type=DataFactory('array.kpoints'),
            required=False
        )
        spec.input_namespace('potentials', dynamic=True)

        spec.output('bands', valid_type=DataFactory('array.bands'))
