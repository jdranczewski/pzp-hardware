import puzzlepiece as pzp
from pyqtgraph.Qt import QtCore

class Piece(pzp.Piece):
    def define_params(self):
        pzp.param.text(self, 'port', 'COM7', visible=False)(None)

        @pzp.param.checkbox(self, 'connected', 0)
        def connected(self, value):
            if self.puzzle.debug:
                return 1
            
            if value:
                # Connect
                self.port = self.serial.Serial(self.params['port'].get_value(), 9600, timeout=3)
            else:
                # Disconnect if we're connected
                if self.ensure_connected(capture_exception=True):
                    self.port.close()

        def get_state():
            self.port.write(b'ens?\r')
            self.port.read_until(b'\r')
            return int(self.port.read_until(b'\r')[0]) - 48

        @pzp.param.checkbox(self, 'open', 0)
        @self.ensure_connected
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
        @self.ensure_connected
        def get_open(self):
            if self.puzzle.debug:
                return self.params['open'].value
            # Get state
            return get_state()
        
    def define_actions(self):
        @pzp.action.define(self, 'Close shutter', QtCore.Qt.Key.Key_F4, visible=False)
        def toggle(self):
            self.params['open'].set_value(not self.params['open'].value)

    @pzp.piece.ensurer
    def ensure_connected(self):
        if not self.puzzle.debug:
            if hasattr(self, 'port') and self.port.is_open:
                return
            raise Exception('Shutter not connected')
    
    def setup(self):
        import serial
        self.serial = serial

    def handle_close(self, event):
        self.params['connected'].set_value(0)
        super().handle_close(event)
            
if __name__ == "__main__":
    from pyqtgraph.Qt import QtWidgets
    app = QtWidgets.QApplication([])
    puzzle = pzp.Puzzle(app, "Shutter", debug=True)
    puzzle.add_piece("shutter", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()