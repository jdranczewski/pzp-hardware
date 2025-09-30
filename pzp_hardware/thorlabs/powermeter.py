import puzzlepiece as pzp
from pyqtgraph.Qt import QtWidgets

class Piece(pzp.Piece):
    def __init__(self, puzzle):
        super().__init__(puzzle)

    def define_params(self):
        @pzp.param.checkbox(self, "connected", 0)
        def connect(self, value):
            if self.puzzle.debug:
                return 1
            
            if value:
                self.imports.connect()
                return 1
            else:
                self.imports.disconnect()
                return 0

        @pzp.param.spinbox(self, 'wavelength', 1100, v_min=500, v_max=1800)
        def set_wavelength(self, value):
            if self.puzzle.debug:
                return value
            return self.imports.set_wavelength(value)
            
        @pzp.param.spinbox(self, 'avg_time', 10.)
        def set_avg_time(self, value):
            if self.puzzle.debug:
                return value
            self.imports.set_avg_time(value*1e-3)
            
        @set_avg_time.set_getter(self)
        def get_avg_time(self):
            if self.puzzle.debug:
                return 1
            return self.imports.get_avg_time()*1e3

    def define_readouts(self):
        @pzp.readout.define(self, "power", "{:.2e}")
        def read_power(self):
            if self.puzzle.debug:
                return 0
            
            return self.imports.power()
        
    def define_actions(self):
        @pzp.action.define(self, 'Zero')
        def zero(self):
            if self.puzzle.debug:
                return
            self.imports.zero()
            
    def setup(self):
        import _powermeter
        self.imports = _powermeter

    def handle_close(self, event):
        if not self.puzzle.debug and self.params['connected'].get_value():
            self.elevate()
            self.params['connected'].set_value(0)
            self.puzzle.process_events()

def main():
    app = QtWidgets.QApplication([])

    window = pzp.Puzzle(app, "Power meter", debug=True)
    window.add_piece("powermeter", Piece(window), 0, 0)
    window.show()

    app.exec()

if __name__ == "__main__":
    main()