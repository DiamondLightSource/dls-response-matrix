from __future__ import annotations

import json
import logging as log
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, NamedTuple, Optional

import cothread
import matplotlib.pyplot as plt
import numpy as np
import pytac
from cothread.catools import FORMAT_CTRL, caget
from matplotlib.colors import TwoSlopeNorm

ISO_TIME_FORMAT_STRING: str = "%Y%m%dT%H%M%S"
"""ISO 8601 in the format YYYYMMDDThhmmss. Note. T seperates date and time."""

DEFAULT_MACHINE_MODE: str = "I04"
"""Default machine ringmode."""

MAX_BPM_ATTEMPTS: int = 3
"""Maximum number of BPM connection attempts before failure."""

CONSOLE_LOG_FORMAT: str = "%(levelname)-7s: [%(filename)s:%(lineno)d] — %(message)s"
"""Logging formatting for console output."""
FILE_LOG_FORMAT: str = (
    "%(levelname)-7s: %(asctime)s — [%(filename)s:%(lineno)d] — %(message)s"
)
"""Logging formatting for file output."""

DeltaLimits: NamedTuple = NamedTuple(
    "DeltaLimits", [("max", float), ("min", float), ("default", float), ("pytac", str)]
)
"""The base structure containing information about the limits of delta."""
DELTA_LIMITS: dict = {
    "pytac.ENG": DeltaLimits(0.1, -0.1, 0.05, pytac.ENG),
    "pytac.PHYS": DeltaLimits(2.5e-5, -2.5e-5, 1e-5, pytac.PHYS),
}
"""Dictionary containing the completed information for ENG or PHYS units."""

MachineSetup: NamedTuple = NamedTuple(
    "MachineSetup", [("time_delay", float), ("port", str)]
)
"""The base structure containing the time delay and port."""
MACHINE_SETUP: dict = {
    "SIM": MachineSetup(1.2, "6064"),
    "LIVE": MachineSetup(0.25, "5054"),
}
"""Dictionary containing the completed information for the SIM or LIVE machine."""


def get_ring_modes() -> tuple[list, str]:
    """Get the current and available ringmodes.

    Returns:
        A tuple containing the list of ring modes, and the current ring mode.
    """
    ring_mode_list = caget("SR-CS-RING-01:MODE", format=FORMAT_CTRL).enums
    current_ringmode = caget("SR-CS-RING-01:MODE", datatype=str)
    return ring_mode_list, current_ringmode


def get_new_logger(
    isotime: str, console_log_level: int = log.INFO, file_log_level: int = log.DEBUG
):
    """Initialise and setup the logger.

    Setting up logging levels for console and file readout.

    Args:
        isotime: ISO 8601 time string.
        console_log_level : The minimum logging level to be returned in the console.
        file_log_level: The minimum logging level to be returned in the file.
    """
    cwd = os.getcwd()
    foldername = f"RM-{isotime}"
    filename = "log.log"
    try:
        os.mkdir(os.path.join(cwd, foldername))
    except FileExistsError:
        pass

    logger = log.getLogger()
    logger.setLevel(log.NOTSET)
    # Console handler
    console_handler = log.StreamHandler()
    console_handler.setLevel(console_log_level)
    console_handler.setFormatter(log.Formatter(CONSOLE_LOG_FORMAT))
    logger.addHandler(console_handler)
    # File handler
    file_handler = log.FileHandler(os.path.join(cwd, foldername, filename))
    file_handler.setLevel(file_log_level)
    file_handler.setFormatter(log.Formatter(FILE_LOG_FORMAT))
    logger.addHandler(file_handler)


