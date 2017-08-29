from aiida.work.workchain import WorkChain
from aiida.orm import DataFactory
from aiida.orm.data.base import Float  

class ModelEvaluation(WorkChain):
    @classmethod
    def define(cls, spec):
        super(ModelEvaluation, cls).define(spec)
        spec.input('tb_model', valid_type=DataFactory('singlefile'))
        spec.input('reference_bands', valid_type=DataFactory('array.bands'))

        spec.output('result', valid_type=Float)
