import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
from pyqtgraph.Qt import QtCore

from pzp_hardware.generic.hw_bases import serial

class Piece(serial.Base):
    def define_params(self):
        super().define_params()
        
        def get_state():
            self.port.write(b'ens?\r')
            self.port.read_until(b'\r')
            return int(self.port.read_until(b'\r')[0]) - 48

        @pzp.param.checkbox(self, 'open', 0)
        @self._ensure
        def open(self, value):
            if self.puzzle.debug:
                return value
            # Check state
            open = get_state()
            # Flip if state is wrong
            if open == value:
                return value
            else:
                self.port.write(b'ens\r')
                self.port.read_until(b'\r')
                return value
            
        @open.set_getter(self)
        @self._ensure
        def get_open(self):
            if self.puzzle.debug:
                return self['open'].value or 0
            # Get state
            return get_state()
        
    def define_actions(self):
        @pzp.action.define(self, 'Close shutter', QtCore.Qt.Key.Key_F4, visible=False)
        def toggle(self):
            self['open'].set_value(not self.params['open'].value)

            
if __name__ == "__main__":
    from pyqtgraph.Qt import QtWidgets
    app = QtWidgets.QApplication([])
    puzzle = pzp.Puzzle(app, "Shutter", debug=pht.debug_prompt())
    puzzle.add_piece("shutter", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()