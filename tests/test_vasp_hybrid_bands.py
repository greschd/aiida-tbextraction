"""
Defines tests for the workflow calculating the reference bands with VASP and hybrid functionals.
"""

from insb_sample import get_insb_input  # pylint: disable=unused-import


def test_vasp_hybrid_bands(
    configure_with_daemon,  # pylint: disable=unused-argument
    assert_finished,
    get_insb_input  # pylint: disable=redefined-outer-name
):
    """
    Runs the VASP + hybrids reference bands workflow with InSb, on a very coarse grid.
    """
    from aiida.orm import DataFactory
    from aiida.work.run import run
    from aiida_tbextraction.dft_run.reference_bands import VaspHybridsReferenceBands

    KpointsData = DataFactory('array.kpoints')  # pylint: disable=invalid-name
    kpoints_mesh = KpointsData()
    kpoints_mesh.set_kpoints_mesh([2, 2, 2])

    kpoints = KpointsData()
    kpoints.set_kpoints_path([('G', (0, 0, 0), 'M', (0.5, 0.5, 0.5))])

    result, pid = run(
        VaspHybridsReferenceBands,
        _return_pid=True,
        kpoints=kpoints,
        kpoints_mesh=kpoints_mesh,
        **get_insb_input
    )
    assert_finished(pid)
    assert 'bands' in result
    assert result['bands'].get_bands().shape == (10, 36)
