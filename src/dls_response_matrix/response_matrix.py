import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, NamedTuple, Tuple

import cothread
import matplotlib.pyplot as plt
import numpy as np
import pytac
from cothread.catools import FORMAT_CTRL, ca_nothing, caget
from matplotlib.colors import TwoSlopeNorm

DEFAULT_MACHINE_MODE = "I04"
MAX_BPM_ATTEMPTS = 3

DeltaLimits = NamedTuple(
    "DeltaLimits", [("max", float), ("min", float), ("default", float), ("pytac", str)]
)
DELTA_LIMITS = {
    "pytac.ENG": DeltaLimits(0.1, -0.1, 0.05, pytac.ENG),
    "pytac.PHYS": DeltaLimits(2.5e-5, -2.5e-5, 1e-5, pytac.PHYS),
}

MachineSetup = NamedTuple("MachineSetup", [("time_delay", float), ("port", str)])
MACHINE_SETUP = {
    "SIM": MachineSetup(1.2, "6064"),
    "LIVE": MachineSetup(0.25, "5054"),
}


def get_ring_modes():  # Needed for UI initialisation.
    res = caget("SR-CS-RING-01:MODE", format=FORMAT_CTRL)
    cur = caget("SR-CS-RING-01:MODE", datatype=str)
    return res.enums, cur


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
    ):
        """Get the standard configuration object.

        Should only be run once and before accessing catools.
        """
        # If no filename is provided, defaults to ISO time.
        if filename is None:
            filename = iso_time

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
    def check_limits(proposed_delta: float, pytac_unit: str) -> Tuple[float, str]:
        """Checks the limits and sets delta."""
        proposed_delta = float(proposed_delta)
        max_delta, min_delta, default_delta, pytac_formatted = DELTA_LIMITS[pytac_unit]

        if not (min_delta <= proposed_delta <= max_delta):
            raise ValueError(
                f"Delta of {proposed_delta} is outside of acceptable range: [{min_delta}, {max_delta}]."
            )

        if proposed_delta == 0.0:
            return default_delta, pytac_formatted
        return proposed_delta, pytac_formatted

    @classmethod
    def machine_setup(cls, machine_type: str) -> float:
        """Sets up the time delay for corrector stepping"""

        time_delay, port = MACHINE_SETUP[machine_type]
        cls.configure_port(port)
        return time_delay

    @staticmethod
    def configure_port(port: str):
        """Configures the port"""

        os.environ["EPICS_CA_SERVER_PORT"] = port


