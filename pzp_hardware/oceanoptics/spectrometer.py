# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
:module_title:`OceanOptics Spectrometer`

Pieces for interacting with `OceanOptics spectrometers <https://www.oceanoptics.com/spectrometers/>`__
using the `python-seabreeze <https://python-seabreeze.readthedocs.io/en/latest/index.html>`__
library and the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework.

Example usage (see :ref:`getting-started` for more details on using Pieces in general)::

    import puzzlepiece as pzp
    from pzp_hardware.oceanoptics import spectrometer

    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("spectrometer", spectrometer.Piece, row=0, column=0)
    puzzle.show()
    app.exec()

Installation
------------
* If available, install OceanView from https://www.oceanoptics.com/software/ - this will
  install the drivers needed to talk to the spectrometer. Alternatively, follow
  https://python-seabreeze.readthedocs.io/en/latest/install.html for details on
  how to install the drivers with ``python-seabreeze``.
* Install the ``seabreeze`` library with pip, or wait to be prompted for automatic
  installation when first running the Piece.

Requirements
------------
.. pzp_requirements:: pzp_hardware.oceanoptics.spectrometer

Available Pieces
----------------
"""

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
from pyqtgraph.Qt import QtWidgets
import pyqtgraph as pg
import numpy as np


class Piece(pzp.Piece):
    """
    A very basic Piece for getting values and wavelengths from an OceanOptics
    spectrometer. Contributions welcome to expose more options!

    .. image:: ../images/pzp_hardware.oceanoptics.spectrometer.Piece.png
    """
    custom_horizontal = True

    def define_params(self):
        @pzp.param.dropdown(self, "spectrometer", "")
        def list_spectrometers():
            if not self.puzzle.debug:
                return self.imports.list_devices()

        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                return 1
            self.spec = self.imports.Spectrometer.from_serial_number(
                self.params['spectrometer'].get_value().split(":")[1][:-1]
            )

        @pzp.param.disconnect(self)
        def disconnect():
            if self.puzzle.debug:
                return 0
            if self._ensure(capture_exception=True):
                self.spec.close()
            return 0

        pzp.param.array(self, 'wls', False)(None)

        @pzp.param.array(self, 'values')
        @self._ensure
        def values():
            if self.puzzle.debug:
                self.params['wls'].set_value(np.arange(100))
                return np.random.random(100)
            wls, vals = self.spec.spectrum()
            self.params['wls'].set_value(wls)
            return vals

    @pzp.piece.ensurer
    def _ensure(self):
        if not self.puzzle.debug and not hasattr(self, 'spec'):
            raise("Spectrometer not connected")

    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        # The thread runs self.get_value repeatedly, which updates the plot through the
        # Signal connection defined below
        self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle, self.params['values'].get_value, 0.05)
        layout.addWidget(self.timer)

        self.pw = pg.PlotWidget()
        layout.addWidget(self.pw)
        self.plot = self.pw.getPlotItem()
        self.plot_line = self.plot.plot([0], [0], symbol='o', symbolSize=3)

        # Update the plot when the values change (through a CallLater, so the
        # update is done only when the GUI loop is running)
        def update_plot():
            self.plot_line.setData(
                self.params['wls'].value,
                self.params['values'].value
            )
        update_later = pzp.threads.CallLater(update_plot)
        self.params['values'].changed.connect(update_later)

        return layout

    def setup(self):
        pht.requirements(
            {
                "seabreeze": {
                    "pip": "seabreeze",
                    "url": "https://python-seabreeze.readthedocs.io/en/latest/install.html"
                }
            }
        )
        import seabreeze.spectrometers
        self.imports = seabreeze.spectrometers


if __name__ == "__main__":
    app = pzp.QApp()
    puzzle = pzp.Puzzle(name="OceanOptics", debug=pht.debug_prompt())
    puzzle.add_piece("spectrometer", Piece, 0, 0)
    puzzle.show()
    app.exec()