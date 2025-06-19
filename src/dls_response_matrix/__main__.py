from argparse import ArgumentParser

from dls_response_matrix.respm_app import start_gui
from dls_response_matrix.response_matrix import (
    DEFAULT_MACHINE_MODE,
    get_ring_modes,
    response_matrix,
)

from . import __version__

__all__ = ["main"]

HELP_INFO = {
    "filename": "The filename for the saved files. Default is the ISO time.",
    "filepath": "The path to the directory where the files should be saved. Default is cwd",
    "ring-mode": "The ring mode of the model. Default is I04",
    "proposed-delta": "The proposed delta to vary correctors by.",
    "proposed-delay": "The proposed time delay to wait between each magnet kick.",
    "pytac-unit": (
        "The units for the model. Toggles between pytac.ENG (default) and pytac.PHYS"
        " units."
    ),
    "machine-type": "The machine type. Toggles between SIM (default) and LIVE units.",
    "remove-correctors": "Remove disabled correctors. Toggle. Default = False",
    "remove-bpms": "Remove disabled BPMs. Toggle. Default = False",
    "split-graphs": "Save individual quadrants. Toggle. Default = False",
}


def parse_arguments():
    parser = ArgumentParser()
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--filename",
        "-f",
        type=str,
        default=None,
        help=HELP_INFO["filename"],
    )
    parser.add_argument(
        "--filepath",
        "-p",
        type=str,
        default=None,
        help=HELP_INFO["filepath"],
    )
    parser.add_argument(
        "--ring-mode",
        "-r",
        type=str,
        default=get_ring_modes()[1],
        help=HELP_INFO["ring-mode"],
    )
    parser.add_argument(
        "--proposed-delta",
        "-d",
        type=float,
        default=0.0,
        help=HELP_INFO["proposed-delta"],
    )
    parser.add_argument(
        "--proposed-delay",
        "-t",
        type=float,
        default=None,
        help=HELP_INFO["proposed-delay"],
    )
    parser.add_argument(
        "--pytac-unit",
        "-u",
        default="pytac.ENG",
        const="pytac.PHYS",
        action="store_const",
        help=HELP_INFO["pytac-unit"],
    )
    parser.add_argument(
        "--machine-type",
        "-m",
        default="SIM",
        const="LIVE",
        action="store_const",
        help=HELP_INFO["machine-type"],
    )
    parser.add_argument(
        "--remove-correctors",
        "-c",
        action="store_true",
        help=HELP_INFO["remove-correctors"],
    )
    parser.add_argument(
        "--remove-bpms",
        "-b",
        action="store_true",
        help=HELP_INFO["remove-bpms"],
    )
    parser.add_argument(
        "--split-graphs",
        "-s",
        action="store_true",
        help=HELP_INFO["split-graphs"],
    )
    return parser.parse_args()


def main(args=None):
    args = parse_arguments()
    response_matrix(
        args.filename,
        args.filepath,
        args.ring_mode,
        args.proposed_delta,
        args.proposed_delay,
        args.pytac_unit,
        args.machine_type,
        args.remove_correctors,
        args.remove_bpms,
        args.split_graphs,
    )


def parse_gui_arguments():
    parser = ArgumentParser()
    parser.add_argument("-v", "--version", action="version", version=__version__)
    return parser.parse_args()


def gui_main():
    parse_gui_arguments()  # Only used for version
    start_gui(HELP_INFO)


if __name__ == "__main__":
    main()
