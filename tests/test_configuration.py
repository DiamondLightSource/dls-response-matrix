import glob
import os
from unittest import mock

import pytest

from dls_response_matrix import configuration

TEST_FILE_NAME = "TEST FILE NAME"
TEST_FILE_PATH = "/TEST/FILE/PATH"

TEST_ISO_TIME = "20000101T010203"


def test_check_limits_returns_default_if_propsed_delta_is_zero():
    pytac_unit = "pytac.ENG"
    delta_limits = configuration.DELTA_LIMITS[pytac_unit]
    result = configuration.Config._check_limits(0, pytac_unit)
    assert result == (delta_limits.default, delta_limits.pytac)


def test_check_limits_raises_ValueError_if_delta_too_large():
    pytac_unit = "pytac.ENG"
    delta_limits = configuration.DELTA_LIMITS[pytac_unit]
    with pytest.raises(ValueError, match=f"[{delta_limits.min}, {delta_limits.max}]"):
        configuration.Config._check_limits(delta_limits.max + 1, pytac_unit)


def test_check_limits_raises_ValueError_if_delta_too_small():
    pytac_unit = "pytac.ENG"
    delta_limits = configuration.DELTA_LIMITS[pytac_unit]
    with pytest.raises(ValueError, match=f"[{delta_limits.min}, {delta_limits.max}]"):
        configuration.Config._check_limits(delta_limits.min - 1, pytac_unit)


def test_check_limits_raises_ValueError_if_wrong_units_used():
    eng_delta_limits = configuration.DELTA_LIMITS["pytac.ENG"]
    with pytest.raises(ValueError):
        configuration.Config._check_limits(eng_delta_limits.max, "pytac.PHYS")


def test_check_limits_returns_value_using_correct_limits():
    pytac_unit = "pytac.ENG"
    delta_limits = configuration.DELTA_LIMITS[pytac_unit]
    test_value = delta_limits.max * 0.5
    result = configuration.Config._check_limits(test_value, pytac_unit)
    assert result == (test_value, delta_limits.pytac)


def test_check_CA_ports_raises_error_when_machine_type_is_SIM_and_addr_port_is_5064():
    addr_port_name = "EPICS_CA_SERVER_PORT"
    machine_type = "SIM"
    port = 5064
    os.environ[addr_port_name] = str(port)
    with pytest.raises(ValueError):
        configuration.Config._check_CA_ports(machine_type)


def test_check_CA_ports_raises_error_when_machine_type_is_SIM_and_repeater_port_is_5065():
    repeater_port_name = "EPICS_CA_REPEATER_PORT"
    machine_type = "SIM"
    port = 5065
    os.environ[repeater_port_name] = str(port)
    with pytest.raises(ValueError):
        configuration.Config._check_CA_ports(machine_type)


def test_check_CA_ports_does_not_raise_error_when_machine_type_is_LIVE_and_port_is_8064():
    port_name = "EPICS_CA_SERVER_PORT"
    machine_type = "LIVE"
    port = 8064
    os.environ[port_name] = str(port)
    configuration.Config._check_CA_ports(machine_type)


def test_machine_setup_time_delay_raises_error_when_too_short():
    machine_type = "SIM"
    time_delay = 0.1
    with pytest.raises(ValueError):
        configuration.Config._machine_setup(time_delay, machine_type)


def test_machine_setup_coorect_time_delay_returned_for_LIVE_machine_type():
    machine_type = "LIVE"
    time_delay = 0.1
    result = configuration.Config._machine_setup(time_delay, machine_type)
    assert result == 0.1


def test_machine_setup_time_delay_returns_default_when_time_delay_is_none():
    machine_type = "SIM"
    time_delay = None
    result = configuration.Config._machine_setup(time_delay, machine_type)
    assert result == configuration.MACHINE_SETUP[machine_type][2]


@mock.patch(
    "dls_response_matrix.configuration.Config._check_limits",
    return_value=(100.0, "reformatted"),
)
@mock.patch("dls_response_matrix.configuration.Config._machine_setup", return_value=3.0)
def test_get_configuration_returns_Config_with_correct_values(
    mock_machine_setup, mock_check_limits
):
    expected_config = configuration.Config(
        TEST_FILE_NAME,
        TEST_FILE_PATH,
        TEST_ISO_TIME,
        "reformatted",
        "I04",
        "SIM",
        100,
        3,
    )
    config = configuration.Config.get_configuration(
        TEST_FILE_NAME,
        TEST_FILE_PATH,
        TEST_ISO_TIME,
        "pytac.ENG",
        "I04",
        "SIM",
        0.05,
        0.5,
    )
    assert config == expected_config


def test_get_configuration_files_are_named_correctly_if_given_expected_args(tmp_path):
    tmp_path = str(tmp_path)
    config = configuration.Config(
        TEST_ISO_TIME,
        tmp_path,
        TEST_ISO_TIME,
        "reformatted",
        "I04",
        "SIM",
        100,
        3,
    )
    metadata = configuration.Metadata(config)
    metadata.write_json()
    foldername = f"RM-{config.iso_time}"
    filename = os.path.join(tmp_path, foldername, "metadata*")
    metadata_file = glob.glob(filename)[0]
    assert ".json" in metadata_file
