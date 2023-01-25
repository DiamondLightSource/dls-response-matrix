import os
from unittest import mock

import pytest

from dls_response_matrix import configuration

TEST_FILE_NAME = "TEST FILE NAME"
TEST_ISO_TIME = "20000101T010203"


def test_check_limits_delta_is_zero():
    pytac_unit = "pytac.ENG"
    delta_limits = configuration.DELTA_LIMITS[pytac_unit]
    result = configuration.Config._check_limits(0, pytac_unit)
    assert result == (delta_limits[2], delta_limits[3])


def test_check_limits_delta_too_large():
    pytac_unit = "pytac.ENG"
    delta_limits = configuration.DELTA_LIMITS[pytac_unit]
    with pytest.raises(Exception, match=f"[{delta_limits[1]}, {delta_limits[0]}]"):
        raise configuration.Config._check_limits(delta_limits[0] + 1, pytac_unit)


def test_check_limits_delta_too_small():
    pytac_unit = "pytac.ENG"
    delta_limits = configuration.DELTA_LIMITS[pytac_unit]
    with pytest.raises(Exception, match=f"[{delta_limits[1]}, {delta_limits[0]}]"):
        raise configuration.Config._check_limits(delta_limits[1] - 1, pytac_unit)


def test_check_limits_wrong_units():
    phys_delta_limits = configuration.DELTA_LIMITS["pytac.PHYS"]
    eng_delta_limits = configuration.DELTA_LIMITS["pytac.ENG"]
    with pytest.raises(Exception):
        raise configuration.Config._check_limits(
            eng_delta_limits[0], phys_delta_limits[3]
        )


def test_check_limits_correct_value():
    pytac_unit = "pytac.ENG"
    delta_limits = configuration.DELTA_LIMITS[pytac_unit]
    test_value = delta_limits[0] * 0.5
    result = configuration.Config._check_limits(test_value, pytac_unit)
    assert result == (test_value, delta_limits[3])


def test_configure_ports_for_sim():
    port_name = "EPICS_CA_SERVER_PORT"
    sim_info = configuration.MACHINE_SETUP["SIM"]
    configuration.Config._configure_port(sim_info[1])
    assert os.environ.get(port_name) == sim_info[1]


def test_configure_ports_for_live():
    port_name = "EPICS_CA_SERVER_PORT"
    live_info = configuration.MACHINE_SETUP["LIVE"]
    configuration.Config._configure_port(live_info[1])
    assert os.environ.get(port_name) == live_info[1]


@mock.patch(
    "dls_response_matrix.configuration.Config._check_limits",
    return_value=(100.0, "reformatted"),
)
@mock.patch("dls_response_matrix.configuration.Config._machine_setup", return_value=3.0)
def test_get_configuration_returns_Config_with_correct_validation(
    mock_check_limits, mock_machine_setup
):
    expected_config = configuration.Config(
        TEST_FILE_NAME,
        TEST_ISO_TIME,
        "reformatted",
        "I04",
        "SIM",
        100,
        3,
    )
    config = configuration.Config.get_configuration(
        TEST_FILE_NAME,
        TEST_ISO_TIME,
        "pytac.ENG",
        "I04",
        "SIM",
        0,
    )
    assert config == expected_config


@mock.patch(
    "dls_response_matrix.configuration.Config._check_limits",
    return_value=(100.0, "reformatted"),
)
@mock.patch("dls_response_matrix.configuration.Config._machine_setup", return_value=3.0)
def test_get_configuration_returns_Config_with_default_filename_if_filename_is_None(
    mock_check_limits, mock_machine_setup
):
    TEST_FILE_NAME_NONE = None
    expected_config = configuration.Config(
        TEST_ISO_TIME,
        TEST_ISO_TIME,
        "reformatted",
        "I04",
        "SIM",
        100,
        3,
    )
    config = configuration.Config.get_configuration(
        TEST_FILE_NAME_NONE,
        TEST_ISO_TIME,
        "pytac.ENG",
        "I04",
        "SIM",
        0,
    )
    assert config == expected_config
