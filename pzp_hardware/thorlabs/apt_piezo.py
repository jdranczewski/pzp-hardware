import puzzlepiece as pzp
from qtpy import QtCore

import apt_stage


class Base(apt_stage.Piece):
    def define_params(self):
        super().define_params()
        del self.params["pos"]

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

    def define_actions(self):
        @pzp.action.define(self, 'Init')
        def init(self):
            if not self.puzzle.debug and not self._ensure(capture_exception=True):
                self._ensure_apt()
                c = self.puzzle.globals['apt'].core.ctypes
                _lib = self.puzzle.globals['apt'].core._lib
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
            self.params['connected'].set_value(1)

        @pzp.action.define(self, 'Cleanup')
        def cleanup(self):
            if not self.puzzle.debug:
                self._apt_cleanup()
                if hasattr(self, 'motor'):
                    del self.motor
            self.params['connected'].set_value(0)

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


class Nudge(pzp.Piece):
    def define_params(self):
        pzp.param.text(self, "move", "piezo:{}")(None)
        pzp.param.spinbox(self, "distance", 0.1)(None)

    def define_actions(self):
        def make_direction(name, axis, pm, key):
            @pzp.action.define(self, name, shortcut=key)
            def move(self):
                param = pzp.parse.parse_params(
                    self['move'].value.format(axis),
                    self.puzzle
                )[0]
                now = param.get_value()
                param.set_value(now + pm * self["distance"].value)

        for name, axis, pm, key in zip(
            ("Left", "Right", "Up", "Down"),
            "xxyy",
            (-1, 1, 1, -1),
            (QtCore.Qt.Key.Key_A, QtCore.Qt.Key.Key_D, QtCore.Qt.Key.Key_W, QtCore.Qt.Key.Key_S)
        ):
            make_direction(name, axis, pm, key)


if __name__ == "__main__":
    app = pzp.QApp([])
    puzzle = pzp.Puzzle(debug=True)
    puzzle.add_piece("piezo", DoublePiece, 0, 0)
    puzzle.add_piece("nudge", Nudge, 1, 0)
    puzzle.show()
    app.exec()