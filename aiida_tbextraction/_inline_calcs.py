try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

from aiida.orm.data.parameter import ParameterData
from aiida.orm.calculation.inline import make_inline

from fsc.export import export


@export
@make_inline
def merge_parameterdata_inline(param_primary, param_secondary):
    return ParameterData(
        dict=ChainMap(param_primary.get_dict(), param_secondary.get_dict())
    )


@export
@make_inline
def slice_bands_inline(bands, slice_idx):
    result = bands.copy()
    result.set_bands(result.get_bands()[:, slice_idx.get_attr('list')])
    return result
