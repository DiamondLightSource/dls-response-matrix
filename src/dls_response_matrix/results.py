"""results.py includes all classes and functions related to Results
including plotting and saving."""

from __future__ import annotations

import json
import logging as log
import os
import shutil

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
        self,
        config: Config,
        matrix: np.ndarray,
        new_filename: str | None = None,
        new_filepath: str | None = None,
    ):
        """Setup of the Results class.

        Args:
            config: A populated Config object.
            matrix: A matrix that contains a row for each BPM, and a
                column for each corrector magnet.
            new_filename: An optional new name to use when saving results
                data. If not specified, the folderpath from config is used.
            new_folderpath: An optional location to save results data,
                if not specified, the folderpath from config is used.
        """
        self._config: Config = config
        self._matrix: np.ndarray = matrix
        self._filepath: str = config.filepath
        self._filename: str = config.filename
        if new_filename is not None or new_filepath is not None:
            self._create_new_data_dir(new_filename, new_filepath)

    def _create_new_data_dir(self, new_filename=None, new_filepath=None):
        """Check that the new folderpath exists and is not the same as the one specified
        in the config. If it exists, then create a new RM- subdirectory."""
        new_filename = self._config.filename if new_filename is None else new_filename
        new_filepath = self._config.filepath if new_filepath is None else new_filepath

        if os.path.join(self._config.filepath, self._config.filename) == os.path.join(
            new_filepath, new_filename
        ):
            raise NewFilenameRequired(
                "New file name and path cannot be the same as old file name and path."
            )
        elif not os.path.exists(new_filepath):
            raise FileExistsError(f"Folder {new_filepath} does not exists.")

        if new_filepath is not None:
            self._filepath: str = new_filepath
            if new_filename is not None:
                self._filename = new_filename
                os.mkdir(f"{new_filepath}/RM-{new_filename}")
            else:
                self._filename = self.config.filename
                os.mkdir(f"{new_filepath}/RM-{self.config.filename}")

            # Copy the raw data to the new data folder for use by the plotting function
            old_foldername = f"RM-{self._config.filename}"
            old_filename = f"rawdata-full-{self._config.filename}.csv"
            src = os.path.join(self._config.filepath, old_foldername, old_filename)

            new_foldername = f"RM-{self._filename}"
            new_filename = f"rawdata-full-{self._filename}.csv"
            dst = os.path.join(self._filepath, new_foldername, new_filename)
            shutil.copyfile(src, dst)

    @classmethod
    def from_corrector_info(
        cls,
        config: Config,
        x_correctors: int,
        y_correctors: int,
        bpms: int,
        new_filename: str | None = None,
        new_filepath: str | None = None,
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
        return cls(config, matrix, new_filename, new_filepath)

    @classmethod
    def from_csv(
        cls,
        full_folderpath: str,
        new_filename: str | None = None,
        new_filepath: str | None = None,
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

        config = Config(
            metadata["Filename"],
            metadata["Filepath"],
            metadata["ISO time"],
            metadata["Pytac units"],
            metadata["Ring Mode"],
            metadata["Machine type"],
            metadata["Delta"],
            metadata["Time delay"],
        )
        return cls(config, matrix, new_filename, new_filepath)

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
        _disabled_bpm_list = list(disabled_bpms)
        # Y bpms
        _disabled_bpm_list.extend([x_bpms + index for index in disabled_bpms])

        for index in _disabled_bpm_list[::-1]:
            self._matrix = np.delete(self._matrix, index, axis=0)

    def write_csv(self):
        """Writes the matrix to a .csv."""
        log.info("Writing data to .csv file.")
        foldername = f"RM-{self._filename}"
        filename = f"rawdata-full-{self._filename}.csv"

        np.savetxt(
            os.path.join(self._filepath, foldername, filename),
            self._matrix,
        )

    def plot(self, split: bool | None = False):
        """Plot the matrix.

        Args:
            split: If the matrix is already split,
                then plot each quadrant seperately. Defaults to False.
        """
        foldername = f"RM-{self._filename}"

        if split:
            names = ["xCxB", "yCxB", "xCyB", "yCyB"]
        else:
            names = ["full"]
            matrix = self._matrix

        for plot_name in names:
            csv_filename = f"rawdata-{plot_name}-{self._filename}.csv"
            plot_filename = f"plot-{plot_name}-{self._filename}.png"
            matrix = np.genfromtxt(
                os.path.join(self._filepath, foldername, csv_filename)
            )

            plt.imshow(matrix, "RdBu", norm=TwoSlopeNorm(vcenter=0))
            plt.xlim([-1, np.shape(matrix)[1]])
            plt.ylim([np.shape(matrix)[0], -1])
            plt.colorbar()
            plt.xlabel("Correctors")
            plt.ylabel("BPM")
            plt.title(f"Response Matrix {plot_name}: {self._config.iso_time}")
            plt.savefig(
                os.path.join(self._filepath, foldername, plot_filename),
                bbox_inches="tight",
                dpi=1200,
            )
            plt.close()

    def split(self):
        """Splits the matrix up into quadrants and writes .csvs."""
        log.info("Splitting the matrix.")
        foldername = f"RM-{self._filename}"
        xCxB_filename = f"rawdata-xCxB-{self._filename}.csv"
        yCxB_filename = f"rawdata-yCxB-{self._filename}.csv"
        xCyB_filename = f"rawdata-xCyB-{self._filename}.csv"
        yCyB_filename = f"rawdata-yCyB-{self._filename}.csv"

        xCxB_yCxB, xCyB_yCyC = np.vsplit(self._matrix, 2)
        xCxB, yCxB = np.hsplit(xCxB_yCxB, 2)
        xCyB, yCyB = np.hsplit(xCyB_yCyC, 2)

        np.savetxt(
            os.path.join(self._filepath, foldername, xCxB_filename),
            xCxB,
        )
        np.savetxt(
            os.path.join(self._filepath, foldername, yCxB_filename),
            yCxB,
        )
        np.savetxt(
            os.path.join(self._filepath, foldername, xCyB_filename),
            xCyB,
        )
        np.savetxt(
            os.path.join(self._filepath, foldername, yCyB_filename),
            yCyB,
        )
