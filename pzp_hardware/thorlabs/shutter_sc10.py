# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
:module_title:`ThorLabs SC10 shutter controller`

Pieces for interacting with the
`ThorLabs SC10 shutter controller <https://www.thorlabs.com/thorProduct.cfm?partNumber=SC10>`__
using the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework and
`serial communication <https://www.artisantg.com/info/ThorLabs_SC10_Manual_202441514442.pdf#page=16>`__.

Example usage (see :ref:`getting-started` for more details on using Pieces in general)::

    import puzzlepiece as pzp
    from pzp_hardware.thorlabs import shutter_sc10

    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("camera", shutter_sc10.Piece, row=0, column=0)
    puzzle.show()
    app.exec()

Requirements
------------
.. pzp_requirements:: pzp_hardware.generic.hw_bases.serial

Available Pieces
----------------
"""

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
from pyqtgraph.Qt import QtCore

from pzp_hardware.generic.hw_bases import serial

class Piece(serial.Base):
    """
    Piece for controlling a shutter through the ThorLabs SC10 shutter controller.

    .. image:: ../images/pzp_hardware.thorlabs.shutter_sc10.Piece.png
    """
    def define_params(self):
        super().define_params()

        def get_state():
            self.port.write(b'ens?\r')
            self.port.read_until(b'\r')
            return int(self.port.read_until(b'\r')[0]) - 48

        @pzp.param.checkbox(self, 'open', 0)
        @self._ensure
        def open(self, value):
            if self.puzzle.debug:
                return value
            # Check state
            open = get_state()
            # Flip if state is wrong
            if open == value:
                return value
            else:
                self.port.write(b'ens\r')
                self.port.read_until(b'\r')
                return value

        @open.set_getter(self)
        @self._ensure
        def get_open(self):
            if self.puzzle.debug:
                return self['open'].value or 0
            # Get state
            return get_state()

    def define_actions(self):
        @pzp.action.define(self, 'Close shutter', QtCore.Qt.Key.Key_F4, visible=False)
        def toggle(self):
            self['open'].set_value(not self.params['open'].value)


if __name__ == "__main__":
    app = pzp.QApp()
    puzzle = pzp.Puzzle(name="Shutter", debug=pht.debug_prompt())
    puzzle.add_piece("shutter", Piece, 0, 0)
    puzzle.show()
    app.exec()