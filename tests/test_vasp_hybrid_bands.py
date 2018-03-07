"""
Defines tests for the workflow calculating the reference bands with VASP and hybrid functionals.
"""

from insb_sample import get_insb_input  # pylint: disable=unused-import


def test_vasp_hybrid_bands(
    configure_with_daemon,  # pylint: disable=unused-argument
    assert_finished,
    wait_for,
    get_insb_input  # pylint: disable=redefined-outer-name
):
    """
    Runs the VASP + hybrids reference bands workflow with InSb, on a very coarse grid.
    """
    from aiida.orm.data.base import Bool
    from aiida.orm import DataFactory
    from aiida.work.run import submit
    from aiida_tbextraction.fp_run.reference_bands import VaspReferenceBands

    KpointsData = DataFactory('array.kpoints')
    kpoints_mesh = KpointsData()
    kpoints_mesh.set_kpoints_mesh([2, 2, 2])

    kpoints = KpointsData()
    kpoints.set_kpoints_path([('G', (0, 0, 0), 'M', (0.5, 0.5, 0.5))])

    pid = submit(
        VaspReferenceBands,
        _return_pid=True,
        merge_kpoints=Bool(True),
        kpoints=kpoints,
        kpoints_mesh=kpoints_mesh,
        **get_insb_input
    ).pid
    wait_for(pid)
    assert_finished(pid)
    result = load_node(pid).get_outputs_dict()
    assert 'bands' in result
    assert result['bands'].get_bands().shape == (10, 36)
