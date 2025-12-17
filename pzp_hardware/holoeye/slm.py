# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
:module_title:`Holoeye SLM`

Pieces for interacting with `Holoeye SLMs <https://holoeye.com/products/spatial-light-modulators/>`__
using the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework.

Example usage (see :ref:`getting-started` for more details on using Pieces in general)::

    import puzzlepiece as pzp
    from pzp_hardware.holoeye import slm

    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("slm", slm.Piece, row=0, column=0)
    puzzle.show()
    app.exec()

Installation
------------
* Install the SLM SDK. You may have to register your SLM at https://customers.holoeye.com/
  to get a download link.
* When you first initialise the Piece, you will be prompted for two directories: the Python
  examples directory (``C:\Program Files\HOLOEYE Photonics\SLM Display SDK (Python) v4.1.0\examples``)
  and the Python API directory
  (``C:\Program Files\HOLOEYE Photonics\SLM Display SDK (Python) v4.1.0\api\python``).
  Accepting the defaults should be ok in most cases, and you will be prompted if the directories are
  not found. If your SDK is installed in a non-standard location, provide the correct directories
  when prompted.

Requirements
------------
.. pzp_requirements:: pzp_hardware.holoeye.slm

Available Pieces
----------------
"""

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht

from pzp_hardware.generic.mixins import image_preview

import numpy as np
import os

class Piece(image_preview.ImagePreview, pzp.Piece):
    custom_horizontal = True
    action_wrap = 1

    def define_params(self):
        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                self["image"].set_value(np.zeros((1200, 1920)))
                return 1
            self._check_call(self.HEDS.SDK.Init(4,1))
            self.slm = self.HEDS.SLM.Init("", True, 0.0)
            self._check_err_code(self.slm.errorCode())
            self["image"].set_value(np.zeros((1200, 1920)))
            return 1

        @pzp.param.disconnect(self)
        def disconnect():
            if self.puzzle.debug:
                return 0
            self.HEDS.SDK.Close()
            del self.slm
            return 0

        image = pzp.param.array(self, 'image')(None)

        @image.set_setter(self)
        @self._ensure
        def image(value):
            if self.puzzle.debug:
                return
            converted = value.astype(np.uint8, copy=False)
            dataHandle = self._check_call(self.slm.loadPhaseData(converted))
            scale = self["scale"].value
            if scale != 1.:
                self._check_call(dataHandle.setTransformScale(scale))
            self._check_call(dataHandle.show())
            return converted
        
        pzp.param.spinbox(self, "scale", 1., 0)(None)

        @pzp.param.spinbox(self, "wavelength", 0.)
        @self._ensure
        def wavelength(value):
            if self.puzzle.debug:
                return value
            self._check_call(self.slm.setWavelength(value))

        @wavelength.set_getter(self)
        @self._ensure
        def wavelength():
            if self.puzzle.debug:
                return wavelength.value or 0
            # the stock "getWavelength" method doesn't work
            return self._check_call(self.HEDS.SDK.libapi.heds_slm_get_wavelength(self.slm._id, self.htypes.HEDSCC_Mono))

        @pzp.param.text(self, "correction_file", "")
        @self._ensure
        def correction_file(value):
            window = self.slm.window()
            if os.path.exists(value):
                self._check_call(window.loadWavefrontCompensationFile(value))
                return value
            else:
                self._check_call(window.clearWavefrontCompensation())
                return ""


    def setup(self):
        pht.add_path_directory(
            pht.config(
                "holoeye_examples_directory",
                default=r"C:\Program Files\HOLOEYE Photonics\SLM Display SDK (Python) v4.1.0\examples",
                validator=pht.validator_path_exists
            )
        )
        pht.add_path_directory(
            pht.config(
                "holoeye_python_directory",
                default=r"C:\Program Files\HOLOEYE Photonics\SLM Display SDK (Python) v4.1.0\api\python",
                validator=pht.validator_path_exists
            )
        )
        import HEDS
        import hedslib.heds_types
        self.HEDS = HEDS
        self.htypes = hedslib.heds_types

    def _check_call(self, returned):
        try:
            code, *others = returned
            self._check_err_code(code)
            if len(others) > 1:
                return others
            else:
                return others[0]
        except TypeError:
            # only one value returned
            self._check_err_code(returned)

    def _check_err_code(self, code):
        if code != self.htypes.HEDSERR_NoError:
            raise Exception(f"SLM error: {self.HEDS.SDK.ErrorString(code)}")

    @pzp.piece.ensurer
    def _ensure(self):
        if not self.puzzle.debug and not hasattr(self, "slm"):
            raise Exception("SLM not connected")

if __name__ == "__main__":
    app = pzp.QApp()
    puzzle = pzp.Puzzle(name="Holoeye SLM", debug=pht.debug_prompt())
    puzzle.add_piece("slm", Piece, 0, 0)
    puzzle.show()
    app.exec()