# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
.. module_title:: Hardware name - speficfy this for the documentation build to include your file

Pieces for interacting with `name of your hardware here <https://example.com>`__ (TODO: update name here)
using the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework.

Example usage (see :ref:`getting-started` for more details on using Pieces in general)::

    import puzzlepiece as pzp
    from pzp_hardware.manufacturer import hardware # TODO: update name here

    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("hardware", hardware.Piece, row=0, column=0) # TODO: update name here
    puzzle.show()
    app.exec()

Installation
------------
* TODO: If the Piece uses any manufacturer APIs, list installation instructions here

Requirements
------------
.. pzp_requirements:: pzp_hardware.thorlabs.camera

TODO: update package name above to generate requirements automatically

Available Pieces
----------------
"""

# MARK: Imports
# You can use mark comments to indicate parts of your file in the Visual Studio Code minimap.
import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht

# TODO: if your Piece has requirements beyond that of puzzlepiece, add specifications
# for them using ``pht.requirements``. This will prompt the user to install at runtime
# and include details in the documentation.
pht.requirements(
    {
        "PIL": {
            "pip": "pillow",
            "url": "https://pillow.readthedocs.io/en/stable/installation/basic-installation.html",
        }
    }
)
from PIL import Image


# region Piece
# You can use #region and #endregion comments to indicate parts of your file in the
# Visual Studio Code minimap (and make them collapsible).
class Piece(pzp.Piece):
    """
    TODO: Write (simple or not) docstrings for the Pieces you want to expose as available
    in the documentation.
    """

    def define_params(self):
        # Use ``pzp.param.connect`` and ``pzp.param.disconnect`` to implement connecting and disconnecting
        # from your hardware (other methods are acceptable too, this is just the standard one).
        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                # Remember to implement debug mode options for your Pieces.
                return 1
            print("Connected")
            return 1

        @pzp.param.disconnect(self)
        def disconnect():
            if self.puzzle.debug:
                return 0
            print("Disconnected")
            return 0

        @pzp.param.readout(self, "hello")
        @self._ensure
        def hello():
            return "world"

    @pzp.piece.ensurer
    def _ensure(self):
        # You can use ensurers to check conditions before running setters, getters, or actions
        if not self["connected"].value:
            raise Exception("Piece not connected")

    def setup(self):
        # You can use ``setup`` to import your APIs, this will only be called when not in debug mode.
        # Remember to define additional requirements in here too.
        pht.requirements(
            {
                "pandas": {
                    "pip": "pandas",
                    "url": "https://pandas.pydata.org/docs/getting_started/install.html",
                }
            }
        )
        import pandas

        self.pandas = pandas


# endregion

if __name__ == "__main__":
    # If running this file directly, make a Puzzle, add our Piece, and display it
    app = pzp.QApp()
    puzzle = pzp.Puzzle(app, "Template", debug=True)  # TODO: update names
    puzzle.add_piece("template", Piece, row=0, column=0)
    puzzle.show()
    app.exec()
