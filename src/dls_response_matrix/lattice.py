"""lattice.py includes all classes and functions related to the lattice
and the response-matrix process."""
from __future__ import annotations

import logging as log
from typing import Any, Callable, List, Optional, Sequence

import cothread
import numpy as np
import pytac
from pytac import cothread_cs
from pytac.exceptions import ControlSystemException

from dls_response_matrix.configuration import Config
from dls_response_matrix.results import Results

MAX_BPM_ATTEMPTS: int = 3
"""Maximum number of BPM connection attempts before failure."""


class BeamPositionMonitorException(Exception):
    """Exception associated with recieving no response from BPMs."""

    pass


class LatticeModel:
    """LatticeModel class stores all lattice data and functions."""

    def __init__(self, config: Config):
        """Initialise the lattice, HSTR, VSTR and BPM arrays.

        Args:
            config: The configuration for the process.

        Attributes:
            hstr: All horizontal corrrector objects in the lattice.
            vstr: All vertical corrrector objects in the lattice.
            bpm: All beam position monitor objects in the lattice.
            counter: The progress through the process as an int. 1 = 0.5% of process.
        """
        self._config: Config = config
        # Required to stop timout and to wait for caputs.
        _cs = cothread_cs.CothreadControlSystem(timeout=10.0, wait=True)

        log.debug(f"Loading pytac lattice: {self._config.ring_mode}")
        self._lattice = pytac.load_csv.load(self._config.ring_mode, _cs)

        self.hstr = self._lattice.get_elements("HSTR")
        self.vstr = self._lattice.get_elements("VSTR")
        self.bpm = self._lattice.get_elements("BPM")
        self.counter = 0.0

    def disable_correctors(
        self, remove_correctors: bool
    ) -> tuple[list[int], list[int]]:
        """Remove disabled correctors from the hstr and vstr lists.

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
            try:
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
            except ControlSystemException as e:
                raise ControlSystemException("Channel access request failed, is the slow_orbit_feedbacks IOC running?") from e
        else:
            disabled_hstr_index, disabled_vstr_index = [-1], [-1]
        return (disabled_hstr_index, disabled_vstr_index)

    def disable_bpms(self, remove_bpms: bool) -> List[int]:
        """Remove disabled bpms from the hstr and vstr lists

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

    def measure_correctors(self) -> tuple[Sequence[Any], Sequence[Any]]:
        """Measures all corrector setpoints in the lattice.

        Returns:
            Horizontal and vertical corrector setpoints.
        """
        # Only used to save the initial states as correctors are from the lattice,
        # not the enabled corrector lists.
        hstr_values = self._lattice.get_element_values(
            "HSTR", "x_kick", pytac.RB, self._config.pytac_unit
        )
        vstr_values = self._lattice.get_element_values(
            "VSTR", "y_kick", pytac.RB, self._config.pytac_unit
        )
        return (hstr_values, vstr_values)

    def measure_bpms(self) -> List:
        """Measure all bpms in the lattice.

        Measure all BPMs (even disabled) for performance requirements. Attempts
        to measure up to MAX_BPM_ATTEMPTS, due to recurring device issues.

        Raises:
            BeamPositionMonitorException: Failed to retrieve BPM values.

        Returns:
            Horizontal and vertical BPM values.
        """
        # Measures all BPMs (even disabled) for performance requirements.
        # Repeat CA requests for BPMs due to recurring device issues
        for attempt in range(1, MAX_BPM_ATTEMPTS + 1):
            try:
                bpm_x = self._lattice.get_element_values(
                    "BPM", "x", pytac.RB, self._config.pytac_unit
                )
                bpm_y = self._lattice.get_element_values(
                    "BPM", "y", pytac.RB, self._config.pytac_unit
                )
            except Exception as e:
                # except ca_nothing or ControlSystemException or Exception as e:
                log.error(f"Failure no: {attempt} to retrieve bpm values:\n{e}")
                if attempt < MAX_BPM_ATTEMPTS:
                    cothread.Sleep(1)
                    continue
                log.critical(
                    f"Failed to retrieve bpm values {MAX_BPM_ATTEMPTS} times:\n{e}"
                )
                raise BeamPositionMonitorException(
                    f"Failed to retrieve bpm values {MAX_BPM_ATTEMPTS} times:\n{e}"
                )
            else:
                break
        return bpm_x + bpm_y

    def calculate_responses(
        self,
        results: Results,
        progress_callback: Callable[[float], Optional[float]] = lambda x: None,
    ):
        """Run the response matrix process on each axis separately.

        Args:
            results: Results class object.
            progress_callback: The progress through the process as an int. 1 = 0.5%
                of process.
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
        """Calculate the response matrix for a given set of correctors, by stepping
        each corrector by delta and measuring the change in beam position.

        Args:
            results: A Results class object.
            correctors: A list of the corrector elements.
            field: The field on the correctors to change.
            offset: The offset for appending data to the matrix.
            progress_callback: The progress through the process as an int. 1 = 0.5%
                of process.
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
            # The sleeps ensure that the machine has settled/virtac has
            # calculated changes.
            cothread.Sleep(self._config.time_delay)
            final_bpm = self.measure_bpms()
            corrector.set_value(field, initial_corr_values, self._config.pytac_unit)
            cothread.Sleep(self._config.time_delay)
            results.store(
                np.subtract(final_bpm, initial_bpm) / self._config.delta, offset + index
            )
            self.counter += 1 / length
            progress_callback(self.counter * 100)
