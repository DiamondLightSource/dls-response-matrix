"""lattice.py includes all classes and functions related to the lattice and the response-matrix process."""

import logging as log
from typing import List

import cothread
import numpy as np
import pytac

from dls_response_matrix.configuration import Config

MAX_BPM_ATTEMPTS = 3


class BeamPositionMonitorException(Exception):
    pass


class LatticeModel:
    """LatticeModel class stores all lattice data and functions."""

    def __init__(self, config: Config):
        """Initialising the lattice, HSTR, VSTR and BPM arrays."""
        self._config = config
        log.debug(f"Loading pytac lattice: {self._config.ring_mode}")
        self._lattice = pytac.load_csv.load(self._config.ring_mode)

        # Required to stop timeout on the machine.
        self._lattice._data_source_manager._data_sources[pytac.LIVE]._devices[
            "beam_current"
        ]._cs._timeout = 10.0

        self.hstr = self._lattice.get_elements("HSTR")
        self.vstr = self._lattice.get_elements("VSTR")
        self.bpm = self._lattice.get_elements("BPM")
        self.counter = 0.0

    def disable_correctors(self, remove_correctors: bool) -> List:
        """Removes disabled correctors from the hstr/vstr lists if required."""

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
        return [disabled_hstr_index, disabled_vstr_index]

    def disable_bpms(self, remove_bpms: bool) -> List:
        """Tracks disabled bpms for removal after measurement."""

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

    def calculate_responses(self, results, progress_callback):
        """Calls the response matrix on both HSTRs and VSTRs."""
        self.counter = 0
        log.info("Starting X axis response matrix.")
        self.calculate_axis_response(results, self.hstr, "x_kick", 0, progress_callback)
        log.info("Starting Y axis response matrix.")
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
