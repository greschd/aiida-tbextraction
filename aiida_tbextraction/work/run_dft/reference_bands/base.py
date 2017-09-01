from aiida.orm import DataFactory
from aiida.orm.code import Code
from aiida.orm.data.base import List
from aiida.work.workchain import WorkChain

class ReferenceBandsBase(WorkChain):
    """
    The base class for WorkChains which can be used to calculate the reference bandstructure. It defines the inputs required by these WorkChains.
    """
    @classmethod
    def define(cls, spec):
        super(ReferenceBandsBase, cls).define(spec)

        ParameterData = DataFactory('parameter')
        spec.input('structure', valid_type=DataFactory('structure'))
        spec.input('kpoints', valid_type=DataFactory('array.kpoints'))
        spec.input('kpoints_mesh', valid_type=DataFactory('array.kpoints'), required=False)
        spec.input_group('potentials')

        spec.output('bands', valid_type=DataFactory('array.bands'))
