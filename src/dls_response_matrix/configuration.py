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
    "MachineSetup",
    [
        ("max_time_delay", float),
        ("min_time_delay", float),
        ("default_time_delay", float),
        ("port", str),
    ],
)
"""The base structure containing the time delay and port."""
MACHINE_SETUP: dict = {
    "SIM": MachineSetup(5, 0.5, 0.5, "8064"),
    "LIVE": MachineSetup(1, 0.1, 0.25, "5064"),
}
"""Dictionary containing the completed information for the SIM or LIVE machine."""


@dataclass
class Config:
    """Config class stores commonly used configuration data."""

    filename: str = ""
    filepath: str = ""
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
        filepath: str,
        iso_time: str,
        pytac_unit: str,
        ring_mode: str,
        machine_type: str,
        proposed_delta: float,
        proposed_delay: float,
    ):
        """Initialise the standard configuration object.

        Note:
            Should only be run once, before accessing cothread.catools.

        Args:
            filename: The filename prefix of the generated files. Defaults to the
                current ISO time.
            filepath: The path to the directory to save the data. Defaults to the
                python module top directory.
            pytac_unit: The unit type as found in pytac.
            ring_mode: The name of the desired ringmode.
            machine_type: The machine type, either "SIM" for simulation or "LIVE"
                for the live machine.
            proposed_delta: The size of the proposed corrector step in
                pytac_units.

        Returns:
            The Config object.
        """
        delta, pytac_formatted = cls._check_limits(proposed_delta, pytac_unit)
        time_delay = cls._machine_setup(proposed_delay, machine_type)
        return cls(
            filename,
            filepath,
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
            log.info(f"Using default delta: {delta_limits.default}.")
            return delta_limits.default, delta_limits.pytac

        log.info(f"Using delta: {proposed_delta}.")
        return proposed_delta, delta_limits.pytac

    @classmethod
    def _machine_setup(cls, proposed_delay: float, machine_type: str) -> float:
        """Set up time delay and port.

        Args:
            machine_type: The setup string of the machine, either SIM for
                simulation or LIVE for the live machine.

        Returns:
            The delay between each corrector step in seconds.
        """
        max, min, default, expected_port = MACHINE_SETUP[machine_type]
        if proposed_delay is None:
            time_delay = default
            log.info(f"Setting step delay to default {default}")
        elif proposed_delay > max or proposed_delay < min:
            raise ValueError(
                f"User requested time delay {proposed_delay} is out of "
                f"allowed range: {min}-{max} seconds"
            )
        else:
            time_delay = proposed_delay
            log.info(f"Setting step delay to {proposed_delay}")
        cls._check_CA_ports(machine_type)
        return time_delay

    @staticmethod
    def _check_CA_ports(machine_type: str):
        """Set up the Channel Access Port.

        Args:
            port: The port number.
        """
        expected_ca_addr_port = MACHINE_SETUP[machine_type][3]
        try:
            server_port = os.environ["EPICS_CA_SERVER_PORT"]
            repeater_port = os.environ["EPICS_CA_REPEATER_PORT"]
            if machine_type != "LIVE" and server_port == str(5064):
                raise ValueError(
                    "CA server port set to 5064, but machine_type is not LIVE. "
                    "Only use port 5064 when running against the LIVE machine"
                )
            if machine_type != "LIVE" and repeater_port == str(5065):
                raise ValueError(
                    "CA server port set to 5064, but machine_type is not LIVE. "
                    "Only use port 5064 when running against the LIVE machine"
                )
            if machine_type == "SIM" and server_port != expected_ca_addr_port:
                log.warning(
                    f"VIRTAC simulation is normally done on CA port {expected_ca_addr_port}, "
                    f"but your CA server port is set to {server_port}. Is this okay?"
                )
            if machine_type == "SIM" and repeater_port != str(
                int(expected_ca_addr_port) + 1
            ):
                log.warning(
                    f"VIRTAC simulation is normally done on CA port {str(int(expected_ca_addr_port) + 1)}, "
                    f"but your CA repeater port is set to {repeater_port}. Is this okay?"
                )
        except KeyError as e:
            raise ValueError("EPICS CA variables not set!") from e
        log.info(f"Using 'EPICS_CA_SERVER_PORT' {server_port}")
        log.info(f"Using 'EPICS_CA_REPEATER_PORT' {repeater_port}")


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

    def write_json(self):
        """Write the metadata to a .json file.

        Args:
            folderpath: An optional folderpath to save the json to.
        """
        log.info("Saving metadata .json.")
        dictionary = {
            # Main metadata.
            "Filename": self.config.filename,
            "Filepath": self.config.filepath,
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

        cwd = self.config.filepath if self.config.filepath is not None else os.getcwd()
        foldername = f"RM-{self.config.filename}"
        filename = f"metadata-{self.config.filename}.json"

        os.makedirs(os.path.join(cwd, foldername), exist_ok=True)

        with open(
            f"{os.path.join(cwd, foldername, filename)}",
            "w",
        ) as outfile:
            json.dump(dictionary, outfile, indent=4, ensure_ascii=False)
