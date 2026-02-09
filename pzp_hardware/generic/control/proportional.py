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
    param_wrap=2

    def define_params(self):
        pzp.param.text(self, 'control', 'dummy:in')(None)
        pzp.param.text(self, 'measure', 'dummy:out')(None)
        pzp.param.spinbox(self, "unit_10e", 0, visible=False)(None)
        pzp.param.spinbox(self, 'goal', 1., v_step=.1)(None)
        pzp.param.spinbox(self, 'tolerance', 0.1, v_step=.1, visible=False)(None)
        pzp.param.spinbox(self, "good_to_stop", 5,  visible=False)(None)
        pzp.param.spinbox(self, "step_loop_limit", 100,  visible=False)(None)

        pzp.param.spinbox(self, "prop", 0.0100, v_step=.01)(None)
        self["prop"].input.setDecimals(4)
        @pzp.param.spinbox(self, "dt", .1, visible=False)
        def dt(value):
            self.timer.sleep = value

    def define_actions(self):
        @pzp.action.define(self, "Step")
        def step():
            value = pzp.parse.parse_params(self["measure"].value, self.puzzle)[0].get_value()
            output = pzp.parse.parse_params(self["control"].value, self.puzzle)[0].get_value()
            goal = self["goal"].value * 10**self["unit_10e"].value
            error = goal - value
            output += self["prop"].value * error
            pzp.parse.parse_params(self["control"].value, self.puzzle)[0].set_value(output)
            new_value = pzp.parse.parse_params(self["measure"].value, self.puzzle)[0].get_value()
            self.update_plot.emit(output, new_value)
            return goal - new_value

        @pzp.action.define(self, "Step loop")
        def step_loop():
            self.stop = False
            count_good = 0
            for i in range(self["step_loop_limit"].value):
                error = self.actions["Step"]()
                self.puzzle.process_events()
                tolerance = self.params['tolerance'].get_value() * 10**self["unit_10e"].value
                if abs(error) < tolerance:
                    count_good += 1
                else:
                    count_good = 0
                if count_good >= self["good_to_stop"].value or self.stop:
                    break

        @pzp.action.define(self, "Clear")
        def clear():
            self._ins = []
            self._outs = []
            self._line_in.setData(self._ins)
            self._line_out.setData(self._outs)

        pzp.action.settings(self)

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
        self._line_in = line_in = plot_in.plot()
        plot_out = self.gl.addPlot(1, 0)
        self._line_out = line_out = plot_out.plot()

        plot_out.addItem(
            plot_region := pg.LinearRegionItem(
                values=[self["goal"].value-self["tolerance"].value, self["goal"].value+self["tolerance"].value],
                orientation='horizontal', movable=False
            )
        )
        plot_out.addItem(il := pg.InfiniteLine(self["goal"].value, 0))

        def update_items():
            il.setValue(self["goal"].value)
            plot_region.setRegion((self["goal"].value-self["tolerance"].value, self["goal"].value+self["tolerance"].value))
        self["goal"].changed.connect(update_items)
        self["tolerance"].changed.connect(update_items)

        self._ins = []
        self._outs = []

        def add_point(a, b):
            self._ins.append(a)
            self._outs.append(b / 10**self["unit_10e"].value)
            line_in.setData(self._ins)
            line_out.setData(self._outs)
        self.update_plot.connect(add_point)

        return layout


if __name__ == "__main__":
    app = pzp.QApp([])
    puzzle = pzp.Puzzle()
    puzzle.add_piece("dummy", Dummy, 0, 0)
    puzzle.add_piece("proportional", Piece, 1, 0)
    puzzle.show()
    app.exec()