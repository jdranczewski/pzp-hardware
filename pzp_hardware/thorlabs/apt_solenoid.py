import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
from qtpy import QtCore

from pzp_hardware.thorlabs import _apt_base

class Piece(_apt_base.APTBase):
    def define_params(self):
        super().define_params()

        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                return 1
            self._ensure_apt()
            _lib = self.puzzle.globals['apt'].core._lib
            _lib.SC_Enable.argtypes = [pht.c.c_long]
            _lib.SC_Disable.argtypes = [pht.c.c_long]
            _lib.SC_GetOPState.argtypes = [pht.c.c_long, pht.c.POINTER(pht.c.c_long)]
            # Left here for compatibility with apt_stage stuff
            self.motor = True
            self._check_error(_lib.InitHWDevice(int(self.params['serial'].get_value())))
            return 1
        
        @pzp.param.checkbox(self, "open", False)
        @self._ensure
        def open_(value):
            if self.puzzle.debug:
                return value
            _lib = self.puzzle.globals['apt'].core._lib
            if value:
                self._check_error(_lib.SC_Enable(int(self.params['serial'].get_value())))
            else:
                self._check_error(_lib.SC_Disable(int(self.params['serial'].get_value())))
            return value

        @open_.set_getter(self)
        @self._ensure
        def open_():
            if self.puzzle.debug:
                return open_.value or False
            _lib = self.puzzle.globals['apt'].core._lib
            state = pht.c.c_long()
            self._check_error(_lib.SC_GetOPState(
                int(self.params['serial'].get_value()),
                pht.c.byref(state)
            ))
            return state.value == 1

        

if __name__ == "__main__":
    app = pzp.QApp()
    puzzle = pzp.Puzzle(name="APT solenoid", debug=pht.debug_prompt())
    puzzle.add_piece("shutter", Piece, 0, 0)
    puzzle.show()
    app.exec()