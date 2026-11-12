import numpy as np
import matplotlib.pyplot as plt
import csv
from scipy.signal import find_peaks as scipy_find_peaks
from scipy.signal import savgol_filter as scipy_savgol_filter
from scipy.integrate import trapezoid as integrate_trapezoid

class Collection:

    def __init__(self, *args):
        self.spectra = list(spectrum.name for spectrum in args)
        self.counts = list(spectrum.counts for spectrum in args)
        self.wavelengths = list(spectrum.wavelengths for spectrum in args)
        self.peaks = list(spectrum.peaks for spectrum in args)
        self.name = "Collection"

    def add(self, spectrum):
        self.spectra.append(spectrum.name)
        self.counts.append(spectrum.counts)
        self.wavelengths.append(spectrum.wavelengths)
        self.peaks.append(spectrum.peaks)
    
    def plot(self, label_y_spacing=40, label_x_spacing=10):
        fig, ax = plt.subplots(figsize=(10, 6))

        for i in range(len(self.spectra)):
            ax.plot(self.wavelengths[i][:], self.counts[i][:], linewidth=1, label=self.spectra[i])
            if self.peaks[i].any():
                ax.scatter(self.peaks[i][:, 0], self.peaks[i][:, 1], label=f"{self.spectra[i]} peaks")
                for peak in self.peaks[i]:
                    label = str(np.round(peak[0], decimals=1))# + " nm"
                    offset = np.array([label_x_spacing, label_y_spacing])
                    ax.annotate(label, xy=peak, xytext=peak+offset)


        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Counts")
        ax.legend()
        ax.set_title(self.name)

        ax.grid(True, alpha=0.3)

        plt.show()


class Spectrum:

    def __init__(self, wavelengths, counts, metadata={}, name="Spectrum"):
        self.wavelengths = np.array(wavelengths)
        self.counts = np.array(counts)
        self.metadata = metadata
        self.peaks = np.array([])
        self.name = name
        self.normalized = False

    @classmethod
    def from_txt(cls, filename):
        """
        Read spectral data from a spectrometer TXT file.

        Returns an instance of class Spectrum.
        """

        wavelengths = []
        counts = []
        metadata = {}

        reading_data = False

        with open(filename, "r", encoding="utf-8", errors="replace") as file:
            for line in file:

                line = line.strip()

                # Start reading spectral data
                if line == "+++++Begin Spectral Data+++++":
                    reading_data = True
                    continue

                # Stop reading spectral data
                if line == "+++++End Spectral Data+++++":
                    break

                # Read metadata
                if not reading_data:
                    if ":" in line:
                        key, value = line.split(sep=":", maxsplit=1)[:2]
                        metadata[key] = value
                
                # Append source to metadata
                metadata["data_source"] = "txt"

                # Ignore empty lines
                if not line:
                    continue

                # Data are separated by tabs
                try:
                    wavelength, intensity = line.split()[:2]

                    wavelengths.append(float(wavelength))
                    counts.append(float(intensity))

                except ValueError:
                    # Ignore malformed lines
                    continue

        name =  filename.split("\\")[-1][:-4]
        return cls(wavelengths, counts, metadata, name)

    @classmethod
    def from_csv(cls, filename):
        """
        Read spectral data from a spectrometer csv file.

        Returns an instance of class Spectrum.
        """

        wavelengths = []
        intensities = []
        metadata = {}

        with open(filename, "r", encoding="utf-8-sig", errors="replace", newline="") as file:

            reader = csv.reader(file)

            # First row contains metadata
            metadata_row = next(reader)
            metadata_row = metadata_row[0].split(";")

            # Metadata are stored as:
            # Name:: Spectrum 57
            # Timestamp:: 2026-09-10 ...
            for item in metadata_row:
                if "::" in item:
                    key, value = item.split("::", 1)
                    metadata[key.strip()] = value.strip()
            
            # Append source to metadata
            metadata["data_source"] = "csv"

            # Second row contains column names
            header = next(reader)

            # Find the relevant columns by name
            wavelength_index = header.index("Wavelength (nm)")
            intensity_index = header.index("Intensity")

            # Read spectral data
            for row in reader:

                if not row:
                    continue

                try:
                    wavelengths.append(float(row[wavelength_index]))
                    intensities.append(float(row[intensity_index]))

                except (ValueError, IndexError):
                    continue

        name =  filename.split("\\")[-1][:-4]
        return cls(wavelengths, intensities, metadata, name)


    def plot(self):
        if self.normalized:
            label_y_spacing = 0.015
        else:
            label_y_spacing = 15

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(self.wavelengths, self.counts, linewidth=1)

        if self.peaks.any():
            ax.scatter(self.peaks[:, 0], self.peaks[:, 1], label="Peaks")
            for peak in self.peaks:
                label = str(np.round(peak[0], decimals=1))# + " nm"
                offset = np.array([-10, label_y_spacing])
                ax.annotate(label, xy=peak, xytext=peak+offset)

        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Counts")
        ax.set_title(self.name)

        ax.grid(True, alpha=0.3)

        plt.show()

    def normalize(self):
        self.counts = self.counts * 1 / np.max(self.counts)
        self.normalized = True

    def zero_baseline(self):
        self.counts = self.counts - np.min(self.counts)

    def subtract(self, other):
        self.counts = np.subtract(self.counts, other.counts)

    def smooth(self, window_length=21, poly_order=3):
        self.counts = scipy_savgol_filter(self.counts, window_length, poly_order)

    def find_peaks(self, spacing=100, h=None, w=20):
        if h == None:
            if self.normalized:
                h = 0.05
            else:
                h = np.min(self.counts) + np.max(self.counts) * 0.1
            
        idxs = scipy_find_peaks(self.counts, distance=spacing, height=h, width=w)[0]
        peaks = np.swapaxes(np.array([self.wavelengths[idxs], self.counts[idxs]]), 0, 1)
        self.peaks = peaks

    def lp_filter(self, cutoff_wavelength=500, factor=0.95, offset=0.02):
        transmittance = (self.wavelengths > cutoff_wavelength) * factor + offset
        self.counts = self.counts * transmittance

    def get_power(self):
        power = integrate_trapezoid(self.counts, self.wavelengths)
        return power
    
