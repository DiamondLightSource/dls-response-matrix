import os

import pytest


@pytest.fixture(autouse=True)
def set_environment():
    os.environ["EPICS_CA_SERVER_PORT"] = str(8064)
    os.environ["EPICS_CA_REPEATER_PORT"] = str(8065)
