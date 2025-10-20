# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
:module_title:`Topas OPA control`

Pieces for interacting with
`Topas Optical Parametric Amplifiers <https://lightcon.com/products/wavelength-tunable-sources/>`__
using the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework.

Example usage (see :ref:`getting-started` for more details on using Pieces in general)::

    import puzzlepiece as pzp
    from pzp_hardware.lightcon import topas

    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("topas", topas.Piece, row=0, column=0, param_defaults={
        "address": "http://127.0.0.1:8000/12030" # optionally specify a default IP address
    })
    puzzle.show()
    app.exec()

Installation
------------
* Find the IP address and port corresponding to the Topas Server. This should be listed
  in the Topas control app, and will be of the form "http://127.0.0.1:8000/12030" if the
  Topas Server is running on the same computer as the Piece. Note the final part of the
  URL is the OPA's serial number.
* Install the ``requests`` library, or wait to be prompted for automatic installation when first
  running the Piece.
* Paste the network address and port you found in the "address" text box, or see above for setting it as the default
  in ``add_piece``.

Requirements
------------
.. pzp_requirements:: pzp_hardware.generic.hw_bases.http

Available Pieces
----------------
"""

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
from pyqtgraph.Qt import QtWidgets, QtCore

from pzp_hardware.generic.hw_bases import http

class Piece(http.Base):
    """
    Topas OPA control Piece.

    .. image:: ../images/pzp_hardware.lightcon.topas.Piece.png
    """
    default_address = "http://127.0.0.1:8000/12030"
    _api = "/v0/PublicAPI"

    def define_params(self):
        super().define_params()
        address = self["address"]

        @pzp.param.spinbox(self, 'wl', 633)
        def set_wavelength(value):
            if self.puzzle.debug:
                return value

            r = self.rq.put(f'{address.value}{self._api}/Optical/WavelengthControl/SetWavelength', json={'Interaction': '*', 'Wavelength': value})
            self.check_response(r)
            return value

        @set_wavelength.set_getter(self)
        def get_wavelength(self):
            if self.puzzle.debug:
                return 633

            r = self.rq.get(f'{address.value}{self._api}/Optical/WavelengthControl/Output/Wavelength')
            self.check_response(r)
            return int(r.text)

        @pzp.param.checkbox(self, 'shutter', 0)
        def shutter(self, value):
            if self.puzzle.debug:
                return value

            endpoint = '/OpenShutter' if value else '/CloseShutter'

            r = self.rq.put(f'{address.value}{self._api}/ShutterInterlock' + endpoint)
            self.check_response(r)

            return value

        @shutter.set_getter(self)
        def check_shutter(self):
            if self.puzzle.debug:
                return 1

            r = self.rq.get(f'{address.value}{self._api}/ShutterInterlock/IsShutterOpen')
            self.check_response(r)

            return r.text == 'true'


    def define_actions(self):
        @pzp.action.define(self, 'Close shutter', QtCore.Qt.Key.Key_F5, visible=False)
        def panic(self):
            self['shutter'].set_value(0)

if __name__ == "__main__":
    app = pzp.QApp()
    puzzle = pzp.Puzzle(name="Topas", debug=pht.debug_prompt())
    puzzle.add_piece("topas", Piece, 0, 0)
    puzzle.show()
    app.exec()