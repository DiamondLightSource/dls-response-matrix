from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path

import cothread
import pytac  # noqa
from PyQt5 import QtCore, QtWidgets, uic  # noqa

from dls_response_matrix import __version__
from dls_response_matrix import response_matrix as rm

_qapp = cothread.iqt()

UI_FILENAME = Path(__file__).parent / "responsematrix.ui"


@dataclass
class Definitions:
    filename: str = None  # type: ignore
    ring_mode: str = rm.DEFAULT_MACHINE_MODE
    machine_type: str = "SIM"
    pytac_unit: str = "pytac.ENG"
    proposed_delta: float = 0.0
    remove_correctors: bool = False
    remove_bpms: bool = False
    split_graphs: bool = False


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, tooltips, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(UI_FILENAME, self)

        self.filename_input.setToolTip(tooltips["filename"])
        self.ring_mode_input.setToolTip(tooltips["ring-mode"])
        self.proposed_delta_input.setToolTip(tooltips["proposed-delta"])
        self.pytac_unit_input.setToolTip(tooltips["pytac-unit"])
        self.machine_type_input.setToolTip(tooltips["machine-type"])
        self.corrector_input.setToolTip(tooltips["remove-correctors"])
        self.bpm_input.setToolTip(tooltips["remove-bpms"])
        self.split_input.setToolTip(tooltips["split-graphs"])

        ring_modes, current_ring_mode = rm.get_ring_modes()
        self.ring_mode_input.addItems(ring_modes)
        self.ring_mode_input.setCurrentText(current_ring_mode)
        self.set_limits()
        self.pytac_unit_input.activated.connect(lambda: self.set_limits())
        self.start_button.clicked.connect(self.button_pressed)

    def get_current_args(self):
        return Definitions(
            filename=self.filename_input.text(),
            ring_mode=self.ring_mode_input.currentText(),
            machine_type=self.machine_type_input.currentText(),
            pytac_unit=self.pytac_unit_input.currentText(),
            proposed_delta=self.proposed_delta_input.text(),
            remove_correctors=self.corrector_input.isChecked(),
            remove_bpms=self.bpm_input.isChecked(),
            split_graphs=self.split_input.isChecked(),
        )

    def set_limits(self):
        maximum, minimum, default, name = rm.DELTA_LIMITS[
            self.pytac_unit_input.currentText()
        ]
        self.proposed_delta_input.setMaximum(maximum)
        self.proposed_delta_input.setMinimum(minimum)
        self.proposed_delta_input.setValue(default)
        self.proposed_delta_input.setSingleStep((maximum - minimum) / 100)

    def progress_callback(self, progress):
        self.progressBar.setValue(int(progress))

    def reset_on_completion(self, process):
        process.Wait()
        self.start_button.setEnabled(True)

    def button_pressed(self):
        defs = self.get_current_args()
        if defs.filename == "":
            defs.filename = None
        if defs.ring_mode == "":
            defs.ring_mode = rm.DEFAULT_MACHINE_MODE
        self.progressBar.setValue(0)
        process = cothread.Spawn(
            lambda: rm.response_matrix(
                **vars(defs), progress_callback=self.progress_callback
            )
        )

        self.start_button.setEnabled(False)
        cothread.Spawn(self.reset_on_completion, process)


def parse_arguments():
    parser = ArgumentParser()
    parser.add_argument("--version", action="version", version=__version__)
    return parser.parse_args()


def main(tooltips=None):
    if tooltips is None:
        print("tooltips cannot be none.")
    args = parse_arguments()  # noqa
    window = MainWindow(tooltips)
    window.show()
    cothread.WaitForQuit()


if __name__ == "__main__":
    main()
