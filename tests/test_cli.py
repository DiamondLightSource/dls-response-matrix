import subprocess
import sys

from dls_response_matrix import __version__


def test_cli_module_version():
    cmd = [sys.executable, "-m", "dls_response_matrix", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__


def test_cli_version():
    cmd = ["dls-response-matrix", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__


def test_cli_gui_version():
    cmd = ["dls-response-matrix-gui", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
