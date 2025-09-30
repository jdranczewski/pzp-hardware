import sys
sys.path.append(r"C:\Program Files (x86)\IVI Foundation\VISA\WinNT\TLPM\Example\Python")

from TLPM import TLPM
import ctypes

tlPM = None

def connect():
    global tlPM

    # Find devices
    tlPM = TLPM()
    deviceCount = ctypes.c_uint32()
    tlPM.findRsrc(ctypes.byref(deviceCount))

    # Iterate through all to get a resourceName (currently assuming there's only one device here)
    resourceName = ctypes.create_string_buffer(1024)
    for i in range(0, deviceCount.value):
        tlPM.getRsrcName(ctypes.c_int(i), resourceName)
        break
    tlPM.close()

    # Connect to this device
    tlPM = TLPM()
    result = tlPM.open(resourceName, ctypes.c_bool(True), ctypes.c_bool(True))
    if result:
        raise Exception("Powermeter init failed with code {}".format(result))
    # tlPM.setPowerAutoRange(1)

def set_wavelength(wavelength):
    tlPM.setWavelength(ctypes.c_double(wavelength))
    wavelength = ctypes.c_double()
    tlPM.getWavelength(ctypes.c_int(0), ctypes.byref(wavelength))
    return wavelength.value

def power():
    power = ctypes.c_double()
    tlPM.measPower(ctypes.byref(power))
    return power.value

def disconnect():
    tlPM.close()

def zero():
    tlPM.startDarkAdjust()
    
def get_avg_time():
    value = ctypes.c_double()
    tlPM.getAvgTime(0, ctypes.byref(value))
    return value.value
    
def set_avg_time(value):
    tlPM.setAvgTime(ctypes.c_double(value))
