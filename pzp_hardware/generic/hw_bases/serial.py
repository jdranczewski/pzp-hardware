# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
:module_title:`Serial Piece`

A base Piece for implementing serial interface communication
using the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework.

Defines a port selector param and a "connected" param. ``self.port`` is a pySerial
`Serial <https://pyserial.readthedocs.io/en/latest/pyserial_api.html#serial.Serial>`__
object that can be used to interact with the port. An ensurer is provided
to make sure the user has connected to a serial port before performing operations.

Example implementation::

    import puzzlepiece as pzp
    from pzp_hardware.generic.hw_bases import serial

    class Piece(serial.Base):
        serial_baud = 115200 # change the default baud rate if needed

        def define_params(self):
            super().define_params()

            @pzp.param.checkbox(self, 'open', 0)
            @self._ensure
            def open(value):
                if self.puzzle.debug:
                    return value
                self.port.write(b'ens\r')
                self.port.read_until(b'\r')
                return value

For a full Piece implemented using this base, see :class:`pzp_hardware.thorlabs.shutter_sc10.Piece`.

Requirements
------------
.. pzp_requirements:: pzp_hardware.generic.hw_bases.serial
"""

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht


class Base(pzp.Piece):
    """
    .. image:: ../images/pzp_hardware.generic.hw_bases.serial.Base.png

    Base Piece implementing serial communication.
    """

    #: Baud rate for the serial connection (set in your child class)
    serial_baud = 9600
    #: Timeout for the serial connection (set in your child class)
    serial_timeout = 3
    #: A pySerial port (only available when connected)
    port = None
    #: A reference to the pySerial library (if not in debug mode)
    serial = None

    def define_params(self):
        @pzp.param.dropdown(self, "port", "")
        def get_ports():
            if self.puzzle.debug:
                return []
            return [port.device for port in self._pyserial_list_ports.comports()]

        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                return 1
            self.port = self.serial.Serial(
                self.params['port'].get_value(),
                self.serial_baud,
                timeout=self.serial_timeout
            )

        @pzp.param.disconnect(self)
        def disconnect():
            if self.puzzle.debug:
                return 0
            if self._ensure(capture_exception=True):
                self.port.close()
                del self.port

    @pzp.piece.ensurer
    def _ensure(self):
        if not self.puzzle.debug:
            if hasattr(self, 'port') and self.port.is_open:
                return
            raise Exception('Shutter not connected')

    def setup(self):
        pht.requirements({
            "serial": {
                "pip": "pyserial",
                "url": "https://pyserial.readthedocs.io/en/latest/pyserial.html#installation"
            }
        })
        import serial
        self.serial = serial
        from serial.tools import list_ports
        self._pyserial_list_ports = list_ports
