import random
import struct
import u6
from numbers import Number
import xtralien
import asyncio
import traceback


class LJTickDAC:
    """
    Updates DACA and DACB on a LJTick-DAC connected to a U3, U6 or UE9.
    
    """
    EEPROM_ADDRESS = 0x50
    DAC_ADDRESS = 0x12
    def __init__(self, device, dioPin):
        """
        device: The object to an opened U3, U6 or UE9.
        dioPin: The digital I/O line that the LJTick-DAC's DIOA is connected to.

        """
        self.device = device

        # The pin numbers for the I2C command-response
        self.sclPin = dioPin
        self.sdaPin = self.sclPin + 1

        self.getCalConstants()

    def toDouble(self, buff):
        """
        Converts the 8 byte array into a floating point number.
        buff: An array with 8 bytes.

        """
        right, left = struct.unpack("<Ii", struct.pack("B" * 8, *buff[0:8]))
        return float(left) + float(right)/(2**32)

    def getCalConstants(self):
        """
        Loads or reloads the calibration constants for the LJTick-DAC.
        See datasheet for more info.

        """
        data = self.device.i2c(LJTickDAC.EEPROM_ADDRESS, [64],
                               NumI2CBytesToReceive=36, SDAPinNum=self.sdaPin,
                               SCLPinNum=self.sclPin)
        response = data['I2CBytes']
        self.slopeA = self.toDouble(response[0:8])
        self.offsetA = self.toDouble(response[8:16])
        self.slopeB = self.toDouble(response[16:24])
        self.offsetB = self.toDouble(response[24:32])
        if 256 in response:
            msg = "LJTick-DAC calibration constants seem off. Check that the " \
                  "LJTick-DAC is connected properly."
            raise Exception(msg)

    def update_A(self, dacA):
        binaryA = int(dacA*self.slopeA + self.offsetA)
        self.device.i2c(LJTickDAC.DAC_ADDRESS,
                        [48, binaryA // 256, binaryA % 256],
                        SDAPinNum=self.sdaPin, SCLPinNum=self.sclPin)
    def update_B(self, dacB):
        binaryB = int(dacB*self.slopeB + self.offsetB)
        self.device.i2c(LJTickDAC.DAC_ADDRESS,
                        [49, binaryB // 256, binaryB % 256],
                        SDAPinNum=self.sdaPin, SCLPinNum=self.sclPin)

###################Flow calculation for the target and carrier gases (with humidity)################
#def calculate_gas_flows(target_ppm, config,step):
def calculate_gas_flows(target_ppm, config):
    cylinder_ppm = config['target_gas_initialPPM']
    #total_flow = config['totalFlow'] + step
    total_flow = config['totalFlow']
    test_type = config['test_type']
    if test_type == 'Humidity':
        rh = target_ppm
        target_flow = (0 / cylinder_ppm) * total_flow * 0.55 ## FOR CONSTANT CO2 VALUE, change 0 to any value
        #target_flow = 0
        rh_flow = (rh / 100.0) * total_flow
        #carrier_flow = total_flow - rh_flow
        carrier_flow = total_flow - ((1/0.55) * target_flow) - rh_flow ## FOR CONSTANT CO2 VALUE
    else:
        rh = config['humidity_set_point']
        target_flow = (target_ppm / cylinder_ppm) * total_flow * 0.55
        carrier_rh_flow = total_flow - target_flow
        #rh_flow = rh*carrier_rh_flow/100
        #carrier_flow = carrier_rh_flow - rh_flow
        rh_flow = (rh / 100.0) * total_flow
        carrier_flow = total_flow - ((1/0.55) * target_flow) - rh_flow

    return {
        'target_flow': round(target_flow, 3),
        'carrier_flow': round(carrier_flow, 3),
        'rh_flow': round(rh_flow, 3)
    }

#Calculation of the output MFC voltage
def flow_to_voltage(flow, max_flow, vref=5.0):
    v_gas = (flow / max_flow) * vref
    return round(v_gas, 3)

# #Function for the MFC voltage setup
def set_analog_output(device, ao_channel, voltage):

    voltage = max(0.0, min(voltage, 5.0)) #This sets the maximum output value to 5V
    dac_value = int((voltage / 5.0) * 65535)
    if ao_channel == 'AO0':
        device.getFeedback(u6.DAC0_16(dac_value))
    elif ao_channel == 'AO1':
        device.getFeedback(u6.DAC1_16(dac_value))
    elif ao_channel == 'AO2':
        dioPin = 2
        tdac = LJTickDAC(device, dioPin)
        tdac.update_A(voltage)
    elif ao_channel == 'AO3': 
        dioPin = 2
        tdac = LJTickDAC(device, dioPin)
        tdac.update_B(voltage)
    else:
        raise ValueError(f"Invalid analog output channel: {ao_channel}")

def get_analog_feedback(device, ao_channel):
    if ao_channel == 'AO0':
        ai_channel = 'AI0'
        return device.getAIN(0)
    elif ao_channel == 'AO1':
        ai_channel = 'AI1'
        return device.getAIN(1)
    elif ao_channel == 'AO2':
        ai_channel = 'AI2'
        return device.getAIN(2)
    elif ao_channel == 'AO3':
        ai_channel = 'AI3'
        return device.getAIN(3)
    else:
        raise ValueError(f"Unsupported AI channel: {ai_channel}")

def voltage_to_flow(feedback_voltage, max_flow):
    measured_flow = (feedback_voltage / 5.0) * max_flow
    return measured_flow




