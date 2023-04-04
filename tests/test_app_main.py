import os

from dls_response_matrix.respm_app import UI_FILENAME


def test_ui_file_exists():
    assert os.path.exists(UI_FILENAME) is True
