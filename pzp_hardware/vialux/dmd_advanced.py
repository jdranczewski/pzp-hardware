import puzzlepiece as pzp
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np

class Piece(pzp.Piece):
    def __init__(self, puzzle, custom_horizontal=True, *args, **kwargs):
        self.image = None
        self.size_x, self.size_y = 1024, 768
        super().__init__(puzzle, custom_horizontal, *args, **kwargs)

    def param_layout(self, wrap=1):
        return super().param_layout(wrap)

    def define_params(self):
        @pzp.param.checkbox(self, 'connected', 0)
        def connected(self, value):
            if self.puzzle.debug:
                self.actions['Black']()
                return 1
            
            if value and not self.params['connected'].value:
                # Connect if not connected
                self._dmd = self._ALP4.ALP4(version = '4.3', libDir=r"C:\Program Files\ALP-4.3\ALP-4.3 API")
                self._dmd.Initialize()
                self.size_x, self.size_y = self._dmd.nSizeX, self._dmd.nSizeY
                self._single_seq = self._dmd.SeqAlloc(nbImg = 1, bitDepth = 1)
                self.actions['Black']()

            elif not value and self.params['connected'].value:
                # Disconnect if we're connected
                if self._ensure(capture_exception=True):
                    self._dmd.Halt()
                    if self._seq is not None:
                        self._dmd.FreeSeq(SequenceId=self._seq)
                        self._seq = None
                    self._dmd.FreeSeq(SequenceId=self._single_seq)
                    self._dmd.Free()

        self._seq = None
        @pzp.param.spinbox(self, "n_images", 1, v_min=1)
        @self._ensure
        def n_images(self, value):
            self["preview_i"].input.setMaximum(value-1)
            if not self.puzzle.debug:
                # Free the previous sequence if present
                if self._seq is not None:
                    self._dmd.FreeSeq(SequenceId=self._seq)
                self._seq = self._dmd.SeqAlloc(nbImg = value, bitDepth = 1)
                self["illumination_time"].set_value()

        @pzp.param.spinbox(self, "illumination_time", 10000, v_min=0, v_step=1000)
        @self._ensure
        @self._ensure_seq
        def illumination_time(self, value):
            if not self.puzzle.debug:
                self._dmd.SetTiming(self._single_seq, illuminationTime=value)
                self._dmd.SetTiming(self._seq, illuminationTime=value)

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

        image = pzp.param.array(self, 'image')(None)
        @image.set_setter(self)
        @self._ensure
        def image(self, value):
            self.image = np.asarray(value)
            if not self.puzzle.debug:
                self._dmd.Halt()
                self._dmd.SeqPut(imgData = self.image.ravel(), SequenceId=self._single_seq)
                self._dmd.Run(self._single_seq, loop=True)

        image = pzp.param.array(self, 'image_sequence')(None)
        @image.set_setter(self)
        @self._ensure
        @self._ensure_seq
        def image_sequence(self, value):
            image = np.asarray(value)
            if not self.puzzle.debug:
                self._dmd.SeqPut(imgData = image.ravel(), SequenceId=self._seq)

        pzp.param.spinbox(self, "preview_i", 0, v_min=0, v_max=0, v_step=1)(None)
        
    def define_actions(self):
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
                self._dmd.Run(self._seq, loop=loop)

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
    
    @pzp.piece.ensurer
    def _ensure_seq(self):
        if self.puzzle.debug:
            return
        if self._seq is None:
            raise Exception('Please set the n_images param.')
        
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
        self["preview_i"].changed.connect(lambda: self.imgw.setImage(
            self['image_sequence'].value[self["preview_i"].value],
            autoLevels=False
        ))

        layout.addWidget(gw)
        return layout
    
    def handle_close(self, event):
        self.params['connected'].set_value(0)
        super().handle_close(event)

            
if __name__ == "__main__":
    import patterns
    app = pzp.QApp([])
    puzzle = pzp.Puzzle(app, "DMD", debug=True)
    puzzle.add_piece("dmd", Piece(puzzle), 0, 0)
    puzzle.add_piece("patterns", patterns.Piece(puzzle), 0, 1)
    puzzle.show()
    app.exec()