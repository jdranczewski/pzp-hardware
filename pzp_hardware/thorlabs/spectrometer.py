import puzzlepiece as pzp
from pyqtgraph.Qt import QtWidgets
import pyqtgraph as pg
import numpy as np


class Piece(pzp.Piece):
    def __init__(self, puzzle, custom_horizontal=True, *args, **kwargs):
        super().__init__(puzzle, custom_horizontal, *args, **kwargs)
    
    def define_params(self):
        @pzp.param.dropdown(self, "spectrometer", "")
        def list_spectrometers(self):
            if not self.puzzle.debug:
                return self.imports.list_devices()
            
        @pzp.param.checkbox(self, "connected", 0)
        def connect(self, value):
            if self.puzzle.debug:
                return 1
            # Check if we're currently connected by seing what the state of the checkbox was
            current_value = self.params['connected'].value

            if value and not current_value:
                self.spec = self.imports.Spectrometer.from_serial_number(
                    self.params['spectrometer'].get_value().split(":")[1][:-1]
                )
                return 1
            elif current_value:
                # Disconnect
                if self._ensure(capture_exception=True):
                    self.spec.close()
                return 0
            
        pzp.param.array(self, 'wls', False)(None)

        @pzp.param.array(self, 'values')
        @self._ensure
        def values(self):
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

        # The thread runs self.get_value repeatedly, which returns a value...
        self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle, self.params['values'].get_value, 0.05)
        layout.addWidget(self.timer)

        self.pw = pg.PlotWidget()
        layout.addWidget(self.pw)
        self.plot = self.pw.getPlotItem()
        self.plot_line = self.plot.plot([0], [0], symbol='o', symbolSize=3)

        def update_plot():
            self.plot_line.setData(
                self.params['wls'].value,
                self.params['values'].value
            )
        self.params['values'].changed.connect(update_plot)

        return layout
    
    def call_stop(self):
        self.timer.stop()

    def setup(self):
        import seabreeze.spectrometers
        self.imports = seabreeze.spectrometers

    def handle_close(self, event):
        self.params['connected'].set_value(0)


if __name__ == "__main__":
    app = pzp.QApp([])
    puzzle = pzp.Puzzle(app, "Oceanview", debug=False)
    puzzle.add_piece("oceanview", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()