# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
from pyqtgraph.Qt import QtCore

class Base(pzp.Piece):
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
            self.port = self.serial.Serial(self.params['port'].get_value(), 9600, timeout=3)

        @pzp.param.disconnect(self)
        def disconnect():
            if self.puzzle.debug:
                return 0
            if self._ensure(capture_exception=True):
                self.port.close()

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
