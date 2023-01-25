import logging as log
import os
from datetime import datetime

from cothread.catools import FORMAT_CTRL, caget

from dls_response_matrix.configuration import Config, Metadata
from dls_response_matrix.lattice import LatticeModel
from dls_response_matrix.results import Results

DEFAULT_MACHINE_MODE = "I04"

CONSOLE_LOG_FORMAT = "%(levelname)-7s: [%(filename)s:%(lineno)d] — %(message)s"
FILE_LOG_FORMAT = (
    "%(levelname)-7s: %(asctime)s — [%(filename)s:%(lineno)d] — %(message)s"
)


def get_ring_modes():  # Needed for UI initialisation.
    ring_mode_list = caget("SR-CS-RING-01:MODE", format=FORMAT_CTRL).enums
    current_ringmode = caget("SR-CS-RING-01:MODE", datatype=str)
    return ring_mode_list, current_ringmode


def get_new_logger(isotime):
    cwd = os.getcwd()
    foldername = f"RM-{isotime}"
    filename = "log.log"
    os.makedirs(os.path.join(cwd, foldername), exist_ok=True)

    logger = log.getLogger()
    logger.setLevel(log.NOTSET)

    # Console handler
    console_handler = log.StreamHandler()
    console_handler.setLevel(log.INFO)
    console_handler.setFormatter(log.Formatter(CONSOLE_LOG_FORMAT))
    logger.addHandler(console_handler)

    # File handler
    file_handler = log.FileHandler(os.path.join(cwd, foldername, filename))
    file_handler.setLevel(log.DEBUG)
    file_handler.setFormatter(log.Formatter(FILE_LOG_FORMAT))
    logger.addHandler(file_handler)


def response_matrix(
    filename: str,
    ring_mode: str,
    proposed_delta: float,
    pytac_unit: str,
    machine_type: str,
    remove_correctors: bool,
    remove_bpms: bool,
    split_graphs: bool,
    progress_callback=lambda x: None,
):
    """Response_matrix calculates the response matrix and times the process."""
    # Timing setup.
    start = datetime.now()
    iso_time = start.strftime("%Y%m%dT%H%M%S")
    get_new_logger(iso_time)

    # Config setup.
    config = Config.get_configuration(
        filename, iso_time, pytac_unit, ring_mode, machine_type, proposed_delta
    )

    # Metadata setup.
    metadata = Metadata(config)

    # Initialize model.
    lattice_model = LatticeModel(config)

    # Disable correctors and BPMs.
    metadata.disabled_correctors = lattice_model.disable_correctors(remove_correctors)
    disabled_bpms = lattice_model.disable_bpms(remove_bpms)
    metadata.disabled_bpms = disabled_bpms

    # Get initial values.
    metadata.initial = lattice_model.measure_correctors()

    # Save metadata.
    metadata.write_json()

    # Initialise the matrix
    results = Results.from_corrector_info(
        config, len(lattice_model.hstr), len(lattice_model.vstr), len(lattice_model.bpm)
    )

    # Calculate the response matrix.
    lattice_model.calculate_responses(results, progress_callback)

    # Remove BPMs that are not required.
    if remove_bpms:
        results.remove_bpms(disabled_bpms, len(lattice_model.bpm))

    results.write_csv()
    # Determine if a single or split matrix is required.
    # TODO: Add parsing for plot.
    split_plot = False
    if split_graphs:
        results.split()
        split_plot = True
    results.plot(split_plot)

    # Calculate the time taken.
    elapsed_time = (datetime.now() - start).total_seconds()
    print(f"Run in {elapsed_time} seconds")
