# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
:module_title:`Pharos laser control`

Pieces for interacting with
`Pharos lasers <https://lightcon.com/products/pharos-femtosecond-lasers/>`__
using the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework.

Example usage (see :ref:`getting-started` for more details on using Pieces in general)::

    import puzzlepiece as pzp
    from pzp_hardware.lightcon import pharos

    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("pharos", pharos.Piece, row=0, column=0, param_defaults={
        "address": "http://123.456.789.1:20022" # optionally specify a default IP address
    })
    puzzle.show()
    app.exec()

Installation
------------
* Find the IP address and port corresponding to the Pharos API.

  - On older Pharos systems, this will be local (so "http://127.0.0.1:20022" for example) if the
    control app is running on the same computer as the Piece. If the Pharos control app is running
    on a different computer, it will be that computer's IP and the same port.
  - On newer Pharos systems, this will be the IP address of the laser controller, so the IP you use
    to access the web-based control panel. You can select "REST API" from the top menu, and note the IP
    address and port in your browser's address bar.

* Install the ``requests`` library with pip, or wait to be prompted for automatic installation when first
  running the Piece.
* Paste the IP address and port you found in the "address" text box, or see above for setting it as the default
  in ``add_piece``.

Requirements
------------
.. pzp_requirements:: pzp_hardware.generic.hw_bases.http

Available Pieces
----------------
"""

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
from pyqtgraph.Qt import QtWidgets

from pzp_hardware.generic.hw_bases import http


class Piece(http.Base):
    """
    Pharos laser control Piece.

    .. image:: ../images/pzp_hardware.lightcon.pharos.Piece.png
    """
    _api = "/v0"
    default_address = "http://127.0.0.1:20022"

    def define_params(self):
        super().define_params()
        address = self["address"]

        @pzp.param.readout(self, "full_state", visible=False)
        def basic():
            if self.puzzle.debug:
                return ""

            r = self.rq.get(f"{address.value}{self._api}/Basic")
            self.check_response(r)
            state = str(r.json()).replace(",", ",\n")
            return state

        @pzp.param.readout(self, "state", visible=True)
        def basic():
            if self.puzzle.debug:
                return ""

            r = self.rq.get(f"{address.value}{self._api}/Basic")
            self.check_response(r)
            return r.json()["GeneralStatus"]

        @pzp.param.checkbox(self, "output", 0)
        def output(value):
            if self.puzzle.debug:
                return value

            if value:
                r = self.rq.post(f"{address.value}{self._api}/Basic/EnableOutput")
            else:
                r = self.rq.post(f"{address.value}{self._api}/Basic/CloseOutput")
            self.check_response(r)
            return value

        @output.set_getter(self)
        def output():
            if self.puzzle.debug:
                return output.value or 0

            r = self.rq.get(f"{address.value}{self._api}/Basic/IsOutputEnabled")
            self.check_response(r)
            return r.text == "true"

        @pzp.param.spinbox(self, "divider", 1, v_min=1)
        def divider(value):
            if self.puzzle.debug:
                return value

            r = self.rq.put(f"{address.value}{self._api}/Basic/TargetPpDivider", str(value))
            self.check_response(r)
            return value

        @divider.set_getter(self)
        def divider():
            if self.puzzle.debug:
                return 1

            r = self.rq.get(f"{address.value}{self._api}/Basic/TargetPpDivider")
            self.check_response(r)
            return int(r.text)

    def define_actions(self):
        super().define_actions()
        address = self["address"]

        @pzp.action.define(self, "Full state")
        def state():
            state = self.params["full_state"].get_value()

            box = QtWidgets.QMessageBox()
            box.setText(state)
            box.exec()

        @pzp.action.define(self, "Standby")
        def shutdown(confirm=True):
            if confirm:
                mb = QtWidgets.QMessageBox
                if (
                    mb.question(
                        self.puzzle, "Shutdown", "Do you want to go to standby?"
                    )
                    != mb.StandardButton.Yes
                ):
                    return

            if self.puzzle.debug:
                return

            r = self.rq.post(f"{address.value}{self._api}/Basic/GoToStandby")
            self.check_response(r)


if __name__ == "__main__":
    app = pzp.QApp()
    puzzle = pzp.Puzzle(name="Pharos", debug=pht.debug_prompt())
    puzzle.add_piece("pharos", Piece, 0, 0)
    puzzle.show()
    app.exec()
