# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
:module_title:`ThorLabs Powermeter`

Pieces for interacting with
`ThorLabs powermeter consoles <https://www.thorlabs.com/navigation.cfm?guide_id=37>`__
using the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework.

Example usage (see :ref:`getting-started` for more details on using Pieces in general)::

    import puzzlepiece as pzp
    from pzp_hardware.thorlabs import powermeter

    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("powermeter", powermeter.Piece, row=0, column=0)
    puzzle.show()
    app.exec()

Installation
------------
* Install the ThorLabs Optical Power Monitor (OPM) software from https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=OPM
* Make sure your powermeter console is using the ``TLPM`` driver, this can be done using the "Driver Switcher" app
  installed with the OPM software.
* The OPM software will install relevant files in two locations, a 32bit and a 64bit one.

  - Locate the TLPM Python examples directory, usually ``C:\Program Files (x86)\IVI Foundation\VISA\WinNT\TLPM\Examples\Python``
    (this will always be in the 32bit installation folder, so 'Program Files (x86)').
  - Locate the TLPM DLL directory, which will be either in 'Program Files' on 64 bit systems, or in 'Program Files (x86)' on 32bit
    systems. It will be of the form ``C:\Program Files\IVI Foundation\VISA\Win64\Bin``.

* Copy the paths of the above directories and paste them into the terminal when prompted at runtime.

Requirements
------------
.. pzp_requirements:: pzp_hardware.thorlabs.powermeter

Available Pieces
----------------
"""

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht

#MARK: Piece
class Piece(pzp.Piece):
    """
    Main ThorLabs powermeter Piece.

    .. image:: ../images/pzp_hardware.thorlabs.powermeter.Piece.png
    """

    def define_params(self):
        @pzp.param.dropdown(self, "device", "")
        def list_devices():
            if self.puzzle.debug:
                return None
            # Based on the TLPM "PowermeterSample.py"
            tlPM = self._TLPM_class()
            try:
                # How many devices can we detect?
                deviceCount = pht.c.c_uint32()
                tlPM.findRsrc(pht.c.byref(deviceCount))
                # Iterate over the devices and yield their ids
                resourceName = pht.c.create_string_buffer(1024)
                for i in range(0, deviceCount.value):
                    tlPM.getRsrcName(pht.c.c_int(i), resourceName)
                    yield resourceName.value.decode()
                tlPM.close()
            except NameError:
                # A NameError is raised if no powermeters connected to the system
                tlPM.close()
                return None

        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                return 1
            if self._ensure(capture_exception=True):
                # Close any existing instance
                self.tlPM.close()
            # Instance the TLPM class
            self.tlPM = self._TLPM_class()
            # Connect to the meter specified by the "device" param
            resourceName = pht.c.create_string_buffer(self["device"].value.encode())
            try:
                result = self.tlPM.open(resourceName, True, True)
            except NameError as e:
                result = e
            # If the connection was not succesful, clean up and raise an exception
            if result:
                self.tlPM.close()
                del self.tlPM
                raise Exception(f"Powermeter init failed with code {result}")
            return 1

        @pzp.param.disconnect(self)
        def disconnect():
            if self.puzzle.debug:
                return 0
            if self._ensure(capture_exception=True):
                self.tlPM.close()
                del self.tlPM
            return 0

        @pzp.param.spinbox(self, 'wavelength', 633, visible=False)
        @self._ensure
        def set_wavelength(value):
            if self.puzzle.debug:
                return value
            self.tlPM.setWavelength(pht.c.c_double(value))
            # Don't return a value, so that the getter gets called
            # to double-check (values outside the correct range won't be set)

        @set_wavelength.set_getter(self)
        @self._ensure
        def get_wavelength():
            if self.puzzle.debug:
                return set_wavelength.value or 500
            value = pht.c.c_double()
            self.tlPM.getWavelength(0, pht.c.byref(value))
            return value.value

        @pzp.param.spinbox(self, 'avg_time', 10., visible=False)
        def set_avg_time(value):
            if self.puzzle.debug:
                return value
            self.imports.set_avg_time(value*1e-3)

        @set_avg_time.set_getter(self)
        def get_avg_time():
            if self.puzzle.debug:
                return set_avg_time.value or 1
            return self.imports.get_avg_time()*1e3

        @pzp.param.readout(self, "power", "{:.2e}")
        def read_power():
            if self.puzzle.debug:
                return 0

            return self.imports.power()

    def define_actions(self):
        @pzp.action.define(self, 'Zero')
        def zero(self):
            if self.puzzle.debug:
                return
            self.imports.zero()

        pzp.action.settings(self)

    #MARK: API setup
    def setup(self):
        pht.add_path_directory(
            pht.config(
                "tlmp_examples_python_directory",
                default=r"C:\Program Files (x86)\IVI Foundation\VISA\WinNT\TLPM\Examples\Python",
                description="the Python files only exist in the (x86) IVI installation directory",
                validator=pht.validator_path_exists
            )
        )
        pht.requirements({"TLPM": {
            "url": "https://pzp-hardware.readthedocs.io/en/latest/auto/pzp_hardware.thorlabs.powermeter.html#installation"
        }})
        from TLPM import TLPM
        pht.add_dll_directory(
            pht.config(
                "tlmp_dll_directory",
                default=r"C:\Program Files\IVI Foundation\VISA\Win64\Bin",
                description="look for the DLL matching your system - 32 bit in 'Program Files (x86)', 64 bit in 'Program Files'",
                validator=pht.validator_path_exists
            )
        )
        self._TLPM_class = TLPM

    @pzp.piece.ensurer
    def _ensure(self):
        if not self.puzzle.debug and not hasattr(self, "tlPM"):
            raise Exception("Powermeter not connected")
        return


if __name__ == "__main__":
    app = pzp.QApp()
    puzzle = pzp.Puzzle(name="Powermeter", debug=pht.debug_prompt())
    puzzle.add_piece("powermeter", Piece, 0, 0)
    puzzle.show()
    app.exec()