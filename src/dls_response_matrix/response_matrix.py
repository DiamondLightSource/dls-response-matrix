from __future__ import annotations

import errno
import logging as log
import os
from datetime import datetime

from cothread.catools import FORMAT_CTRL, ca_nothing, caget

from dls_response_matrix.configuration import Config, Metadata
from dls_response_matrix.lattice import LatticeModel
from dls_response_matrix.results import Results

ISO_TIME_FORMAT_STRING: str = "%Y%m%dT%H%M%S"
"""ISO 8601 in the format YYYYMMDDThhmmss. Note. T seperates date and time."""

DEFAULT_MACHINE_MODE: str = "I04"
"""Default machine ringmode."""

CONSOLE_LOG_FORMAT: str = "%(levelname)-7s: [%(filename)s:%(lineno)d] — %(message)s"
"""Logging formatting for console output."""

FILE_LOG_FORMAT: str = (
    "%(levelname)-7s: %(asctime)s — [%(filename)s:%(lineno)d] — %(message)s"
)

"""Logging formatting for file output."""


def get_ring_modes() -> tuple[list, str]:
    """Get the current and available ringmodes.
    This is required for UI initialisation.

    Returns:
        A tuple containing the list of ring modes, and the current ring mode.
    """
    try:
        ring_mode_list = caget(
            "SR-CS-RING-01:MODE", format=FORMAT_CTRL, throw=True
        ).enums
        current_ringmode = caget("SR-CS-RING-01:MODE", datatype=str, throw=True)
    except ca_nothing:
        ring_mode_list = [DEFAULT_MACHINE_MODE]
        current_ringmode = DEFAULT_MACHINE_MODE
        log.warning(
            f"Timeout while searching for PV SR-CS-RING-01:MODE. Using default "
            f"ring_mode {DEFAULT_MACHINE_MODE}"
        )
    return ring_mode_list, current_ringmode


def get_new_logger(
    filename: str,
    filepath: str,
    console_log_level: int = log.INFO,
    file_log_level: int = log.DEBUG,
):
    """Initialise and setup the logger.

    Setting up logging levels for console and file readout.

    Args:
        isotime: ISO 8601 time string.
        console_log_level : The minimum logging level to be returned in the console.
        file_log_level: The minimum logging level to be returned in the file.
    """
    foldername = f"RM-{filename}"
    full_path = os.path.join(filepath, foldername)
    file_log_name = "log.log"
    try:
        os.mkdir(full_path)
    except FileExistsError:
        pass

    logger = log.getLogger()
    logger.handlers.clear()
    logger.setLevel(log.NOTSET)
    # Console handler
    console_handler = log.StreamHandler()
    console_handler.setLevel(console_log_level)
    console_handler.setFormatter(log.Formatter(CONSOLE_LOG_FORMAT))
    logger.addHandler(console_handler)
    # File handler
    file_handler = log.FileHandler(os.path.join(full_path, file_log_name))
    file_handler.setLevel(file_log_level)
    file_handler.setFormatter(log.Formatter(FILE_LOG_FORMAT))
    logger.addHandler(file_handler)

    log.info(f"Saving data to: {full_path}")


def response_matrix(
    filename: str,
    filepath: str,
    ring_mode: str,
    proposed_delta: float,
    proposed_delay: float,
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
    iso_time = start.strftime(ISO_TIME_FORMAT_STRING)

    # Check filename and filepath are valid
    if filename is None:
        filename = iso_time
    log.info(f"Filename: {filename}, Iso Time: {iso_time}.")
    if filepath is None:
        filepath = os.getcwd()
    elif not os.path.isdir(filepath):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), filepath)

    get_new_logger(filename, filepath)

    # Config setup.
    config = Config.get_configuration(
        filename,
        filepath,
        iso_time,
        pytac_unit,
        ring_mode,
        machine_type,
        proposed_delta,
        proposed_delay,
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
