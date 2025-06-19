from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import cothread
from PyQt6 import uic
from PyQt6.QtWidgets import QFileDialog, QMainWindow

from dls_response_matrix.configuration import DELTA_LIMITS, MACHINE_SETUP
from dls_response_matrix.response_matrix import (
    DEFAULT_MACHINE_MODE,
    get_ring_modes,
    response_matrix,
)

_qapp = cothread.iqt()

UI_FILENAME = Path(__file__).parent / "responsematrix.ui"


@dataclass
class Definitions:
    filename: str = None  # type: ignore
    filepath: str = None  # type: ignore
    ring_mode: str = DEFAULT_MACHINE_MODE
    machine_type: str = "SIM"
    pytac_unit: str = "pytac.ENG"
    proposed_delta: float = 0.0
    proposed_delay: float = 0.5
    remove_correctors: bool = False
    remove_bpms: bool = False
    split_graphs: bool = False


class MainWindow(QMainWindow):
    def __init__(self, tooltips, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(UI_FILENAME, self)

        self.filename_input.setToolTip(tooltips["filename"])
        self.filepath_input.setToolTip(tooltips["filepath"])
        self.file_browser.clicked.connect(self.open_file_dialog)
        self.ring_mode_input.setToolTip(tooltips["ring-mode"])
        self.proposed_delta_input.setToolTip(tooltips["proposed-delta"])
        self.proposed_delay_input.setToolTip(tooltips["proposed-delay"])
        self.pytac_unit_input.setToolTip(tooltips["pytac-unit"])
        self.machine_type_input.setToolTip(tooltips["machine-type"])
        self.corrector_input.setToolTip(tooltips["remove-correctors"])
        self.bpm_input.setToolTip(tooltips["remove-bpms"])
        self.split_input.setToolTip(tooltips["split-graphs"])

        ring_modes, current_ring_mode = get_ring_modes()
        self.ring_mode_input.addItems(ring_modes)
        self.ring_mode_input.setCurrentText(current_ring_mode)
        self.set_limits()
        self.pytac_unit_input.activated.connect(lambda: self.set_limits())
        self.machine_type_input.activated.connect(lambda: self.set_limits())
        self.start_button.clicked.connect(self.button_pressed)

    def get_current_args(self):
        return Definitions(
            filename=self.filename_input.text(),
            filepath=self.filepath_input.text(),
            ring_mode=self.ring_mode_input.currentText(),
            machine_type=self.machine_type_input.currentText(),
            pytac_unit=self.pytac_unit_input.currentText(),
            proposed_delta=self.proposed_delta_input.value(),
            proposed_delay=self.proposed_delay_input.value(),
            remove_correctors=self.corrector_input.isChecked(),
            remove_bpms=self.bpm_input.isChecked(),
            split_graphs=self.split_input.isChecked(),
        )

    def set_limits(self):
        maximum, minimum, default, name = DELTA_LIMITS[
            self.pytac_unit_input.currentText()
        ]
        self.proposed_delta_input.setMaximum(maximum)
        self.proposed_delta_input.setMinimum(minimum)
        self.proposed_delta_input.setValue(default)
        self.proposed_delta_input.setSingleStep(0.1)

        maximum, minimum, default, port = MACHINE_SETUP[
            self.machine_type_input.currentText()
        ]
        self.proposed_delay_input.setMaximum(maximum)
        self.proposed_delay_input.setMinimum(minimum)
        self.proposed_delay_input.setValue(default)
        self.proposed_delay_input.setSingleStep(0.1)

    def progress_callback(self, progress):
        self.progressBar.setValue(int(progress))

    def reset_on_completion(self, process):
        process.Wait()
        self.start_button.setEnabled(True)

    def open_file_dialog(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select a File", f"{os.getcwd()}"
        )
        self.filepath_input.setText(directory)

    def button_pressed(self):
        defs = self.get_current_args()
        if defs.filename == "":
            defs.filename = None
        if defs.filepath == "":
            defs.filepath = None
        if defs.ring_mode == "":
            defs.ring_mode = DEFAULT_MACHINE_MODE
        self.progressBar.setValue(0)
        process = cothread.Spawn(
            lambda: response_matrix(
                **vars(defs), progress_callback=self.progress_callback
            )
        )

        self.start_button.setEnabled(False)
        cothread.Spawn(self.reset_on_completion, process)


def start_gui(tooltips=None):
    if tooltips is None:
        print("tooltips cannot be none.")
    window = MainWindow(tooltips)
    window.show()
    cothread.WaitForQuit()
