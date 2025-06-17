import os
from dataclasses import replace

import numpy as np
import pytest

from dls_response_matrix import configuration, lattice, results

config_sim_filename = "test"
config_sim_filepath = "./"
config_sim = configuration.Config(
    config_sim_filename,
    config_sim_filepath,
    "TEST_ISO_TIME",
    "reformatted",
    "I04",
    "SIM",
    0.01,
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
    config_sim.filepath = str(tmp_path)
    metadata = configuration.Metadata(config_sim)
    latticemodel = lattice.LatticeModel(config_sim)
    metadata.write_json()
    matrix = np.zeros(
        shape=(
            len(latticemodel.bpm) * 2,
            len(latticemodel.hstr) + len(latticemodel.vstr),
        )
    )
    result_old = results.Results(config_sim, matrix)
    result_old.write_csv()
    foldername = f"RM-{result_old._config.filename}"
    full_path = os.path.join(tmp_path, foldername)
    result_new = results.Results.from_csv(full_path, "NEW_FILENAME", tmp_path)
    assert result_new._filename == "NEW_FILENAME"
    assert result_new._filepath == tmp_path


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
    # Create initial Results data and directory from empty numpy array
    config_sim.filepath = str(tmp_path)
    metadata = configuration.Metadata(config_sim)
    latticemodel = lattice.LatticeModel(config_sim)
    metadata.write_json()
    matrix = np.zeros(
        shape=(
            len(latticemodel.bpm) * 2,
            len(latticemodel.hstr) + len(latticemodel.vstr),
        )
    )
    result_old = results.Results(config_sim, matrix)
    # Write initial Results data to csv
    result_old.write_csv()
    foldername = f"RM-{result_old._config.filename}"
    old_path = os.path.join(tmp_path, foldername)
    with pytest.raises(results.NewFilenameRequired):
        # Attempt to create new Results data and directory from the created csv file
        results.Results.from_csv(old_path, config_sim.filename, config_sim.filepath)


def test_from_csv_creates_new_Results_data_correctly(tmp_path):
    # Create initial Results data and directory from empty numpy array
    config_sim.filepath = str(tmp_path)
    metadata = configuration.Metadata(config_sim)
    latticemodel = lattice.LatticeModel(config_sim)
    metadata.write_json()
    matrix = np.zeros(
        shape=(
            len(latticemodel.bpm) * 2,
            len(latticemodel.hstr) + len(latticemodel.vstr),
        )
    )
    result_old = results.Results(config_sim, matrix)
    # Write initial Results data to csv
    result_old.write_csv()
    foldername = f"RM-{result_old._config.filename}"
    full_path = os.path.join(tmp_path, foldername)
     # Attempt to create new Results data and directory from the created csv file
    result_new = results.Results.from_csv(full_path, "New_Filename", tmp_path)
    assert result_new._filename != result_old._config.filename
    assert result_new._filepath != result_old._config.filepath

def test_splitting_of_old_results_data_into_new_filepath(tmp_path):
    # Create initial Results data and directory from empty numpy array
    config_sim.filepath = str(tmp_path)
    metadata = configuration.Metadata(config_sim)
    latticemodel = lattice.LatticeModel(config_sim)
    metadata.write_json()
    matrix = np.zeros(
        shape=(
            len(latticemodel.bpm) * 2,
            len(latticemodel.hstr) + len(latticemodel.vstr),
        )
    )
    result_old = results.Results(config_sim, matrix)
    # Write initial Results data to csv
    result_old.write_csv()
    foldername = f"RM-{result_old._config.filename}"
    full_path = os.path.join(tmp_path, foldername)
    new_filename = "New_Filename"
     # Attempt to create new Results data and directory from the created csv file
    result_new = results.Results.from_csv(full_path, new_filename, tmp_path)
    result_new.split()
    result_new.plot(split=True)
    for file in os.listdir(os.path.join(tmp_path, "RM-"+new_filename)):
        file_found=False
        # Look for one of the image plot files
        if ("plot-yCxB" in file):
            file_found = True
            break
    assert file_found
