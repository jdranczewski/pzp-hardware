import puzzlepiece as pzp
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np

class Piece(pzp.Piece):
    def __init__(self, puzzle, custom_horizontal=True, *args, **kwargs):
        self.image = None
        self.size_x, self.size_y = 1280, 800
        super().__init__(puzzle, custom_horizontal, *args, **kwargs)

    def action_layout(self, wrap=1):
        return super().action_layout(wrap)

    def define_params(self):
        @pzp.param.checkbox(self, 'connected', 0)
        def connected(self, value):
            if self.puzzle.debug:
                self.actions['Black']()
                return 1
            
            if value and not self.params['connected'].value:
                # Connect if not connected
                self._dmd = self._ALP4.ALP4(version = '4.3')
                self._dmd.Initialize()
                self._seq = self._dmd.SeqAlloc(nbImg = 1, bitDepth = 1)
                self.size_x, self.size_y = self._dmd.nSizeX, self._dmd.nSizeY
                self.actions['Black']()

            elif not value and self.params['connected'].value:
                # Disconnect if we're connected
                if self._ensure(capture_exception=True):
                    self._dmd.Halt()
                    self._dmd.FreeSeq(SequenceId=self._seq)
                    self._dmd.Free()
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

    def custom_layout(self):
        layout = QtWidgets.QHBoxLayout()

        gw = pg.GraphicsView()
        view = pg.ViewBox()
        view.setAspectLocked(True)
        view.invertY(True)
        gw.setCentralItem(view)

        pg.setConfigOption('useNumba', True)
        self.imgw = pg.ImageItem(border='w', axisOrder='row-major', levels=[0, 255])
        view.addItem(self.imgw)
        view.setRange(QtCore.QRectF(0, 0, 1280, 800))
        update_later = pzp.threads.CallLater(lambda: self.imgw.setImage(self.params['image'].value, autoLevels=False))
        self.params['image'].changed.connect(update_later)

        layout.addWidget(gw)
        return layout
    
    def handle_close(self, event):
        self.params['connected'].set_value(0)
        super().handle_close(event)


class BlueNoise(pzp.Piece):
    def define_params(self):
        from skimage.io import imread
        blue = imread("source_images/LDR_LLL1_0.png")[:,:,0]
        blue_mask = (np.pad(blue, ((0, 800-512), (0, 1280-512)), mode='wrap') + 1.) / 256 * 255

        image = pzp.param.array(self, "image")(None)
        @image.set_setter(self)
        def image(self, image):
            param = pzp.parse.parse_params(self["destination"].value, self.puzzle)[0]
            shape = image.shape
            param.set_value((image >= blue_mask[:shape[0], :shape[1]]) * 255)
            return image

        pzp.param.text(self, "destination", "dmd:image")(None)

            
if __name__ == "__main__":
    app = pzp.QApp([])
    puzzle = pzp.Puzzle(app, "DMD", debug=True)
    puzzle.add_piece("dmd", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()