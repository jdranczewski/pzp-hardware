import puzzlepiece as pzp
import numpy as np
from pyqtgraph.Qt import QtWidgets

class Piece(pzp.Piece):
    def define_params(self):
        pzp.param.spinbox(self, 'radius', 50, v_min=1)(None)
        pzp.param.checkbox(self, 'invert', 0)(None)
        pzp.param.spinbox(self, 'factor', 1., v_min=.1, v_max=10., v_step=.05)(None)
        pzp.param.checkbox(self, 'stretch', 0)(None)

    def define_actions(self):
        @pzp.action.define(self, 'Display')
        def display(self):
            dmd = self.puzzle['dmd']
            radius = self.params['radius'].get_value()
            canvas = np.zeros((dmd.size_y, dmd.size_x))
            function = [x.dmd_draw_function for x in self._radio_buttons.buttons() if x.isChecked()][0]
            function(canvas, radius)
            if self.params['invert'].value:
                canvas = - (canvas - 255)
            dmd.params['image'].set_value(canvas)

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
    import dmd
    app = QtWidgets.QApplication([])
    puzzle = pzp.Puzzle(app, "Patterns", debug=True)
    puzzle.add_piece("dmd", dmd.Piece(puzzle), 0, 0)
    puzzle.add_piece("patterns", Piece(puzzle), 0, 1)
    puzzle.show()
    app.exec()