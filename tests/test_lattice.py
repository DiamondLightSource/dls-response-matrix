import random
from unittest import mock

import numpy as np
import pytac
import pytest

from dls_response_matrix import configuration, lattice, results

config_live = configuration.Config(
    "TEST_ISO_TIME",
    "TEST_ISO_TIME",
    "reformatted",
    "I04",
    "LIVE",
    100,
    3,
)
config_sim = configuration.Config(
    "TEST_ISO_TIME",
    "TEST_ISO_TIME",
    "reformatted",
    "I04",
    "SIM",
    100,
    3,
)
config_incorrect = configuration.Config(
    "TEST_ISO_TIME",
    "TEST_ISO_TIME",
    "reformatted",
    "FALSE_RINGMODE",
    "SIM",
    100,
    3,
)


@mock.patch("pytac.lattice.Lattice.get_elements", return_value=1)
def test_LatticeModel_init_using_the_live_machine(mock_get_elements):
    latticemodel = lattice.LatticeModel(config_live)
    assert latticemodel.hstr == 1 and latticemodel._config == config_live


def test_LatticeModel_init_using_the_sim_machine():
    latticemodel = lattice.LatticeModel(config_sim)
    print(type(latticemodel.hstr[0]))
    assert (
        type(latticemodel.hstr[0]) is pytac.element.EpicsElement
        and latticemodel._config == config_sim
    )


def test_LatticeModel_init_using_incorrect_config():
    with pytest.raises(FileNotFoundError):
        lattice.LatticeModel(config_incorrect)


@mock.patch(
    "pytac.lattice.EpicsLattice.get_element_values",
    return_value=[random.randint(0, 1) for _ in range(10)],
)
@mock.patch(
    "pytac.lattice.Lattice.get_elements",
    return_value=[random.randint(0, 5) for _ in range(10)],
)
def test_LatticeModel_disable_correctors_where_true(
    mock_get_elements, mock_get_element_values
):
    latticemodel = lattice.LatticeModel(config_sim)
    disabled = latticemodel.disable_correctors(True)
    assert all(num >= 0 for num in disabled[0])


@mock.patch(
    "pytac.lattice.EpicsLattice.get_element_values",
    return_value=[random.randint(0, 1) for _ in range(10)],
)
@mock.patch(
    "pytac.lattice.Lattice.get_elements",
    return_value=[random.randint(0, 5) for _ in range(10)],
)
def test_LatticeModel_disable_correctors_where_false(
    mock_get_elements, mock_get_element_values
):
    latticemodel = lattice.LatticeModel(config_sim)
    disabled = latticemodel.disable_correctors(False)
    assert disabled == [[-1], [-1]]


@mock.patch(
    "pytac.lattice.EpicsLattice.get_element_values",
    return_value=[random.randint(0, 1) for _ in range(10)],
)
@mock.patch(
    "pytac.lattice.Lattice.get_elements",
    return_value=[random.randint(0, 5) for _ in range(10)],
)
def test_LatticeModel_disable_bpms_where_true(
    mock_get_elements, mock_get_element_values
):
    latticemodel = lattice.LatticeModel(config_sim)
    disabled = latticemodel.disable_bpms(True)
    assert all(num >= 0 for num in disabled)


@mock.patch(
    "pytac.lattice.EpicsLattice.get_element_values",
    return_value=[random.randint(0, 1) for _ in range(10)],
)
@mock.patch(
    "pytac.lattice.Lattice.get_elements",
    return_value=[random.randint(0, 5) for _ in range(10)],
)
def test_LatticeModel_disable_bpms_where_false(
    mock_get_elements, mock_get_element_values
):
    latticemodel = lattice.LatticeModel(config_sim)
    disabled = latticemodel.disable_bpms(False)
    assert disabled == [-1]


@mock.patch(
    "pytac.lattice.EpicsLattice.get_element_values",
    return_value=[-2],
)
def test_LatticeModel_measure_correctors(mock_get_element_values):
    latticemodel = lattice.LatticeModel(config_sim)
    values = latticemodel.measure_correctors()
    assert values == [[-2], [-2]]


@mock.patch(
    "pytac.lattice.EpicsLattice.get_element_values",
    return_value=[0, 1, 2],
)
def test_LatticeModel_meausure_bpms_passes(mock_get_element_values):
    latticemodel = lattice.LatticeModel(config_sim)
    values = latticemodel.measure_bpms()
    assert values == [0, 1, 2, 0, 1, 2]


@mock.patch(
    "pytac.lattice.EpicsLattice.get_element_values",
    side_effect=pytac.exceptions.ControlSystemException,
)
def test_LatticeModel_meausure_bpms_timeout_exception(mock_get_element_values):
    latticemodel = lattice.LatticeModel(config_sim)
    with pytest.raises(lattice.BeamPositionMonitorException):
        latticemodel.measure_bpms()


@mock.patch("dls_response_matrix.lattice.LatticeModel.calculate_axis_response")
def test_LatticeModel_calculate_responses_passes(mock_calculate_axis_response):
    latticemodel = lattice.LatticeModel(config_sim)
    result = results.Results.from_corrector_info(config_sim, 1, 1, 1)
    latticemodel.calculate_responses(result, progress_callback=lambda x: None)
    assert latticemodel.counter == 0


@mock.patch("dls_response_matrix.lattice.LatticeModel.measure_bpms", return_value=[0])
@mock.patch("cothread.Sleep")
@mock.patch("pytac.element.Element.set_value")
def test_LatticeModel_calculate_axis_response_passes(
    mock_set_value, mock_sleep, mock_measure_bpms
):
    latticemodel = lattice.LatticeModel(config_sim)

    estimated_matrix = np.zeros(
        shape=(
            len(latticemodel.bpm) * 2,
            len(latticemodel.hstr) + len(latticemodel.vstr),
        )
    )
    result = results.Results.from_corrector_info(
        config_sim,
        len(latticemodel.hstr),
        len(latticemodel.vstr),
        len(latticemodel.bpm),
    )
    with mock.patch("pytac.element.Element.get_value", return_value=0):
        latticemodel.calculate_responses(result, progress_callback=lambda x: None)
    assert np.array_equiv(result._matrix, estimated_matrix)
