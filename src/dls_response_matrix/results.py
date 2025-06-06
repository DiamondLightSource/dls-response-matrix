"""results.py includes all classes and functions related to Results
including plotting and saving."""

from __future__ import annotations

import json
import logging as log
import os
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm

from dls_response_matrix.configuration import Config


class NewFilenameRequired(Exception):
    """Raised when a duplicate filename is passed."""

    pass


class Results:
    """The Results class handles the data, providing functions to store, remove, save,
    split and plot."""

    def __init__(
        self, config: Config, matrix: np.ndarray
    ):
        """Setup of the Results class.

        Args:
            config: A populated Config object.
            matrix: A matrix that contains a row for each BPM, and a
                column for each corrector magnet.
        """
        self._config: Config = config
        self._matrix: np.ndarray = matrix

    @classmethod
    def from_corrector_info(
        cls, config: Config, x_correctors: int, y_correctors: int, bpms: int
    ):
        """Create a matrix of the appropriate size for the Results object.

        Args:
            config: A populated Config object.
            x_correctors: The number of horizontal correctors.
            y_correctors: The number of vertical correctors
            bpms: The number of BPMs.

        Returns:
            A Results object.
        """
        matrix: np.ndarray = np.zeros(shape=(2 * bpms, x_correctors + y_correctors))
        return cls(config, matrix)

    @classmethod
    def from_csv(
        cls,
        full_folderpath: str,
        new_filename: str,
        new_filepath: str,
    ):
        """Load and setup the Results object when given a valid folderpath.

        The folderpath must contain a .json with "metadata" in the name, alongside
        a .csv file with "rawdata" in the name.

        Args:
            full_folderpath: The path to the folder with old data that we are importing.
            new_filename: The filename that newly generated files will have.
            new_filepath: The path to the directory where the new data is to be stored.

        Returns:
            A Results object.

        Raises:
            NewFilenameRequired: If the filename is identical to an existing file.
        """
        file_list = os.listdir(full_folderpath)
        metadata_file = [file for file in file_list if file.startswith("metadata")][0]
        rawdata_file = [file for file in file_list if file.startswith("rawdata")][0]

        matrix = np.genfromtxt(os.path.join(full_folderpath, rawdata_file))
        with open(os.path.join(full_folderpath, metadata_file)) as f:
            metadata = json.load(f)

        if os.path.join(metadata["Filepath"], metadata["Filename"]) == os.path.join(new_filepath, new_filename):
            raise NewFilenameRequired(
                "New file name and path cannot be the same as old file name and path."
            )

        config = Config(
            new_filename,
            new_filepath,
            metadata["ISO time"],
            metadata["Pytac units"],
            metadata["Ring Mode"],
            metadata["Machine type"],
            metadata["Delta"],
            metadata["Time delay"],
        )
        return cls(config, matrix)

    def store(self, bpm_values: np.ndarray, index: int):
        """Store the BPM values in the correct index of the matrix.

        Args:
            bpm_values: The BPM values.
            index: The index of the BPM from which the values came.
        """
        self._matrix[:, index] = bpm_values

    def remove_bpms(self, disabled_bpms: list, x_bpms: int):
        """Remove inactive BPMs from the matrix.

        Args:
            disabled_bpms: The list of BPM indices to remove.
            x_bpms: The number of horizontal BPMs.
        """
        log.info("Removed inactive bpms.")
        # X bpms
        _disabled_bpm_list = [index for index in disabled_bpms]
        # Y bpms
        _disabled_bpm_list.extend([x_bpms + index for index in disabled_bpms])

        for index in _disabled_bpm_list[::-1]:
            self._matrix = np.delete(self._matrix, index, axis=0)

    def write_csv(self):
        """Writes the matrix to a .csv."""
        log.info("Writing data to .csv file.")

        cwd = self._config.filepath if self._config.filepath is not None else os.getcwd()
        foldername = f"RM-{self._config.filename}"
        filename = f"rawdata-full-{self._config.filename}.csv"

        np.savetxt(
            os.path.join(cwd, foldername, filename),
            self._matrix,
        )

    def plot(self, split: Optional[bool] = False):
        """Plot the matrix.

        Args:
            split: If the matrix is already split,
                then plot each quadrant seperately. Defaults to False.
        """
        cwd = self._config.filepath if self._config.filepath is not None else os.getcwd()
        foldername = f"RM-{self._config.filename}"

        if split:
            names = ["xCxB", "yCxB", "xCyB", "yCyB"]
        else:
            names = ["full"]
            matrix = self._matrix

        for plot_name in names:
            csv_filename = f"rawdata-{plot_name}-{self._config.filename}.csv"
            plot_filename = f"plot-{plot_name}-{self._config.filename}.png"
            matrix = np.genfromtxt(os.path.join(cwd, foldername, csv_filename))

            plt.imshow(matrix, "RdBu", norm=TwoSlopeNorm(vcenter=0))
            plt.xlim([-1, np.shape(matrix)[1]])
            plt.ylim([np.shape(matrix)[0], -1])
            plt.colorbar()
            plt.xlabel("Correctors")
            plt.ylabel("BPM")
            plt.title(f"Response Matrix {plot_name}: {self._config.iso_time}")
            plt.savefig(
                os.path.join(cwd, foldername, plot_filename),
                bbox_inches="tight",
                dpi=1200,
            )
            plt.close()

    def split(self):
        """Splits the matrix up into quadrants and writes .csvs."""
        log.info("Splitting the matrix.")
        cwd = self._config.filepath if self._config.filepath is not None else os.getcwd()
        foldername = f"RM-{self._config.filename}"
        xCxB_filename = f"rawdata-xCxB-{self._config.filename}.csv"
        yCxB_filename = f"rawdata-yCxB-{self._config.filename}.csv"
        xCyB_filename = f"rawdata-xCyB-{self._config.filename}.csv"
        yCyB_filename = f"rawdata-yCyB-{self._config.filename}.csv"

        xCxB_yCxB, xCyB_yCyC = np.vsplit(self._matrix, 2)
        xCxB, yCxB = np.hsplit(xCxB_yCxB, 2)
        xCyB, yCyB = np.hsplit(xCyB_yCyC, 2)

        np.savetxt(
            os.path.join(cwd, foldername, xCxB_filename),
            xCxB,
        )
        np.savetxt(
            os.path.join(cwd, foldername, yCxB_filename),
            yCxB,
        )
        np.savetxt(
            os.path.join(cwd, foldername, xCyB_filename),
            xCyB,
        )
        np.savetxt(
            os.path.join(cwd, foldername, yCyB_filename),
            yCyB,
        )
