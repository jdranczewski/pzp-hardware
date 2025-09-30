import puzzlepiece as pzp
import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets, QtCore

class Dummy(pzp.Piece):
    def define_params(self):
        pzp.param.spinbox(self, "in", 0.)(None)
        pzp.param.spinbox(self, "mult", 10.)(None)
        pzp.param.spinbox(self, "rand", .1)(None)
        @pzp.param.readout(self, "out", format="{:.4f}")
        def out():
            return self["in"].value * self["mult"].value + np.random.random() * self["rand"].value
        
class Piece(pzp.Piece):
    update_plot = QtCore.Signal(float, float)

    def define_params(self):
        pzp.param.text(self, 'control', 'dummy:in')(None)
        pzp.param.text(self, 'measure', 'dummy:out')(None)
        pzp.param.spinbox(self, 'goal', 1.)(None)

        pzp.param.spinbox(self, "prop", 0., v_step=.01)(None)
        self["prop"].input.setDecimals(4)
        @pzp.param.spinbox(self, "dt", .1)
        def dt(value):
            self.timer.sleep = value

    def param_layout(self, wrap=2):
        return super().param_layout(wrap)

    def define_actions(self):
        self._prev_error = 0.
        self._integral = 0.
        @pzp.action.define(self, "Step")
        def step():
            value = pzp.parse.parse_params(self["measure"].value, self.puzzle)[0].get_value()
            output = pzp.parse.parse_params(self["control"].value, self.puzzle)[0].get_value()
            error = self["goal"].value - value
            output += self["prop"].value * error
            pzp.parse.parse_params(self["control"].value, self.puzzle)[0].set_value(output)
            self.update_plot.emit(output, value)

        @pzp.action.define(self, "Clear")
        def clear():
            self._ins = []
            self._outs = []
            self._prev_error = 0
            self._integral = 0

    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        # Add a PuzzleTimer for live view
        self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle, self.actions['Step'], 0.1)
        self["dt"].set_value()
        layout.addWidget(self.timer)

        # Make the plots
        self.gl = pg.GraphicsLayoutWidget()
        layout.addWidget(self.gl)
        
        plot_in = self.gl.addPlot(0, 0)
        line_in = plot_in.plot()
        plot_out = self.gl.addPlot(1, 0)
        line_out = plot_out.plot()
        plot_out.addItem(il := pg.InfiniteLine(1, 0))
        self["goal"].changed.connect(lambda: il.setValue(self["goal"].value))

        self._ins = []
        self._outs = []

        def add_point(a, b):
            self._ins.append(a)
            self._outs.append(b)
            line_in.setData(self._ins)
            line_out.setData(self._outs)
        self.update_plot.connect(add_point)

        return layout


if __name__ == "__main__":
    app = pzp.QApp([])
    puzzle = pzp.Puzzle()
    puzzle.add_piece("dummy", Dummy, 0, 0)
    puzzle.add_piece("pid", Piece, 1, 0)
    puzzle.show()
    app.exec()