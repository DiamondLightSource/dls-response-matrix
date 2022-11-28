import subprocess
import sys

from dls_response_matrix import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "dls_response_matrix", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