@dataclass
class Config:
    """Config class stores commonly used configuration data."""

    filename: str = ""
    iso_time: str = ""
    pytac_unit: str = ""
    ring_mode: str = ""
    machine_type: str = ""
    delta: float = 0.0
    time_delay: float = 0.0

    @classmethod
    def get_configuration(
        cls,
        filename: str,
        iso_time: str,
        pytac_unit: str,
        ring_mode: str,
        machine_type: str,
        proposed_delta: float,
    ) -> Config:

        """Initialise the standard configuration object.

        Note:
            Should only be run once, before accessing cothread.catools.

        Args:
            filename: The filename prefix of the generated files. Defaults to the
                current ISO time.
            iso_time: ISO 8601 time.
            pytac_unit: The unit type as found in pytac.
            ring_mode: The name of the desired ringmode.
            machine_type: The machine type, either "SIM" for simulation or "LIVE"
                for the live machine.
            proposed_delta: The size of the proposed corrector step in
                pytac_units.

        Returns:
            The Config object.
        """
        if filename is None:
            filename = iso_time
        log.info(f"Filename: {filename}, Iso Time: {iso_time}.")

        delta, pytac_formatted = cls.check_limits(proposed_delta, pytac_unit)
        time_delay = cls.machine_setup(machine_type)
        return cls(
            filename,
            iso_time,
            pytac_formatted,
            ring_mode,
            machine_type,
            delta,
            time_delay,
        )

    @staticmethod
    def check_limits(proposed_delta: float, pytac_unit: str) -> tuple[float, str]:
        """Checks the proposed delta is within the approved limits.

        Args:
            proposed_delta: The size of the proposed corrector step in
                pytac_units.
            pytac_unit: The unit type as found in pytac.

        Raises:
            ValueError: If propsed_delta is outside of the range set my DELTA_LIMITS.

        Returns:
            Tuple[float, str]: A tuple of the approved corrector step and the
                formatted pytac string.
        """
        proposed_delta = float(proposed_delta)
        max_delta, min_delta, default_delta, pytac_formatted = DELTA_LIMITS[pytac_unit]

        try:
            if not (min_delta <= proposed_delta <= max_delta):
                raise ValueError(
                    f"Delta of {proposed_delta} is outside of acceptable range: [{min_delta}, {max_delta}]."
                )
        except ValueError as e:
            log.critical(e, exc_info=True)

        if proposed_delta == 0.0:
            return default_delta, pytac_formatted
        log.info(f"Delta: {proposed_delta}.")
        return proposed_delta, pytac_formatted

    @classmethod
    def machine_setup(cls, machine_type: str) -> float:
        """Set up time delay and port.

        Args:
            machine_type: The setup string of the machine, either SIM for
                simulation or LIVE for the live machine.

        Returns:
            The delay between each corrector step in seconds.
        """

        time_delay, port = MACHINE_SETUP[machine_type]
        cls.configure_port(port)
        return time_delay

    @staticmethod
    def configure_port(port: str):
        """Set up the Channel Access Port.

        Args:
            port: The port number.
        """

        os.environ["EPICS_CA_SERVER_PORT"] = port
        log.debug(f"'EPICS_CA_SERVER_PORT' set to {port}")


@dataclass
class Metadata:
    """The Metadata class includes the configuration and additional metadata for the process."""

    # Including the Config data.
    config: Config
    """config: The configuration for the process."""

    # Initial and disabled states.
    disabled_correctors: tuple[Sequence[Any], Sequence[Any]] = field(
        default_factory=lambda: (list(), list())
    )
    """disabled_correctors: Lattice indices of disabled correctors."""
    disabled_bpms: list[int] = field(default_factory=list)
    """disabled_bpms: Lattice indices of disabled BPMs."""
    initial: tuple[Sequence[Any], Sequence[Any]] = field(
        default_factory=lambda: (list(), list())
    )
    """initial: The initial setpoints of all correctors."""

    def write_json(self):
        """Write the metadata to a .json file."""
        log.info("Saving metadata .json.")
        dictionary = {
            # Main metadata.
            "Filename": self.config.filename,
            "ISO time": self.config.iso_time,
            "Ring Mode": self.config.ring_mode,
            "Machine type": self.config.machine_type,
            "Time delay": self.config.time_delay,
            "Delta": self.config.delta,
            "Pytac units": self.config.pytac_unit,
            # Disabled item elements. If the value is -1, then the item was not requested.
            "Disabled correctors (Python indices): X, Y": self.disabled_correctors,
            "Disabled BPMs (Python indices)": self.disabled_bpms,
            # The initial corrector values are for all correctors in the full lattice.
            "Initial HSTR, VSTR:": self.initial,
        }
        cwd = os.getcwd()
        foldername = f"RM-{self.config.iso_time}"
        filename = f"metadata-{self.config.filename}.json"
        try:
            os.mkdir(os.path.join(cwd, foldername))
        except FileExistsError:
            pass

        with open(
            f"{os.path.join(cwd, foldername, filename)}",
            "w",
        ) as outfile:
            json.dump(dictionary, outfile, indent=4, ensure_ascii=False)


class BeamPositionMonitorException(Exception):
    """Exception associated with recieving no response from BPMs."""

    pass


