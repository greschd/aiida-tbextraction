try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

from fsc.export import export

import aiida
aiida.try_load_dbenv()
from aiida.orm.data.base import Str, List
from aiida.work.run import submit
from aiida.work.workchain import WorkChain, if_, ToContext
from aiida.orm import (Code, Computer, DataFactory, CalculationFactory)

from ._utils import check_workchain_step


@export
class TbExtraction(WorkChain):
    """
    This workchain creates a tight-binding model from the Wannier90 input and a symmetry file.
    """

    @classmethod
    def define(cls, spec):
        super(TbExtraction, cls).define(spec)

        ParameterData = DataFactory('parameter')
        spec.input(
            'structure',
            valid_type=DataFactory('structure'),
            required=False,
            help=
            'Structure of the material for which the tight-binding model should be calculated.'
        )
        spec.input(
            'wannier_code',
            valid_type=Code,
            help='Code that executes Wannier90.'
        )
        spec.input(
            'wannier_input_folder',
            valid_type=DataFactory('folder'),
            help=
            'A folder containing the Wannier90 ``.mmn`` and ``.amn`` input files.'
        )
        spec.input(
            'wannier_calculation_kwargs',
            valid_type=ParameterData,
            default=ParameterData(dict={'_options': {}}),
            help=
            'Additional keyword arguments passed to the ``wannier90.wannier90`` calculation.'
        )
        spec.input(
            'wannier_parameters',
            valid_type=ParameterData,
            help="Wannier90 paramaters written to the ``.win`` file."
        )
        spec.input(
            'wannier_settings',
            valid_type=ParameterData,
            required=False,
            help="Settings for the ``wannier90.wannier90`` calculation."
        )
        spec.input(
            'wannier_projections',
            valid_type=(DataFactory('orbital'), List),
            required=False,
            help=
            'Projections used, either as OrbitalData or as a list of strings in Wannier90\'s projections format.'
        )
        spec.input(
            'wannier_kpoints',
            valid_type=DataFactory('array.kpoints'),
            help=
            'The k-points used in the Wannier90 run. These must match the k-points used in the ``.amn`` and ``.mmn`` input files.'
        )

        spec.input(
            'tbmodels_code',
            valid_type=Code,
            help='Code that runs the TBmodels CLI.'
        )
        spec.input(
            'slice_idx',
            valid_type=List,
            required=False,
            help=
            'Indices of the orbitals which are sliced (selected) from the tight-binding model. This can be used to either reduce the number of orbitals, or re-order the orbitals.'
        )
        spec.input(
            'symmetries',
            valid_type=DataFactory('singlefile'),
            required=False,
            help=
            'File containing the symmetries which will be applied to the tight-binding model. The file must be in ``symmetry-representation`` HDF5 format.'
        )

        spec.outline(
            cls.run_wswannier, cls.parse,
            if_(cls.has_slice)(cls.slice),
            if_(cls.has_symmetries)(cls.symmetrize), cls.finalize
        )

        spec.output(
            'tb_model',
            valid_type=DataFactory('singlefile'),
            help='The calculated tight-binding model, in TBmodels HDF5 format.'
        )

    def has_slice(self):
        return 'slice_idx' in self.inputs

    def has_symmetries(self):
        return 'symmetries' in self.inputs

    @check_workchain_step
    def run_wswannier(self):
        wannier_parameters = self.inputs.wannier_parameters.get_dict()
        wannier_parameters.setdefault('write_hr', True)
        wannier_parameters.setdefault('use_ws_distance', True)
        self.report("Running Wannier90 calculation.")
        pid = submit(
            CalculationFactory('wannier90.wannier90').process(),
            code=self.inputs.wannier_code,
            local_input_folder=self.inputs.wannier_input_folder,
            parameters=DataFactory('parameter')(dict=wannier_parameters),
            kpoints=self.inputs.wannier_kpoints,
            projections=self.inputs.get('wannier_projections', None),
            structure=self.inputs.get('structure', None),
            settings=DataFactory('parameter')(
                dict=ChainMap(
                    self.inputs.get(
                        'wannier_settings', DataFactory('parameter')()
                    ).get_dict(), {'retrieve_hoppings': True}
                )
            ),
            **self.inputs.wannier_calculation_kwargs.get_dict()
        )
        return ToContext(wannier_calc=pid)

    def setup_tbmodels(self, calc_string):
        process = CalculationFactory(calc_string).process()
        inputs = process.get_inputs_template()
        inputs.code = self.inputs.tbmodels_code
        inputs._options.resources = {'num_machines': 1}
        inputs._options.withmpi = False
        return process, inputs

    @property
    def tb_model(self):
        return self.ctx.tbmodels_calc.out.tb_model

    @check_workchain_step
    def parse(self):
        process, inputs = self.setup_tbmodels('tbmodels.parse')
        inputs.wannier_folder = self.ctx.wannier_calc.out.retrieved
        self.report("Parsing Wannier90 output to tbmodels format.")
        pid = submit(process, **inputs)
        return ToContext(tbmodels_calc=pid)

    @check_workchain_step
    def slice(self):
        process, inputs = self.setup_tbmodels('tbmodels.slice')
        inputs.tb_model = self.tb_model
        inputs.slice_idx = self.inputs.slice_idx
        self.report("Slicing tight-binding model.")
        pid = submit(process, **inputs)
        return ToContext(tbmodels_calc=pid)

    @check_workchain_step
    def symmetrize(self):
        process, inputs = self.setup_tbmodels('tbmodels.symmetrize')
        inputs.tb_model = self.tb_model
        inputs.symmetries = self.inputs.symmetries
        self.report("Symmetrizing tight-binding model.")
        pid = submit(process, **inputs)
        return ToContext(tbmodels_calc=pid)

    @check_workchain_step
    def finalize(self):
        self.out("tb_model", self.tb_model)
        self.report('Added final tb_model to results.')
