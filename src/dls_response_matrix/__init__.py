from importlib.metadata import version

__version__ = version("dls-response-matrix")
del version

__all__ = ["__version__"]