class LatticeModel:
    """LatticeModel class stores all lattice data and functions."""

    def __init__(self, config: Config):
        """Initialising the lattice, HSTR, VSTR and BPM arrays.

        Args:
            config: The configuration for the process.

        Attributes:
            hstr: All horizontal corrrector objects in the lattice.
            vstr: All vertical corrrector objects in the lattice.
            bpm: All beam position monitor objects in the lattice.
            counter: The progress through the process as an int. 1 = 0.5% of process.
        """

        self._config = config
        log.debug(f"Loading pytac lattice: {self._config.ring_mode}")
        self._lattice = pytac.load_csv.load(self._config.ring_mode)

        # Required to stop timeout on the machine.
        self._lattice._data_source_manager._data_sources[pytac.LIVE]._devices[
            "beam_current"
        ]._cs._timeout = 10.0

        self.hstr: list[pytac.element.EpicsElement] = self._lattice.get_elements("HSTR")
        self.vstr: list[pytac.element.EpicsElement] = self._lattice.get_elements("VSTR")
        self.bpm: list[pytac.element.EpicsElement] = self._lattice.get_elements("BPM")
        self.counter: float = 0.0

    def disable_correctors(
        self, remove_correctors: bool
    ) -> tuple[list[int], list[int]]:
        """Removes disabled correctors from the hstr and vstr lists.

        This will return -1 if remove_correctors = False, to clearly show a difference
        between the choice of not removing disabled elements and if no elements are
        disabled.

        Args:
            remove_correctors: If True, remove disabled correctors.

        Returns:
            A tuple containing lists for which correctors are disabled horizontally
                and vertically.
        """

        if remove_correctors:
            log.info("Removing disabled correctors")
            hstr_array = self._lattice.get_element_values("HSTR", "h_sofb_disabled")
            vstr_array = self._lattice.get_element_values("VSTR", "v_sofb_disabled")

            disabled_hstr_index = [
                index for index, element in enumerate(hstr_array) if element == 1.0
            ]
            disabled_vstr_index = [
                index for index, element in enumerate(vstr_array) if element == 1.0
            ]

            self.hstr = [
                element
                for index, element in enumerate(self.hstr)
                if index not in disabled_hstr_index
            ]
            self.vstr = [
                element
                for index, element in enumerate(self.vstr)
                if index not in disabled_vstr_index
            ]
        else:
            disabled_hstr_index, disabled_vstr_index = [-1], [-1]
        return disabled_hstr_index, disabled_vstr_index

    def disable_bpms(self, remove_bpms: bool) -> list[int]:
        """Removes disabled bpms from the hstr and vstr lists

        This will return -1 if remove_bpms = False, to clearly show a difference
        between the choice of not removing disabled elements and if no elements are
        disabled.

        Args:
            remove_bpms: If True, remove disabled BPMs.

        Returns:
            Returns a list of which BPMs are disabled.
        """

        if remove_bpms:
            log.info("Removing disabled bpms")
            self._bpm_inactive = self._lattice.get_element_values("BPM", "enabled")
            disabled_bpm_indices = [
                index
                for index, element in enumerate(self._bpm_inactive)
                if element == 0.0
            ]
        else:
            disabled_bpm_indices = [-1]
        return disabled_bpm_indices

    def measure_correctors(
        self,
    ) -> tuple[Sequence[Any], Sequence[Any]]:
        """Measures all corrector setpoints in the lattice.

        Returns:
            Horizontal and vertical corrector setpoints.
        """
        hstr_values = self._lattice.get_element_values(
            "HSTR", "x_kick", pytac.RB, self._config.pytac_unit
        )
        vstr_values = self._lattice.get_element_values(
            "VSTR", "y_kick", pytac.RB, self._config.pytac_unit
        )
        return hstr_values, vstr_values

    def measure_bpms(self) -> list:
        """Measures all bpms in the lattice.

        Measures all BPMs (even disabled) for performance requirements. Attempts
        to measure up to MAX_BPM_ATTEMPTS, due to recurring device issues.

        Raises:
            BeamPositionMonitorException: Failed to retrieve BPM values.

        Returns:
            Horizontal and vertical BPM values.
        """
        for attempt in range(1, MAX_BPM_ATTEMPTS + 1):
            try:
                bpm_x = self._lattice.get_element_values(
                    "BPM", "x", pytac.RB, self._config.pytac_unit
                )
                bpm_y = self._lattice.get_element_values(
                    "BPM", "y", pytac.RB, self._config.pytac_unit
                )
            except Exception as e:
                # TODO: except ca_nothing or ControlSystemException or Exception as e:
                log.error(f"Failure no: {attempt} to retrieve BPM values:\n{e}")
                if attempt < MAX_BPM_ATTEMPTS:
                    cothread.Sleep(1)
                    continue
                log.critical(
                    f"Failed to retrieve BPM values {MAX_BPM_ATTEMPTS} times:\n{e}"
                )
                raise BeamPositionMonitorException(
                    f"Failed to retrieve BPM values {MAX_BPM_ATTEMPTS} times:\n{e}"
                )
            else:
                break
        return bpm_x + bpm_y

    def calculate_responses(
        self,
        results: Results,
        progress_callback: Callable[[float], Optional[float]] = lambda x: None,
    ):
        """Runs the response matrix process on each axis seperately.

        Args:
            results: Results class object.
            progress_callback: The progress through the process as an int. 1 = 0.5% of process.
        """
        self.counter = 0
        log.info("Starting X axis response matrix.")
        self.calculate_axis_response(results, self.hstr, "x_kick", 0, progress_callback)
        log.info("Starting Y axis response matrix.")
        self.calculate_axis_response(
            results, self.vstr, "y_kick", len(self.hstr), progress_callback
        )

    def calculate_axis_response(
        self,
        results: Results,
        correctors: list,
        field: str,
        offset: int,
        progress_callback: Callable[[float], Optional[float]] = lambda x: None,
    ):
        """Calculates the response matrix for a given set of correctors, by stepping each corrector by delta and measuring the change in beam position.

        Args:
            results: A Results class object.
            correctors: A list of the corrector elements.
            field: The field on the correctors to change.
            offset: The offset for appending data to the matrix.
            progress_callback: The progress through the process as an int. 1 = 0.5% of process.
        """

        length = len(correctors)

        for index, corrector in enumerate(correctors):
            initial_bpm = self.measure_bpms()
            initial_corr_values = corrector.get_value(
                field, pytac.RB, self._config.pytac_unit
            )
            corrector.set_value(
                field,
                (initial_corr_values + self._config.delta),
                self._config.pytac_unit,
            )
            log.debug(f"Stepped {corrector.get_pv_name(field, pytac.RB)[:-2]}")
            # The sleeps ensure that the machine has settled/virtac has calculated changes.
            cothread.Sleep(self._config.time_delay)
            final_bpm = self.measure_bpms()
            corrector.set_value(field, initial_corr_values, self._config.pytac_unit)
            cothread.Sleep(self._config.time_delay)
            results.store(
                np.subtract(final_bpm, initial_bpm) / self._config.delta, offset + index
            )
            self.counter += 1 / length
            progress_callback(self.counter * 100)


