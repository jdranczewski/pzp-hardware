import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
from qtpy import QtCore

import _apt_base


class Base(_apt_base.APTBase):
    def define_params(self):
        super().define_params()

        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                return 1
            self._ensure_apt()
            _lib = self.puzzle.globals['apt'].core._lib
            c = pht.c
            _lib.PZMOT_GetPositionSteps.argtypes = [c.c_long, c.POINTER(c.c_long)]
            _lib.PZMOT_MoveAbsoluteStepsEx.argtypes = [c.c_long, c.c_long, c.c_bool]
            _lib.PZMOT_SetChannel.argtypes = [c.c_long, c.c_long]
            # Left here for compatibility with apt_stage stuff
            self.motor = True
            err_code = self.puzzle.globals['apt'].core._lib.InitHWDevice(int(self.params['serial'].get_value()))
            if (err_code != 0):
                message = self.puzzle.globals['apt'].core._get_error_text(err_code)
                raise Exception(
                    f"Failed to connect to piezo: {message}"
                )
            return 1

    def make_channel(self, name, i):
        def set_channel():
            err_code = self.puzzle.globals['apt'].core._lib.PZMOT_SetChannel(
                int(self.params['serial'].get_value()),
                i,
            )
            if (err_code != 0):
                message = self.puzzle.globals['apt'].core._get_error_text(err_code)
                raise Exception(
                    f"Failed to select channel: {message}"
                )
            
        @pzp.param.spinbox(self, name, 0)
        @self._ensure
        def set_value(value):
            if self.puzzle.debug:
                return value
            if self[name].value == value:
                # APT crashes if you try to set a value that is already set...
                return
            set_channel()
            err_code = self.puzzle.globals['apt'].core._lib.PZMOT_MoveAbsoluteStepsEx(
                int(self.params['serial'].get_value()),
                value,
                True
            )
            if (err_code != 0):
                message = self.puzzle.globals['apt'].core._get_error_text(err_code)
                raise Exception(
                    f"Failed to move the piezo: {message}"
                )
            
        @set_value.set_getter(self)
        @self._ensure
        def get_value():
            if self.puzzle.debug:
                return self[name].value
            set_channel()
            pos = self.puzzle.globals['apt'].core.ctypes.c_long()
            err_code = self.puzzle.globals['apt'].core._lib.PZMOT_GetPositionSteps(
                int(self.params['serial'].get_value()),
                self.puzzle.globals['apt'].core.ctypes.byref(pos),
            )
            if (err_code != 0):
                message = self.puzzle.globals['apt'].core._get_error_text(err_code)
                raise Exception(
                    f"Failed to get the piezo value: {message}"
                )
            return pos.value


class Piece(Base):
    def define_params(self):
        super().define_params()

        for i, name in zip((1, 0), "xy"):
            self.make_channel(name, i)

class DoublePiece(Base):
    def define_params(self):
        super().define_params()

        for i, name in zip((0, 1, 2, 3), ("x1", "y1", "x2", "y2")):
            self.make_channel(name, i)


if __name__ == "__main__":
    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=pht.debug_prompt())
    puzzle.add_piece("piezo", DoublePiece, 0, 0)
    puzzle.show()
    app.exec()