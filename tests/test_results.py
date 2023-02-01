import os

import numpy as np

from dls_response_matrix import configuration, lattice, results

config_sim = configuration.Config(
    "FILENAME",
    "TEST_ISO_TIME",
    "reformatted",
    "I04",
    "SIM",
    100,
    3,
)


def test_results_init_from_corrector_info():
    latticemodel = lattice.LatticeModel(config_sim)
    result = results.Results.from_corrector_info(
        config_sim,
        len(latticemodel.hstr),
        len(latticemodel.vstr),
        len(latticemodel.bpm),
    )
    assert type(result._matrix) is np.ndarray


def test_results_init_from_csv(tmp_path):
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


def test_results_remove_bpms():
    pass
