import sys

if sys.version_info < (3, 8):
    from importlib_metadata import version  # noqa
else:
    from importlib.metadata import version  # noqa

from . import response_matrix

__version__ = version("dls-response-matrix")
del version

__all__ = ["__version__", "response_matrix"]
