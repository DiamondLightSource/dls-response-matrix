import os
from dataclasses import replace

import numpy as np
import pytest

from dls_response_matrix import configuration, lattice, results

config_sim_filename = "FILENAME"
config_sim = configuration.Config(
    config_sim_filename,
    "TEST_ISO_TIME",
    "reformatted",
    "I04",
    "SIM",
    100,
    3,
)


def test_results_initialised_from_corrector_info():
    latticemodel = lattice.LatticeModel(config_sim)
    result = results.Results.from_corrector_info(
        config_sim,
        len(latticemodel.hstr),
        len(latticemodel.vstr),
        len(latticemodel.bpm),
    )
    assert type(result._matrix) is np.ndarray


def test_results_initialised_from_csv(tmp_path):
    metadata = configuration.Metadata(config_sim)
    latticemodel = lattice.LatticeModel(config_sim)
    metadata.write_json(tmp_path)
    matrix = np.zeros(
        shape=(
            len(latticemodel.bpm) * 2,
            len(latticemodel.hstr) + len(latticemodel.vstr),
        )
    )
    result_old = results.Results(config_sim, matrix, tmp_path)
    result_old.write_csv()
    foldername = f"RM-{result_old._config.iso_time}"
    full_path = os.path.join(tmp_path, foldername)
    result_new = results.Results.from_csv(full_path, "NEW_FILENAME")
    assert result_new._config.filename == "NEW_FILENAME"


def test_results_remove_bpms_works_as_expected():
    latticemodel = lattice.LatticeModel(config_sim)
    result = results.Results.from_corrector_info(
        config_sim,
        len(latticemodel.hstr),
        len(latticemodel.vstr),
        len(latticemodel.bpm),
    )
    number = 20
    start_x, start_y = np.shape(result._matrix)
    disabled_bpms = sorted(
        np.random.randint(0, high=len(latticemodel.bpm), size=number)
    )
    result.remove_bpms(disabled_bpms, len(latticemodel.bpm))
    assert np.shape(result._matrix) == (start_x - (number * 2), start_y)


def test_from_csv_raises_exception_if_new_filename_same_as_old_filename(tmp_path):
    metadata = configuration.Metadata(config_sim)
    latticemodel = lattice.LatticeModel(config_sim)
    metadata.write_json(tmp_path)
    matrix = np.zeros(
        shape=(
            len(latticemodel.bpm) * 2,
            len(latticemodel.hstr) + len(latticemodel.vstr),
        )
    )
    result_old = results.Results(config_sim, matrix, tmp_path)
    result_old.write_csv()
    foldername = f"RM-{result_old._config.iso_time}"
    full_path = os.path.join(tmp_path, foldername)
    with pytest.raises(results.NewFilenameRequired):
        results.Results.from_csv(full_path, config_sim.filename)


def test_from_csv_returns_results_if_new_filename_different_to_old_filename(tmp_path):
    metadata = configuration.Metadata(config_sim)
    latticemodel = lattice.LatticeModel(config_sim)
    metadata.write_json(tmp_path)
    matrix = np.zeros(
        shape=(
            len(latticemodel.bpm) * 2,
            len(latticemodel.hstr) + len(latticemodel.vstr),
        )
    )
    result_old = results.Results(config_sim, matrix, tmp_path)
    result_old.write_csv()
    foldername = f"RM-{result_old._config.iso_time}"
    full_path = os.path.join(tmp_path, foldername)
    result_new = results.Results.from_csv(full_path, "New_Filename")
    assert result_new._config.filename != result_old._config.filename
    assert (
        replace(result_new._config, filename=config_sim_filename) == result_old._config
    )
