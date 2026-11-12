import u6
import time
import csv
from datetime import datetime

import mfc # Custom library

# MFC specifications
MAX_FLOW = 1000       # sccm
VREF = 5.0            # V
DURATION = 120        # seconds per configuration
SAMPLE_INTERVAL = 10   # seconds


def run_mfc_test():

    device = u6.U6()

    # Test configurations: (AO0 flow, AO1 flow)
    configurations = [
        (500, 0),
        (0, 500),
        (250, 250)
    ]

    try:
        # Start with both outputs at zero
        mfc.set_analog_output(device, "AO0", 0)
        mfc.set_analog_output(device, "AO1", 0)

        print("\nStarting MFC scaling test.")
        print(f"Maximum flow: {MAX_FLOW} sccm")
        print(f"Duration per configuration: {DURATION} seconds\n")

        with open("mfc_test_results.csv", "w", newline="") as file:

            writer = csv.writer(file)
            writer.writerow([
                "Timestamp",
                "Configuration",
                "AO0_Setpoint_sccm",
                "AO0_Command_V",
                "AO0_Feedback_V",
                "AO0_Measured_sccm",
                "AO1_Setpoint_sccm",
                "AO1_Command_V",
                "AO1_Feedback_V",
                "AO1_Measured_sccm"
            ])

            for i, (flow0, flow1) in enumerate(configurations):

                voltage0 = mfc.flow_to_voltage(flow0, MAX_FLOW, VREF)
                voltage1 = mfc.flow_to_voltage(flow1, MAX_FLOW, VREF)

                print(f"\nConfiguration {i+1}/3")
                print(f"AO0: {flow0} sccm ({voltage0} V)")
                print(f"AO1: {flow1} sccm ({voltage1} V)")

                # Apply the new setpoints
                mfc.set_analog_output(device, "AO0", voltage0)
                mfc.set_analog_output(device, "AO1", voltage1)

                start_time = time.monotonic()

                while time.monotonic() - start_time < DURATION:

                    # Read analog feedback
                    feedback0 = mfc.get_analog_feedback(device, "AO0")
                    feedback1 = mfc.get_analog_feedback(device, "AO1")

                    # Convert feedback voltages into flow estimates
                    measured0 = mfc.voltage_to_flow(feedback0, MAX_FLOW)
                    measured1 = mfc.voltage_to_flow(feedback1, MAX_FLOW)

                    elapsed = time.monotonic() - start_time

                    timestamp = datetime.now().isoformat(timespec="seconds")

                    writer.writerow([
                        timestamp,
                        i + 1,
                        flow0,
                        voltage0,
                        feedback0,
                        measured0,
                        flow1,
                        voltage1,
                        feedback1,
                        measured1
                    ])

                    file.flush()

                    print(
                        f"\rElapsed: {elapsed:5.1f}s | "
                        f"AO0: {measured0:7.1f} sccm | "
                        f"AO1: {measured1:7.1f} sccm",
                        end="",
                        flush=True
                    )

                    time.sleep(SAMPLE_INTERVAL)

                print("\nConfiguration completed.")

    except KeyboardInterrupt:
        print("\nTest interrupted by user.")

    finally:
        # Return both command outputs to zero
        try:
            mfc.set_analog_output(device, "AO0", 0)
            mfc.set_analog_output(device, "AO1", 0)
            print("\nBoth analog outputs set to zero.")
        finally:
            device.close()
            print("LabJack connection closed.")


if __name__ == "__main__":
    run_mfc_test()
