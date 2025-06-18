[![CI](https://github.com/DiamondLightSource/dls-response-matrix/actions/workflows/ci.yml/badge.svg)](https://github.com/DiamondLightSource/dls-response-matrix/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/DiamondLightSource/dls-response-matrix/branch/main/graph/badge.svg)](https://codecov.io/gh/DiamondLightSource/dls-response-matrix)
[![PyPI](https://img.shields.io/pypi/v/dls-response-matrix.svg)](https://pypi.org/project/dls-response-matrix)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# dls_response_matrix

Generate storage ring response matrix by kicking individual corrector magnets and reading bpm data.

This module is used to generate a response matrix (RM) for the Diamond storage ring. It only requires a channel access 
connection to corrector magnets and bpms for the most basic usage. It is considered a slow method of calculating an RM
and takes ~11 minutes. For a faster version ~1 minute see the ploco-excite functionality of 
https://gitlab.diamond.ac.uk/controls/python3/ploco

Source          | <https://github.com/DiamondLightSource/dls-response-matrix>
:---:           | :---:
PyPI            | `pip install dls-response-matrix`
Docker          | `docker run ghcr.io/diamondlightsource/dls-response-matrix:latest`
Documentation   | <https://diamondlightsource.github.io/dls-response-matrix>
Releases        | <https://github.com/DiamondLightSource/dls-response-matrix/releases>

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

<!-- README only content. Anything below this line won't be included in index.md -->

See https://diamondlightsource.github.io/dls-response-matrix for more detailed documentation.

