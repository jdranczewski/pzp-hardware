import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np

from pzp_hardware.generic.mixins import image_preview

class Piece(image_preview.ImagePreview, pzp.Piece):
    custom_horizontal = True
    action_wrap = 1

    def __init__(self, puzzle, *args, **kwargs):
        self.image = None
        self.size_x, self.size_y = 1280, 800
        super().__init__(puzzle, *args, **kwargs)

    def define_params(self):
        @pzp.param.connect(self)
        def connected():
            if self.puzzle.debug:
                self.actions['Black']()
                return 1 
            self._dmd = self._ALP4.ALP4(version = '4.3')
            self._dmd.Initialize()
            self._seq = self._dmd.SeqAlloc(nbImg = 1, bitDepth = 1)
            self.size_x, self.size_y = self._dmd.nSizeX, self._dmd.nSizeY
            self.actions['Black']()

        @pzp.param.disconnect(self)
        def disconnected():
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
        def image(self, value):
            self.image = np.asarray(value)
            if not self.puzzle.debug:
                self._dmd.Halt()
                self._dmd.SeqPut(imgData = self.image.ravel(), SequenceId=self._seq)
                self._dmd.Run()
        
    def define_actions(self):
        @pzp.action.define(self, 'White')
        def white(self):
            self.params['image'].set_value(np.ones((self.size_y, self.size_x)).astype(int) * 255)
    
        @pzp.action.define(self, 'Black')
        def black(self):
            self.params['image'].set_value(np.zeros((self.size_y, self.size_x)).astype(int))

        @pzp.action.define(self, 'Display', visible=False)
        def display(self):
            self.params['image'].set_value(self.image)
            
    @pzp.piece.ensurer
    def _ensure(self):
        if self.puzzle.debug:
            return
        if hasattr(self, '_dmd') and hasattr(self._dmd, '_ALPLib'):
            return
        raise Exception('DMD not connected')
        
    def setup(self):
        import ALP4
        self._ALP4 = ALP4
    
    def handle_close(self, event):
        self.params['connected'].set_value(0)
        super().handle_close(event)

    
if __name__ == "__main__":
    app = pzp.QApp()
    puzzle = pzp.Puzzle(app, "DMD", debug=pht.debug_prompt())
    puzzle.add_piece("dmd", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()