# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

"""
:module_title:`Patterns`

Display a set of test patterns (circle, square, checkerboard) on any Piece with an array parameter
(DMD, SLM, etc).

Example usage (see :ref:`getting-started` for more details on using Pieces in general)::

    import puzzlepiece as pzp
    from pzp_hardware.vialux import dmd
    from pzp_hardware.generic.patterning import patterns

    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("dmd", dmd.Piece, row=0, column=0)
    puzzle.add_piece("patterns", patterns.Piece, row=0, column=1, param_defaults={
        "destination": "dmd:image"
    })
    puzzle.show()
    app.exec()
"""

import puzzlepiece as pzp
import numpy as np
from pyqtgraph.Qt import QtWidgets

class Piece(pzp.Piece):
    """
    Piece for displaying test patterns. The "destination" param should be a string
    reference to an ArrayParam in the format ``piece_name:param_name``. The destination
    must already contain an image, so that its shape can be inspected.

    .. image:: ../images/pzp_hardware.generic.patterning.patterns.Piece.png
    """
    def define_params(self):
        pzp.param.text(self, "destination", "dmd:image", visible=False)(None)
        pzp.param.spinbox(self, 'radius', 50, v_min=1)(None)
        pzp.param.slider(
            self, "brightness", 255,
            v_min=0, v_max=255, v_step=1,
            visible=False
        )(None)
        pzp.param.checkbox(self, 'invert', 0)(None)
        pzp.param.checkbox(self, 'stretch', 0, visible=False)(None).set_group("Stretch")
        pzp.param.spinbox(
            self, 'factor', 1.,
            v_min=.1, v_max=10., v_step=.05,
            visible=False
        )(None).set_group("Stretch")

    def define_actions(self):
        @pzp.action.define(self, 'Display')
        def display(self):
            destination = pzp.parse.parse_params(self["destination"].value, self.puzzle)[0]
            radius = self.params['radius'].get_value()
            canvas = np.zeros(destination.value.shape, np.uint8)
            function = [x.dmd_draw_function for x in self._radio_buttons.buttons() if x.isChecked()][0]
            function(canvas, radius)
            if self.params['invert'].value:
                canvas = - (canvas - 255)
            canvas[canvas>0] = self["brightness"].value
            destination.set_value(canvas)

        pzp.action.settings(self)

    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        self._radio_buttons = QtWidgets.QButtonGroup()
        for i, f in enumerate((self.circle, self.square, self.checkerboard)):
            button = QtWidgets.QRadioButton(f.__name__)
            button.dmd_draw_function = f
            if not i:
                button.setChecked(True)
            button.clicked.connect(lambda _: self.actions['Display']())
            layout.addWidget(button)
            self._radio_buttons.addButton(button)

        self.params['radius'].changed.connect(self.actions['Display'])
        self.params['brightness'].changed.connect(self.actions['Display'])
        self.params['invert'].changed.connect(self.actions['Display'])
        self.params['factor'].changed.connect(self.actions['Display'])
        # self.params['stretch'].changed.connect(self.actions['Display'])
        layout.addStretch()

        return layout

    def circle(self, canvas, radius):
        x, y = canvas.shape
        xx, yy = np.mgrid[:x, :y]
        factor = self["factor"].value if self["stretch"].value else 1
        circle = np.sqrt(((xx - x/2) / factor)**2 + (yy - y/2)**2)
        canvas[circle <= radius] = 255

    def square(self, canvas, radius):
        x, y = canvas.shape
        factor = self["factor"].value if self["stretch"].value else 1
        A, B, C, D = x//2 - int(radius*factor), x//2 + int(radius*factor), y//2 - radius, y//2 + radius
        canvas[A:B, C:D] = 255

    def checkerboard(self, canvas, radius):
        x, y = canvas.shape
        board = np.asarray([[0, 255], [255, 0]])
        factor = self["factor"].value if self["stretch"].value else 1
        board = np.kron(board, np.ones((int(radius*factor), radius)))
        canvas[:] = np.pad(board, ((0, x-2*int(radius*factor)), (0, y-2*radius)), mode='wrap')

if __name__ == "__main__":
    from puzzlepiece.extras import hardware_tools as pht
    app = pzp.QApp()
    puzzle = pzp.Puzzle(name="Patterns", debug=True)
    puzzle.add_piece("patterns", Piece, 0, 0)
    puzzle.show()
    app.exec()