@dataclass
class Metadata:
    """Metadata class stores all configuration data and provides a function to write this data to a .json file."""

    # Including the Config data.
    config: Config

    # Initial and disabled states.
    disabled_correctors: List[int] = field(default_factory=list)
    disabled_bpms: List[int] = field(default_factory=list)
    initial: List[float] = field(default_factory=list)

    def write_json(self):
        """This function writes the metadata to a .json file."""
        dictionary = {
            # Main metadata.
            "Filename": self.config.filename,
            "ISO time": self.config.iso_time,
            "Lattice model:": self.config.ring_mode,
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
        with open(f"RM-{self.config.filename}-metadata.json", "w") as outfile:
            json.dump(dictionary, outfile, indent=4, ensure_ascii=False)


class LatticeModel:
    """LatticeModel class stores all lattice data and functions."""

    def __init__(self, config: Config):
        """Initialising the lattice, HSTR, VSTR and BPM arrays."""
        self._config = config
        self._lattice = pytac.load_csv.load(self._config.ring_mode)

        # Required to stop timeout on the machine.
        self._lattice._data_source_manager._data_sources[pytac.LIVE]._devices[
            "beam_current"
        ]._cs._timeout = 5.0

        self.hstr = self._lattice.get_elements("HSTR")
        self.vstr = self._lattice.get_elements("VSTR")
        self.bpm = self._lattice.get_elements("BPM")
        self.counter = 0.0

    def disable_correctors(self, remove_correctors: bool) -> List:
        """Removes disabled correctors from the hstr/vstr lists if required."""

        if remove_correctors:
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
        return [disabled_hstr_index, disabled_vstr_index]

    def disable_bpms(self, remove_bpms: bool) -> List:
        """Tracks disabled bpms for removal after measurement."""

        if remove_bpms:
            self._bpm_inactive = self._lattice.get_element_values("BPM", "enabled")
            disabled_bpm_indices = [
                index
                for index, element in enumerate(self._bpm_inactive)
                if element == 0.0
            ]
        else:
            disabled_bpm_indices = [-1]
        return disabled_bpm_indices

    def measure_correctors(self):
        """Measures all correctors in the lattice."""
        # Only used to save the initial states as correctors are from the lattice, not the enabled corrector lists.
        hstr_values = self._lattice.get_element_values(
            "HSTR", "x_kick", pytac.RB, self._config.pytac_unit
        )
        vstr_values = self._lattice.get_element_values(
            "VSTR", "y_kick", pytac.RB, self._config.pytac_unit
        )
        return [hstr_values, vstr_values]

    def measure_bpms(self):
        """Measures all bpms in the lattice."""
        # Measures all BPMs (even disabled) for performance requirements.
        # The try statement is to guard against caget failures.
        bpm_x = self._lattice.get_element_values(
            "BPM", "x", pytac.RB, self._config.pytac_unit
        )
        bpm_y = self._lattice.get_element_values(
            "BPM", "y", pytac.RB, self._config.pytac_unit
        )

        for attempt in range(MAX_BPM_ATTEMPTS):
            try:
                bpm_x = self._lattice.get_element_values(
                    "BPM", "x", pytac.RB, self._config.pytac_unit
                )
                bpm_y = self._lattice.get_element_values(
                    "BPM", "y", pytac.RB, self._config.pytac_unit
                )
            except ca_nothing as e:
                print(f"Failure no: {attempt + 1} to retrieve bpm values:\n{e}")
                # log.error(f"Failure no: {attempt + 1} to retrieve bpm values:\n{e}")
                if attempt < MAX_BPM_ATTEMPTS - 1:
                    cothread.Sleep(1)
                    continue
                print(f"Failed to retrieve bpm values {MAX_BPM_ATTEMPTS} times:\n{e}")
                # log.critical(f"Failed to retrieve bpm values {MAX_BPM_ATTEMPTS} times:\n{e}")
                raise Exception(
                    f"Failed to retrieve bpm values {MAX_BPM_ATTEMPTS} times:\n{e}"
                )
            else:
                break
        return bpm_x + bpm_y

    def calculate_responses(self, results, progress_callback):
        """Calls the response matrix on both HSTRs and VSTRs."""
        self.calculate_axis_response(results, self.hstr, "x_kick", 0, progress_callback)
        self.calculate_axis_response(
            results, self.vstr, "y_kick", len(self.hstr), progress_callback
        )

    def calculate_axis_response(
        self, results, correctors: list, field: str, offset: int, progress_callback
    ):
        """Calculates the response matrix for a given set of correctors, by stepping each corrector by delta and measuring the change in beam position.

        Arguments:
            correctors: A list of the corrector elements.
            field: The field on the correctors to change.
            offset: The offset for appending data to the matrix.
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
    """The Results class handles the data, providing functions to store, remove, save, split and plot."""

    def __init__(self, config: Config, x_correctors: int, y_correctors: int, bpms: int):
        """Initializes the np.ndarray to the right shape."""

        self._config = config
        self._matrix: np.ndarray = np.zeros(
            shape=(2 * bpms, x_correctors + y_correctors)
        )

    def store(self, bpm_values: list, index: int):
        """Stores the data in the correct index of the matrix."""
        self._matrix[:, index] = bpm_values

    def remove_bpms(self, disabled_bpms: list, x_bpms: int):
        """Removes inactive bpm rows from the matrix."""
        # X bpms
        _disabled_bpm_list = [index for index in disabled_bpms]
        # Y bpms
        _disabled_bpm_list.extend([x_bpms + index for index in disabled_bpms])

        for index in _disabled_bpm_list[::-1]:
            self._matrix = np.delete(self._matrix, index, axis=0)

    def write_csv(self):
        """Writes the matrix to a .csv."""

        np.savetxt(f"RM-{self._config.filename}.csv", self._matrix)

    def plot(self):
        """Plots the matrix."""

        plt.imshow(self._matrix, "RdBu", norm=TwoSlopeNorm(vcenter=0))
        plt.xlim([-1, np.shape(self._matrix)[1]])
        plt.ylim([np.shape(self._matrix)[0], -1])
        plt.colorbar()
        plt.xlabel("Correctors")
        plt.ylabel("BPM")
        plt.title(f"Response Matrix: {self._config.iso_time}")
        plt.savefig(f"RM-{self._config.filename}.png", bbox_inches="tight", dpi=1200)

    def split(self):
        """Splits the matrix up into quadrants and writes .csvs."""

        xCxB_yCxB, xCyB_yCyC = np.vsplit(self._matrix, 2)
        xCxB, yCxB = np.hsplit(xCxB_yCxB, 2)
        xCyB, yCyB = np.hsplit(xCyB_yCyC, 2)

        np.savetxt(f"RM-xCxB-{self._config.filename}.csv", xCxB)
        np.savetxt(f"RM-yCxB-{self._config.filename}.csv", yCxB)
        np.savetxt(f"RM-xCyB-{self._config.filename}.csv", xCyB)
        np.savetxt(f"RM-yCyB-{self._config.filename}.csv", yCyB)


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
    iso_name = start.strftime("%Y%m%dT%H%M%S")

    # Config setup.
    config = Config.get_configuration(
        filename, iso_name, pytac_unit, ring_mode, machine_type, proposed_delta
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
    results = Results(
        config, len(lattice_model.hstr), len(lattice_model.vstr), len(lattice_model.bpm)
    )

    # Calculate the response matrix.
    lattice_model.calculate_responses(results, progress_callback)

    # Remove BPMs that are not required.
    if remove_bpms:
        results.remove_bpms(disabled_bpms, len(lattice_model.bpm))

    # Determine if a single or split matrix is required.
    if split_graphs:
        results.split()
    else:
        results.write_csv()
    results.plot()

    # Calculate the time taken.
    elapsed_time = (datetime.now() - start).total_seconds()
    print(f"Run in {elapsed_time} seconds")
