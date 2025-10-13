# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
:module_title:`ThorLabs APT piezo inertia actuator`

Pieces for interacting with
`ThorLabs piezo inertia actuator controllers <https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=9790>`__
through the `APT interface <https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=9019>`__
using the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework.

Example usage (see :ref:`getting-started` for more details on using Pieces in general)::

    import puzzlepiece as pzp
    from pzp_hardware.thorlabs import apt_piezo

    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("stage", apt_piezo.Piece, row=0, column=0)
    puzzle.show()
    app.exec()

.. automodule:: pzp_hardware.thorlabs._apt_base
   :no-index:

Available Pieces
----------------
"""

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
from qtpy import QtCore

from pzp_hardware.thorlabs import _apt_base


#MARK: Base Piece
class Base(_apt_base.APTBase):
    """
    .. image:: ../images/pzp_hardware.thorlabs.apt_piezo.Base.png

    Base Piece that doesn't define any channels, and should be inherited to provide a Piece
    matching your piezo configuration. Two examples are included:
    :class:`~pzp_hardware.thorlabs.apt_piezo.Piece`  and
    :class:`~pzp_hardware.thorlabs.apt_piezo.DoublePiece`.
    """
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
        """
        Create a named param for a channel number with a setter and getter. Should be
        called within ``define_params`` to create params for your piezo controllers
        x, y, z, etc axes::

            def define_params(self):
                super().define_params()

                for i, name in zip((0, 1), "xy"):
                    self.make_channel(name, i)

        :param name: name of the channel/param to create
        :param i: index of the channel on the piezo controller
        :rtype: puzzlepiece.param.ParamInt
        """
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
                return self[name].value or 0
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

        return set_value


#MARK: Main Pieces
class Piece(Base):
    """
    A Piece that defines two piezo channels, ``x`` and ``y``, for example to control a mirror.

    .. image:: ../images/pzp_hardware.thorlabs.apt_piezo.Piece.png
    """
    def define_params(self):
        super().define_params()

        for i, name in zip((0, 1), "xy"):
            self.make_channel(name, i)

class DoublePiece(Base):
    """
    A Piece that defines four piezo channels, an ``x`` and ``y`` times two, for example
    to control two mirrors.

    .. image:: ../images/pzp_hardware.thorlabs.apt_piezo.DoublePiece.png
    """
    def define_params(self):
        super().define_params()

        for i, name in zip((0, 1, 2, 3), ("x1", "y1", "x2", "y2")):
            self.make_channel(name, i)


if __name__ == "__main__":
    app = pzp.QApp()
    puzzle = pzp.Puzzle(name="APT piezo", debug=pht.debug_prompt())
    puzzle.add_piece("piezo", DoublePiece, 0, 0)
    puzzle.show()
    app.exec()