dls-response-matrix
=============================================================================

|code_ci| |docs_ci| |coverage| |pypi_version| |license|

This package contains a response matrix generation module.

============== ==============================================================
PyPI           ``pip install dls-response-matrix``
Source code    https://github.com/DiamondLightSource/dls-response-matrix

Releases       https://github.com/DiamondLightSource/dls-response-matrix/releases
============== ==============================================================

.. |code_ci| image:: https://github.com/DiamondLightSource/dls-response-matrix/actions/workflows/code.yml/badge.svg?branch=main
    :target: https://github.com/DiamondLightSource/dls-response-matrix/actions/workflows/code.yml
    :alt: Code CI

.. |docs_ci| image:: https://github.com/DiamondLightSource/dls-response-matrix/actions/workflows/docs.yml/badge.svg?branch=main
    :target: https://github.com/DiamondLightSource/dls-response-matrix/actions/workflows/docs.yml
    :alt: Docs CI

.. |coverage| image:: https://codecov.io/gh/DiamondLightSource/dls-response-matrix/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/DiamondLightSource/dls-response-matrix
    :alt: Test Coverage

.. |pypi_version| image:: https://img.shields.io/pypi/v/dls-response-matrix.svg
    :target: https://pypi.org/project/dls-response-matrix
    :alt: Latest PyPI version

.. |license| image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
    :target: https://opensource.org/licenses/Apache-2.0
    :alt: Apache License

..
    Anything below this line is used when viewing README.rst and will be replaced
    when included in index.rst

To create a new response matrix with default settings, run: 

    dls_response_matrix

To get commandline help, run: 

    dls_response_matrix -h

To load an existing response matrix csv and save the data to a new directory:
From within a python venv:

    >>> import dls_response_matrix
    >>> old_data_path = "/path/to/existing/data/"
    >>> results = dls_response_matrix.results.Results.from_csv(old_data_path, "new_name", "new/file/path/")
    >>> results.split()
    >>> results.plot(split=True)