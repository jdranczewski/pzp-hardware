import puzzlepiece as pzp
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets

class Piece(pzp.Piece):
    def define_params(self):
        pzp.param.text(self, 'control', '')(None)
        pzp.param.text(self, 'measure', '')(None)
        pzp.param.spinbox(self, 'goal', 1.)(None)
        pzp.param.spinbox(self, 'tolerance', 0.)(None)
        pzp.param.spinbox(self, 'prop', 1.)(None)
        pzp.param.spinbox(self, 'unit', 1)(None)

    def define_actions(self):
        @pzp.action.define(self, 'Run')
        def run(self):
            unit = self.params['unit'].get_value()
            goal = self.params['goal'].get_value() * 10**unit
            tolerance = self.params['tolerance'].get_value() * 10**unit
            prop = self.params['prop'].get_value() * 10**(-unit)
            control = pzp.parse.parse_params(self.params['control'].get_value(), self.puzzle)[0]
            measure = pzp.parse.parse_params(self.params['measure'].get_value(), self.puzzle)[0]

            self.plot_goal.setValue(goal)
            self.plot_region.setRegion([goal-tolerance, goal+tolerance])

            x_values = []
            values = []
            self.stop = False
            count_good = 0
            for i in range(100):
                value = measure.get_value()
                current = control.get_value()
                x_values.append(current)
                values.append(value)
                self.plot_line.setData(x_values, values)
                self.puzzle.process_events()
                diff = value - goal
                if abs(diff) < tolerance:
                    count_good += 1
                else:
                    count_good = 0
                if count_good >= 5 or self.stop:
                    break
                control.set_value(current + diff*prop)

    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        self.pw = pg.PlotWidget()
        layout.addWidget(self.pw)
        self.plot = self.pw.getPlotItem()
        self.plot_line = self.plot.plot([], [], symbol='o', symbolSize=3)
        self.plot_region = pg.LinearRegionItem(values=[-1, 1], orientation='horizontal', movable=False)
        self.plot_goal = pg.InfiniteLine(0, angle=0)
        self.plot.addItem(self.plot_region)
        self.plot.addItem(self.plot_goal)

        return layout