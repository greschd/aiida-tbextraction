try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

from fsc.export import export

from aiida.work.workchain import WorkChain, if_, ToContext
from aiida.orm.data.base import List, Str
from aiida.orm.data.parameter import ParameterData
from aiida.orm import Code, DataFactory, CalculationFactory

from aiida_tools import check_workchain_step


@export  # pylint: disable=abstract-method
class TightBindingCalculation(WorkChain):
    """
    This workchain creates a tight-binding model from the Wannier90 input and a symmetry file.
    """

    @classmethod
    def define(cls, spec):
        super(TightBindingCalculation, cls).define(spec)

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
        spec.input_namespace(
            'wannier_calculation_kwargs',
            dynamic=True,
            help=
            'Additional keyword arguments passed to the ``wannier90.wannier90`` calculation.'
        )
        spec.input(
            'wannier_calculation_kwargs.options',
            non_db=True,
            help='Resource options for the Wannier90 calculation.'
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
            'Indices of the orbitals which are sliced (selected) from the tight-binding model. This can be used to either reduce the number of orbitals, or re-order the orbitals.'  # pylint: disable=line-too-long
        )
        spec.input(
            'symmetries',
            valid_type=DataFactory('singlefile'),
            required=False,
            help=
            'File containing the symmetries which will be applied to the tight-binding model. The file must be in ``symmetry-representation`` HDF5 format.'  # pylint: disable=line-too-long
        )
        spec.output(
            'tb_model',
            valid_type=DataFactory('singlefile'),
            help='The calculated tight-binding model, in TBmodels HDF5 format.'
        )

        spec.outline(
            cls.run_wswannier, cls.parse,
            if_(cls.has_slice)(cls.slice),
            if_(cls.has_symmetries)(cls.symmetrize), cls.finalize
        )

    def has_slice(self):
        return 'slice_idx' in self.inputs

    def has_symmetries(self):
        return 'symmetries' in self.inputs

    @check_workchain_step
    def run_wswannier(self):
        wannier_parameters = self.inputs.wannier_parameters.get_dict()
        wannier_parameters.setdefault('write_hr', True)
        wannier_parameters.setdefault('write_xyz', True)
        wannier_parameters.setdefault('use_ws_distance', True)
        self.report("Running Wannier90 calculation.")

        # optional inputs
        inputs = dict(
            projections=self.inputs.get('wannier_projections', None),
            structure=self.inputs.get('structure', None),
        )
        inputs = {k: v for k, v in inputs.items() if v is not None}

        inputs.update(self.inputs.wannier_calculation_kwargs)

        return ToContext(wannier_calc=self.submit(
            CalculationFactory('wannier90.wannier90').process(),
            code=self.inputs.wannier_code,
            local_input_folder=self.inputs.wannier_input_folder,
            parameters=ParameterData(dict=wannier_parameters),
            kpoints=self.inputs.wannier_kpoints,
            settings=ParameterData(
                dict=ChainMap( # yapf: disable
                    self.inputs.get('wannier_settings', ParameterData()).get_dict(),
                    dict(
                        retrieve_hoppings=True,
                        additional_retrieve_list=['*_centres.xyz', '*.win']
                    )
                )
            ),
            **inputs
        ))

    def setup_tbmodels(self, calc_string):
        builder = CalculationFactory(calc_string).get_builder()
        builder.code = self.inputs.tbmodels_code
        builder.options = dict(resources={'num_machines': 1}, withmpi=False)
        return builder

    @property
    def tb_model(self):
        return self.ctx.tbmodels_calc.out.tb_model

    @check_workchain_step
    def parse(self):
        builder = self.setup_tbmodels('tbmodels.parse')
        builder.wannier_folder = self.ctx.wannier_calc.out.retrieved
        builder.pos_kind = Str('nearest_atom')
        self.report("Parsing Wannier90 output to tbmodels format.")
        return ToContext(tbmodels_calc=self.submit(builder))

    @check_workchain_step
    def slice(self):
        builder = self.setup_tbmodels('tbmodels.slice')
        builder.tb_model = self.tb_model
        builder.slice_idx = self.inputs.slice_idx
        self.report("Slicing tight-binding model.")
        return ToContext(tbmodels_calc=self.submit(builder))

    @check_workchain_step
    def symmetrize(self):
        builder = self.setup_tbmodels('tbmodels.symmetrize')
        builder.tb_model = self.tb_model
        builder.symmetries = self.inputs.symmetries
        self.report("Symmetrizing tight-binding model.")
        return ToContext(tbmodels_calc=self.submit(builder))

    @check_workchain_step
    def finalize(self):
        self.out("tb_model", self.tb_model)
        self.report('Adding tight-binding model to results.')
