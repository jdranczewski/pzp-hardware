# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
:module_title:`ThorLabs APT stage`

Pieces for interacting with
`ThorLabs moving stages <https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=2420>`__
through the `APT interface <https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=9019>`__
using the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework.

Example usage (see :ref:`getting-started` for more details on using Pieces in general)::

    import puzzlepiece as pzp
    from pzp_hardware.thorlabs import apt_stage

    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("stage", apt_stage.Piece, row=0, column=0)
    puzzle.show()
    app.exec()

.. automodule:: pzp_hardware.thorlabs._apt_base

Available Pieces
----------------
"""

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht

from pzp_hardware.thorlabs import _apt_base

#MARK: Piece
class Piece(_apt_base.APTBase):
    """
    Main Piece for controlling APT stages.

    .. image:: ../images/pzp_hardware.thorlabs.apt_stage.Piece.png
    """
    def define_params(self):
        super().define_params()

        @pzp.param.spinbox(self, 'pos', 0.)
        @self._ensure
        def move_to(value):
            if self.puzzle.debug:
                return value
            self.motor.move_to(value, blocking=True)

        @move_to.set_getter(self)
        @self._ensure
        def get_position():
            if self.puzzle.debug:
                return self["pos"].value or 0.
            return self.motor.position

    def define_actions(self):
        @pzp.action.define(self, 'Home')
        @self._ensure
        def home():
            if self.puzzle.debug:
                self.param['pos'].set_value(0)
            self.motor.move_home(blocking=True)
            self.params['pos'].get_value()

        @pzp.action.define(self, 'Identify')
        @self._ensure
        def identify():
            if self.puzzle.debug:
                return
            self.motor.identify()


if __name__ == "__main__":
    app = pzp.QApp()
    puzzle = pzp.Puzzle(name="APT stage", debug=pht.debug_prompt())
    puzzle.add_piece("stage", Piece, 0, 0)
    puzzle.show()
    app.exec()