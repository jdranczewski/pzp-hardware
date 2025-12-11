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
            dataHandle = self._check_call(self.slm.loadPhaseData(value))
            self._check_call(dataHandle.show())

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
    puzzle = pzp.Puzzle(name="DMD", debug=pht.debug_prompt())
    puzzle.add_piece("dmd", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()