class Results:
    """The Results class handles the data, providing functions to store, remove, save,
    split and plot."""

    def __init__(
        self, config: Config, matrix: np.ndarray, filepath: Optional[str] = None
    ):
        """Setup of the Results class.

        Args:
            config: A populated Config object.
            matrix: A matrix that contains a row for each BPM, and a
                column for each corrector magnet.
            filepath: An optional filepath to save the
                files to. Defaults to None.
        """
        self._config = config
        self._matrix = matrix
        self._filepath = filepath

    @classmethod
    def from_corrector_info(
        cls, config: Config, x_correctors: int, y_correctors: int, bpms: int
    ):
        """Creates a matrix of the appropriate size for the Results object.

        Args:
            config: A populated Config object.
            x_correctors: The number of horizontal correctors.
            y_correctors: The number of vertical correctors
            bpms: The number of BPMs.

        Returns:
            A Results object.
        """

        matrix: np.ndarray = np.zeros(shape=(2 * bpms, x_correctors + y_correctors))
        return cls(config, matrix)

    @classmethod
    def from_csv(
        cls,
        full_folderpath: str,
        new_filename: str,
    ):
        """Setup of the Results object when loading the files.

        Args:
            full_folderpath: The path to the folder with old data.
            new_filename: The new filename that newly generated files will have.

        Returns:
            A Results object.
        """
        file_list = os.listdir(full_folderpath)
        metadata_file = [file for file in file_list if file.startswith("metadata")][0]
        rawdata_file = [file for file in file_list if file.startswith("rawdata")][0]

        matrix = np.genfromtxt(os.path.join(full_folderpath, rawdata_file))
        with open(os.path.join(full_folderpath, metadata_file)) as f:
            metadata = json.load(f)

        config = Config(
            new_filename,
            metadata["ISO time"],
            metadata["Pytac units"],
            metadata["Ring Mode"],
            metadata["Machine type"],
            metadata["Delta"],
            metadata["Time delay"],
        )
        return cls(config, matrix, full_folderpath)

    def store(self, bpm_values: np.ndarray, index: int):
        """Store the BPM values in the correct index of the matrix.

        Args:
            bpm_values: The BPM values.
            index: The index of the BPM from which the values came.
        """
        self._matrix[:, index] = bpm_values

    def remove_bpms(self, disabled_bpms: list, x_bpms: int):
        """Removes inactive BPMs from the matrix.

        Args:
            disabled_bpms: The list of BPM indices to remove.
            x_bpms: The number of horizontal BPMs.
        """
        log.info("Removed inactive bpms.")
        # X bpms
        _disabled_bpm_list = [index for index in disabled_bpms]
        # Y bpms
        _disabled_bpm_list.extend([x_bpms + index for index in disabled_bpms])

        for index in _disabled_bpm_list[::-1]:
            self._matrix = np.delete(self._matrix, index, axis=0)

    def write_csv(self):
        """Write the matrix to a .csv."""
        log.info("Writing to data to a .csv.")

        cwd = self._filepath if self._filepath is not None else os.getcwd()
        foldername = f"RM-{self._config.iso_time}"
        filename = f"rawdata-full-{self._config.filename}.csv"

        np.savetxt(
            os.path.join(cwd, foldername, filename),
            self._matrix,
        )

    def plot(self, split: Optional[bool] = False):
        """Plots the matrix.

        Args:
            split: If the matrix is already split,
                then plot each quadrant seperately. Defaults to False.
        """
        cwd = self._filepath if self._filepath is not None else os.getcwd()
        foldername = f"RM-{self._config.iso_time}"

        if split:
            names = ["xCxB", "yCxB", "xCyB", "yCyB"]
        else:
            names = ["full"]
            matrix = self._matrix

        for plot_name in names:
            csv_filename = f"rawdata-{plot_name}-{self._config.filename}.csv"
            plot_filename = f"plot-{plot_name}-{self._config.filename}.png"
            matrix = np.genfromtxt(os.path.join(cwd, foldername, csv_filename))

            plt.imshow(matrix, "RdBu", norm=TwoSlopeNorm(vcenter=0))
            plt.xlim([-1, np.shape(matrix)[1]])
            plt.ylim([np.shape(matrix)[0], -1])
            plt.colorbar()
            plt.xlabel("Correctors")
            plt.ylabel("BPM")
            plt.title(f"Response Matrix {plot_name}: {self._config.iso_time}")
            plt.savefig(
                os.path.join(cwd, foldername, plot_filename),
                bbox_inches="tight",
                dpi=1200,
            )
            plt.close()

    def split(self):
        """Split the matrix up into quadrants and writes .csvs."""
        log.info("Splitting the matrix.")
        cwd = self._filepath if self._filepath is not None else os.getcwd()
        foldername = f"RM-{self._config.iso_time}"
        xCxB_filename = f"rawdata-xCxB-{self._config.filename}.csv"
        yCxB_filename = f"rawdata-yCxB-{self._config.filename}.csv"
        xCyB_filename = f"rawdata-xCyB-{self._config.filename}.csv"
        yCyB_filename = f"rawdata-yCyB-{self._config.filename}.csv"

        xCxB_yCxB, xCyB_yCyC = np.vsplit(self._matrix, 2)
        xCxB, yCxB = np.hsplit(xCxB_yCxB, 2)
        xCyB, yCyB = np.hsplit(xCyB_yCyC, 2)

        np.savetxt(
            os.path.join(cwd, foldername, xCxB_filename),
            xCxB,
        )
        np.savetxt(
            os.path.join(cwd, foldername, yCxB_filename),
            yCxB,
        )
        np.savetxt(
            os.path.join(cwd, foldername, xCyB_filename),
            xCyB,
        )
        np.savetxt(
            os.path.join(cwd, foldername, yCyB_filename),
            yCyB,
        )


def response_matrix(
    filename: str,
    ring_mode: str,
    proposed_delta: float,
    pytac_unit: str,
    machine_type: str,
    remove_correctors: bool,
    remove_bpms: bool,
    split_graphs: bool,
    progress_callback: Callable[[float], Optional[float]] = lambda x: None,
):
    """Calculates the response matrix and times the process.

    Args:
        filename: The given filename of the generated files.
        ring_mode: The name of the desired ringmode.
        proposed_delta: The size of the proposed corrector step in
                pytac_units.
        pytac_unit: Appropriately formatted pytac.ENG or pytac.PHYS string.
        machine_type: The setup string of the machine, either SIM for
                simulation or LIVE for the live machine.
        remove_correctors: If to remove disabled correctors.
        remove_bpms: If to remove disabled BPMs.
        split_graphs: If to split the response matrix into quadrants.
        progress_callback: The progress through the process as an int. 1 = 0.5% of process.
    """
    # Timing setup.
    start = datetime.now()
    iso_time = start.strftime(ISO_TIME_FORMAT_STRING)
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
