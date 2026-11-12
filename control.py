import serial
import numpy as np
import os
import time
from datetime import datetime as dt

import spectroscopy # Custom library

# --------------------------------------------------
# Initialize spectrometer
# --------------------------------------------------

s = serial.Serial('COM4', timeout=15)

# Query device metadata
s.write(b'<gain?>')
gain = s.readline().decode().strip()

s.write(b'<offset?>')
offset = s.readline().decode().strip()

s.write(b'<itime?>')
itime = s.readline().decode().strip()

# Set integration time to 4000 ms
s.write(b'<itime:4000000>')
response = s.readline().decode().strip()
print(response)

# Retrieve wavelengths (only needs to be done once)
s.write(b'<wavs?>')
response = s.readline().decode()

wavelengths = np.fromstring(response, sep=',')

# --------------------------------------------------
# Acquisition function
# --------------------------------------------------

def acquire_spectrum():
    """Acquire one spectrum and return a Spectrum object."""

    s.write(b'<read:1>')
    response = s.read(3204)

    if len(response) != 3204:
        raise TimeoutError(
            f"Incomplete spectrum: received {len(response)} of 3204 bytes"
        )

    counts = np.frombuffer(
        response[2:3202],
        dtype=np.uint16
    ).copy()

    timestamp = dt.now().isoformat()

    metadata = {
        'gain': gain,
        'offset': offset,
        'integration time': itime,
        'date and time': timestamp
    }

    return spectroscopy.Spectrum(
        wavelengths,
        counts,
        metadata
    )

# --------------------------------------------------
# Save spectrum
# --------------------------------------------------

def save_spectrum(wavelengths, counts, filename):
    data = np.column_stack((wavelengths, counts))

    np.savetxt(
        filename,
        data,
        delimiter=',',
        header='Wavelength (nm),Intensity',
        comments=''
    )

# --------------------------------------------------
# Periodic measurements
# --------------------------------------------------

interval = 60  # Seconds between measurements

next_measurement = time.monotonic()

folder = "experiment_001"
os.makedirs(folder, exist_ok=True)
measurement_number = 1

try:
    while True:

        # Wait until the next scheduled measurement
        time.sleep(max(0, next_measurement - time.monotonic()))

        # Acquire spectrum
        spectrum = acquire_spectrum()

        # Save spectrum
        filename = os.path.join(folder, f"spectrum_{measurement_number:02d}_{spectrum.metadata['date and time']}.csv")
        save_spectrum(spectrum.wavelength, spectrum.counts, filename)

        print(
            f"Measurement {measurement_number} acquired at {spectrum.metadata['date and time']}"
        )

        measurement_number += 1

        # Schedule next measurement
        next_measurement += interval

        # Skip missed time slots rather than taking measurements back-to-back
        now = time.monotonic()

        while next_measurement <= now:
            next_measurement += interval

except KeyboardInterrupt:
    print("\nMeasurement stopped by user.")

finally:
    s.close()