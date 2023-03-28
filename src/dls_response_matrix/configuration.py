"""configuration.py includes all classes and functions related to Config and Metadata."""

import json
import logging as log
import os
from dataclasses import dataclass, field
from typing import List, NamedTuple, Tuple

import pytac

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
        log.info(f"Filename: {filename}, Iso Time: {iso_time}.")

        delta, pytac_formatted = cls._check_limits(proposed_delta, pytac_unit)
        time_delay = cls._machine_setup(machine_type)
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
    def _check_limits(proposed_delta: float, pytac_unit: str) -> Tuple[float, str]:
        """Checks the limits and sets delta."""
        proposed_delta = float(proposed_delta)
        max_delta, min_delta, default_delta, pytac_formatted = DELTA_LIMITS[pytac_unit]

        if not (min_delta <= proposed_delta <= max_delta):
            raise ValueError(
                f"Delta of {proposed_delta} is outside of acceptable range: [{min_delta}, {max_delta}]."
            )

        if proposed_delta == 0.0:
            return default_delta, pytac_formatted
        log.info(f"Delta: {proposed_delta}.")
        return proposed_delta, pytac_formatted

    @classmethod
    def _machine_setup(cls, machine_type: str) -> float:
        """Sets up the time delay for corrector stepping"""

        time_delay, port = MACHINE_SETUP[machine_type]
        cls._configure_port(port)
        return time_delay

    @staticmethod
    def _configure_port(port: str):
        """Configures the port"""

        os.environ["EPICS_CA_SERVER_PORT"] = port
        log.debug(f"'EPICS_CA_SERVER_PORT' set to {port}")


@dataclass
class Metadata:
    """Metadata class stores all configuration data and provides a function to write this data to a .json file."""

    # Including the Config data.
    config: Config

    # Initial and disabled states.
    disabled_correctors: List[List[int]] = field(default_factory=list)
    disabled_bpms: List[int] = field(default_factory=list)
    initial: List[List[float]] = field(default_factory=list)

    def write_json(self, folderpath=None):
        """This function writes the metadata to a .json file."""
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

        cwd = os.getcwd() if folderpath is None else folderpath
        foldername = f"RM-{self.config.iso_time}"
        filename = f"metadata-{self.config.filename}.json"

        os.makedirs(os.path.join(cwd, foldername), exist_ok=True)

        with open(
            f"{os.path.join(cwd, foldername, filename)}",
            "w",
        ) as outfile:
            json.dump(dictionary, outfile, indent=4, ensure_ascii=False)
