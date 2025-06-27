from importlib.metadata import version  # noqa

from . import response_matrix

__version__ = version("dls-response-matrix")
del version

__all__ = ["__version__", "response_matrix"]
