# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
:module_title:`Vialux DMD`

Pieces for interacting with `Vialux Digital Micromirror Devices (DMDs) <http://www.vialux.de/en/>`__
using `ALP4lib <https://github.com/wavefrontshaping/ALP4lib>`__ and
the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework.

Example usage (see :ref:`getting-started` for more details on using Pieces in general)::

    import puzzlepiece as pzp
    from pzp_hardware.vialux import dmd

    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("hardware", dmd.Piece, row=0, column=0)
    puzzle.show()
    app.exec()

Installation
------------
* Install the Vialux software from http://www.vialux.de/en/ or a USB key that came with
  your hardware.
* Locate the ALP DLLs in the Vialux software's installation directory -- this will depend on
  your ALP version, look for a folder similar to ``C:\Program Files\ALP-4.4\ALP-4.4 API\x64``.
* Install ALP4lib in your Python environment with ``pip install ALP4lib``, or wait to
  be prompted to install it at runtime. See https://github.com/wavefrontshaping/ALP4lib for more.
* Provide the path to ALP DLLs when prompted at runtime.

Requirements
------------
.. pzp_requirements:: pzp_hardware.vialux.dmd

Available Pieces
----------------
"""

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
import numpy as np

from pzp_hardware.generic.mixins import image_preview

#MARK: Piece
class Piece(image_preview.ImagePreview, pzp.Piece):
    """
    Basic Piece for controlling a Vialux DMD. Allows setting any image array to the DMD,
    and quickly making it fully black or white. Have a look at
    :class:`pzp_hardware.generic.patterning.patterns` for a quick way to display test patterns.

    Note that by default this image will run at 30fps, with very short periods of the DMD
    resetting between the frames.

    .. image:: ../images/pzp_hardware.vialux.dmd.Piece.png
    """
    custom_horizontal = True
    action_wrap = 1

    def __init__(self, puzzle, *args, **kwargs):
        self.image = None
        self.size_x, self.size_y = 1280, 800
        super().__init__(puzzle, *args, **kwargs)

    def define_params(self):
        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                self.actions['Black']()
                return 1
            self._dmd = self._ALP4.ALP4(version = '4.3')
            self._dmd.Initialize()
            self._seq = self._dmd.SeqAlloc(nbImg = 1, bitDepth = 1)
            self.size_x, self.size_y = self._dmd.nSizeX, self._dmd.nSizeY
            self.actions['Black']()

        @pzp.param.disconnect(self)
        def disconnect():
            if self.puzzle.debug:
                return 0
            if self._ensure(capture_exception=True):
                self._dmd.Halt()
                self._dmd.FreeSeq(SequenceId=self._seq)
                self._dmd.Free()
                return 0

        image = pzp.param.array(self, 'image')(None)

        @image.set_setter(self)
        @self._ensure
        def image(value):
            if not self.puzzle.debug:
                self._dmd.Halt()
                self._dmd.SeqPut(imgData = np.asarray(value).ravel(), SequenceId=self._seq)
                self._dmd.Run()

    def define_actions(self):
        @pzp.action.define(self, 'White')
        def white():
            self.params['image'].set_value(np.ones((self.size_y, self.size_x)).astype(int) * 255)

        @pzp.action.define(self, 'Black')
        def black():
            self.params['image'].set_value(np.zeros((self.size_y, self.size_x)).astype(int))

        @pzp.action.define(self, 'Display', visible=False)
        def display():
            self.params['image'].set_value()

    @pzp.piece.ensurer
    def _ensure(self):
        if self.puzzle.debug:
            return
        if hasattr(self, '_dmd') and hasattr(self._dmd, '_ALPLib'):
            return
        raise Exception('DMD not connected')

    def setup(self):
        pht.requirements({"ALP4": {
            "pip": "ALP4lib",
            "url": "https://pzp-hardware.readthedocs.io/en/latest/auto/pzp_hardware.vialux.dmd.html#installation"
        }})
        pht.add_dll_directory(
            pht.config(
                "ALP4_dll_directory",
                default=r"C:\Program Files\ALP-4.4\ALP-4.4 API\x64",
                description="the exact path may depend on your DMD's ALP version, say 4.4 vs 4.1",
                validator=pht.validator_path_exists
            )
        )
        import ALP4
        self._ALP4 = ALP4


#MARK: AdvancedPiece
class AdvancedPiece(Piece):
    """
    An advanced Piece for controlling a Vialux DMD. Just as :class:`pzp_hardware.vialux.dmd.Piece`, it
    allows setting any image array to the DMD, and quickly making it fully black or white.
    In addition, the frame timing and slave mode can be controlled, enabling externally triggered operation.

    The image sequence feature allows loading a set of images onto the DMD, which it will run through
    in sequence (with internal or external triggering). For example::

        # Stop the DMD before dealing with image sequences
        puzzle["dmd"].actions["Halt"]()
        # Prepare the DMD to receive a sequence of 10 images
        puzzle["dmd:n_images"].set_value(10)
        # Set the illumination time to 10ms (param units are us, matching the API)
        puzzle["dmd:illumination_time"].set_value(10*1000)
        # Set the image sequence
        puzzle["dmd:image_sequence"].set_value(np.zeros((10, puzzle["dmd"].size_y, puzzle["dmd"].size_x), np.uint8))
        # Run the sequence in a loop (by default the sequence only runs once)
        puzzle["dmd"].actions["Run Sequence"](loop=True)

    .. image:: ../images/pzp_hardware.vialux.dmd.AdvancedPiece.png
    """
    action_wrap = 2

    def define_params(self):
        super().define_params()

        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                self.actions['Black']()
                return 1

            self._dmd = self._ALP4.ALP4(version = '4.3', libDir=r"C:\Program Files\ALP-4.3\ALP-4.3 API")
            self._dmd.Initialize()
            self.size_x, self.size_y = self._dmd.nSizeX, self._dmd.nSizeY
            self._seq = self._dmd.SeqAlloc(nbImg = 1, bitDepth = 1)
            self.actions['Black']()
            return 1

        @pzp.param.disconnect(self)
        @self._ensure
        def disconnect():
            if self.puzzle.debug:
                return 0
            self._dmd.Halt()
            if self._long_seq is not None:
                self._dmd.FreeSeq(SequenceId=self._long_seq)
                self._long_seq = None
            self._dmd.FreeSeq(SequenceId=self._seq)
            self._dmd.Free()
            return 0

        @pzp.param.group("Settings")
        @pzp.param.spinbox(self, "illumination_time", 10000, v_min=0, v_step=1000)
        @self._ensure
        @self._ensure_seq
        def illumination_time(self, value):
            if not self.puzzle.debug:
                self._dmd.SetTiming(self._seq, illuminationTime=value)
                self._dmd.SetTiming(self._long_seq, illuminationTime=value)

        @pzp.param.group("Settings")
        @pzp.param.checkbox(self, "slave", 0)
        @self._ensure
        def slave(self, value):
            if self.puzzle.debug:
                return
            if value:
                self._dmd.ProjControl(self._ALP4.ALP_PROJ_MODE, self._ALP4.ALP_SLAVE)
                self._dmd.DevControl(self._ALP4.ALP_TRIGGER_EDGE, self._ALP4.ALP_EDGE_RISING)
            else:
                self._dmd.ProjControl(self._ALP4.ALP_PROJ_MODE, self._ALP4.ALP_MASTER)

        self._long_seq = None
        @pzp.param.group("Sequence")
        @pzp.param.spinbox(self, "n_images", 1, v_min=1)
        @self._ensure
        def n_images(self, value):
            self["preview_i"].input.setMaximum(value-1)
            if not self.puzzle.debug:
                # Free the previous sequence if present
                if self._long_seq is not None:
                    self._dmd.FreeSeq(SequenceId=self._long_seq)
                self._long_seq = self._dmd.SeqAlloc(nbImg = value, bitDepth = 1)
                self["illumination_time"].set_value()

        image = pzp.param.array(self, 'image_sequence')(None)
        image.set_group("Sequence")
        @image.set_setter(self)
        @self._ensure
        @self._ensure_seq
        def image_sequence(self, value):
            image = np.asarray(value)
            if not self.puzzle.debug:
                self._dmd.SeqPut(imgData = image.ravel(), SequenceId=self._long_seq)

        pzp.param.spinbox(self, "preview_i", 0, v_min=0, v_max=0, v_step=1)(None).set_group("Sequence")

    def define_actions(self):
        super().define_actions()

        @pzp.action.define(self, "Halt")
        @self._ensure
        def halt(self):
            if not self.puzzle.debug:
                self._dmd.Halt()

        @pzp.action.define(self, "Run Sequence")
        @self._ensure
        @self._ensure_seq
        def run(self, loop=False):
            if not self.puzzle.debug:
                self._dmd.Run(self._long_seq, loop=loop)

    @pzp.piece.ensurer
    def _ensure_seq(self):
        if self.puzzle.debug:
            return
        if self._long_seq is None:
            raise Exception('Please set the n_images param.')

    def custom_layout(self):
        layout = super().custom_layout()
        self["preview_i"].changed.connect(lambda: self.imgw.setImage(
            self['image_sequence'].value[self["preview_i"].value],
            autoLevels=False
        ))
        return layout


if __name__ == "__main__":
    app = pzp.QApp()
    puzzle = pzp.Puzzle(name="DMD", debug=pht.debug_prompt())
    puzzle.add_piece("dmd", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()