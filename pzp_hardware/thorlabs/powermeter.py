import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
from pyqtgraph.Qt import QtWidgets

class Piece(pzp.Piece):
    def __init__(self, puzzle):
        super().__init__(puzzle)

    def define_params(self):
        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                return 1
            self.imports.connect()
            return 1
        
        @pzp.param.disconnect(self)
        def disconnect():
            if self.puzzle.debug:
                return 0
            self.imports.disconnect()
            return 0

        @pzp.param.spinbox(self, 'wavelength', 1100, v_min=500, v_max=1800, visible=False)
        def set_wavelength(value):
            if self.puzzle.debug:
                return value
            return self.imports.set_wavelength(value)
        
        @set_wavelength.set_getter(self)
        def get_wavelength():
            if self.puzzle.debug:
                return set_wavelength.value or 500
            return self.imports.get_wavelength()
            
        @pzp.param.spinbox(self, 'avg_time', 10., visible=False)
        def set_avg_time(value):
            if self.puzzle.debug:
                return value
            self.imports.set_avg_time(value*1e-3)
            
        @set_avg_time.set_getter(self)
        def get_avg_time():
            if self.puzzle.debug:
                return set_avg_time.value or 1
            return self.imports.get_avg_time()*1e3

        @pzp.param.readout(self, "power", "{:.2e}")
        def read_power():
            if self.puzzle.debug:
                return 0
            
            return self.imports.power()
        
    def define_actions(self):
        @pzp.action.define(self, 'Zero')
        def zero(self):
            if self.puzzle.debug:
                return
            self.imports.zero()

        pzp.action.settings(self)
            
    def setup(self):
        import _powermeter
        self.imports = _powermeter


if __name__ == "__main__":
    app = pzp.QApp()
    puzzle = pzp.Puzzle(name="Powermeter", debug=pht.debug_prompt())
    puzzle.add_piece("powermeter", Piece, 0, 0, param_defaults={
        "wavelength": 633
    })
    puzzle.show()
    app.exec()