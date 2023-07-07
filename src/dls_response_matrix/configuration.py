"""configuration.py includes all classes and functions related to
Config and Metadata."""
from __future__ import annotations

import json
import logging as log
import os
from dataclasses import dataclass, field
from typing import Any, NamedTuple, Optional, Sequence, Tuple

import pytac

DeltaLimits: NamedTuple = NamedTuple(
    "DeltaLimits", [("max", float), ("min", float), ("default", float), ("pytac", str)]
)
"""The base structure containing information about the limits of delta."""
DELTA_LIMITS = {
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
        """Check the proposed delta is within the approved limits.

        Args:
            proposed_delta: The size of the proposed corrector step in
                pytac_units.
            pytac_unit: The unit type as found in pytac.

        Raises:
            ValueError: If propsed_delta is outside of the range set my DELTA_LIMITS.

        Returns:
            Tuple[float, str]: A tuple of the approved corrector step and the
                unit in the pytac format.
        """
        proposed_delta = float(proposed_delta)
        delta_limits = DELTA_LIMITS[pytac_unit]

        if not (delta_limits.min <= proposed_delta <= delta_limits.max):
            raise ValueError(
                f"Delta of {proposed_delta} is outside of acceptable range: "
                f"[{delta_limits.min}, {delta_limits.max}]."
            )

        if proposed_delta == 0.0:
            return delta_limits.default, delta_limits.pytac
        log.info(f"Delta: {proposed_delta}.")
        return proposed_delta, delta_limits.pytac

    @classmethod
    def _machine_setup(cls, machine_type: str) -> float:
        """Set up time delay and port.

        Args:
            machine_type: The setup string of the machine, either SIM for
                simulation or LIVE for the live machine.

        Returns:
            The delay between each corrector step in seconds.
        """
        time_delay, port = MACHINE_SETUP[machine_type]
        cls._configure_port(port)
        return time_delay

    @staticmethod
    def _configure_port(port: str):
        """Set up the Channel Access Port.

        Args:
            port: The port number.
        """
        os.environ["EPICS_CA_SERVER_PORT"] = port
        log.debug(f"'EPICS_CA_SERVER_PORT' set to {port}")


@dataclass
class Metadata:
    """Metadata class stores all configuration data and provides a function to write
    this data to a .json file."""

    # Including the Config data.
    config: Config
    """config: The configuration for the process."""

    # Initial and disabled states.
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

    def write_json(self, folderpath: Optional[str] = None):
        """Write the metadata to a .json file.

        Args:
            folderpath: An optional folderpath to save the json to.
        """
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
            # Disabled item elements. If the value is -1,
            # then the item was not requested.
            "Disabled correctors (Python indices): X, Y": self.disabled_correctors,
            "Disabled BPMs (Python indices)": self.disabled_bpms,
            # The initial corrector values are for all correctors in the full lattice.
            "Initial HSTR, VSTR:": self.initial,
        }

        cwd = os.getcwd() if folderpath is None else folderpath
        foldername = f"RM-{self.config.iso_time}"
        filename = f"metadata-{self.config.filename}.json"

        os.makedirs(os.path.join(cwd, foldername))

        with open(
            f"{os.path.join(cwd, foldername, filename)}",
            "w",
        ) as outfile:
            json.dump(dictionary, outfile, indent=4, ensure_ascii=False)
