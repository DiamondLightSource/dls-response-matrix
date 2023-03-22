import os
from unittest import mock

import pytest

from dls_response_matrix import configuration

TEST_FILE_NAME = "TEST FILE NAME"
TEST_ISO_TIME = "20000101T010203"


def test_check_limits_returns_default_if_propsed_delta_is_zero():
    pytac_unit = "pytac.ENG"
    delta_limits = configuration.DELTA_LIMITS[pytac_unit]
    result = configuration.Config._check_limits(0, pytac_unit)
    assert result == (delta_limits.default, delta_limits.pytac)


def test_check_limits_raises_ValueError_if_delta_too_large():
    pytac_unit = "pytac.ENG"
    delta_limits = configuration.DELTA_LIMITS[pytac_unit]
    with pytest.raises(ValueError, match=f"[{delta_limits[1]}, {delta_limits[0]}]"):
        configuration.Config._check_limits(delta_limits[0] + 1, pytac_unit)


def test_check_limits_raises_ValueError_if_delta_too_small():
    pytac_unit = "pytac.ENG"
    delta_limits = configuration.DELTA_LIMITS[pytac_unit]
    with pytest.raises(ValueError, match=f"[{delta_limits[1]}, {delta_limits[0]}]"):
        configuration.Config._check_limits(delta_limits[1] - 1, pytac_unit)


def test_check_limits_raises_ValueError_if_wrong_units_used():
    eng_delta_limits = configuration.DELTA_LIMITS["pytac.ENG"]
    with pytest.raises(ValueError):
        configuration.Config._check_limits(eng_delta_limits[0], "pytac.PHYS")


def test_check_limits_returns_value_using_correct_limits():
    pytac_unit = "pytac.ENG"
    delta_limits = configuration.DELTA_LIMITS[pytac_unit]
    test_value = delta_limits[0] * 0.5
    result = configuration.Config._check_limits(test_value, pytac_unit)
    assert result == (test_value, delta_limits[3])


def test_configure_ports_sets_ports_correctly_for_sim():
    port_name = "EPICS_CA_SERVER_PORT"
    sim_info = configuration.MACHINE_SETUP["SIM"]
    configuration.Config._configure_port(sim_info[1])
    assert os.environ.get(port_name) == sim_info[1]


def test_configure_ports_sets_ports_correctly_for_live():
    port_name = "EPICS_CA_SERVER_PORT"
    live_info = configuration.MACHINE_SETUP["LIVE"]
    configuration.Config._configure_port(live_info[1])
    assert os.environ.get(port_name) == live_info[1]


def test_machine_setup_set_correctly_for_live():
    machine_type = "LIVE"
    time_delay = configuration.MACHINE_SETUP[machine_type][0]
    result = configuration.Config._machine_setup(machine_type)
    assert time_delay == result


def test_machine_setup_set_correctly_for_sim():
    machine_type = "SIM"
    time_delay = configuration.MACHINE_SETUP[machine_type][0]
    result = configuration.Config._machine_setup(machine_type)
    assert time_delay == result


def test_machine_setup_raises_KeyError_because_incorrect_machine_type():
    machine_type = "DOES_NOT_EXIST"
    with pytest.raises(KeyError):
        configuration.Config._machine_setup(machine_type)


@mock.patch(
    "dls_response_matrix.configuration.Config._check_limits",
    return_value=(100.0, "reformatted"),
)
@mock.patch("dls_response_matrix.configuration.Config._machine_setup", return_value=3.0)
def test_get_configuration_returns_Config_with_correct_validation(
    mock_machine_setup, mock_check_limits
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
def test_get_configuration_returns_Config_with_isotime_if_filename_is_None(
    mock_machine_setup, mock_check_limits
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


def test_correctly_named_files_when_given_expected_args(tmp_path):
    config = configuration.Config(
        TEST_ISO_TIME,
        TEST_ISO_TIME,
        "reformatted",
        "I04",
        "SIM",
        100,
        3,
    )
    metadata = configuration.Metadata(config)
    metadata.write_json(tmp_path)
    foldername = f"RM-{config.iso_time}"
    file_list = os.listdir(os.path.join(tmp_path, foldername))
    metadata_file = [file for file in file_list if file.startswith("metadata")][0]
    assert str(metadata_file)[:8] == "metadata"


def test_fails_when_writing_json_if_missing_config():
    with pytest.raises(TypeError):
        configuration.Metadata()
