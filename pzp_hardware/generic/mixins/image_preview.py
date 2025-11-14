# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

"""
:module_title:`Image preview mixin`

These Mixins allow you to add an image preview to your custom Piece easily.
They require an array param named ``image`` to exist on the Piece, and will
update the preview automatically when its value changes.

Add the mixin *before* ``pzp.Piece`` in your class definition, specifying any
settings as class variables::

    import puzzlepiece as pzp
    from pzp_hardware.generic.mixins import image_preview

    import numpy as np

    class Piece(image_preview.ImagePreview, pzp.Piece):
        # including any of these settings is optional, these are the defaults:
        live_toggle = False # include a toggle to enable live mode
        autolevel_toggle = False # include a toggle to enable autoleveling
        max_counts = 255 # the maximum image brightness (will be white with autolevel off)
        use_numba = False # if you need increased performance, you can tell pyqtgraph to use numba
        # horizontal_layout = True # you can use Piece settings to display the preview to the right
        #                           # of the params

        def define_params(self):
            super().define_params()

            @pzp.param.array(self, "image")
            def image():
                return np.random.random((1080, 1440)) * 255
"""

import puzzlepiece as pzp

import numpy as np
from qtpy import QtWidgets, QtCore
import pyqtgraph as pg

#MARK: Base
class Base():
    """
    Base for image previews, implements the live toggle and the autolevel toggle,
    as well as the settings outlined below.

    .. image:: ../images/pzp_hardware.generic.mixins.image_preview.Base.png

    Will not display an image preview on its own, use
    :class:`~pzp_hardware.generic.mixins.image_preview.ImagePreview` or
    :class:`~pzp_hardware.generic.mixins.image_preview.LineoutImagePreview`,
    which are based on this class.
    """
    #: Display a toggle that lets the user refresh the image live
    live_toggle = False
    #: Display a toggle that makes the image brightness range adjust automatically
    autolevel_toggle = False
    #: Adjust the default range of the image view, this is the white point
    max_counts = 255
    #: Enable numba acceleration for some performance gains (but longer initial load times)
    use_numba = False

    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        if self.live_toggle or self.autolevel_toggle:
            toggle_layout = QtWidgets.QGridLayout()
            layout.addLayout(toggle_layout)
            toggle_layout.setColumnStretch(1, 1)

            if self.live_toggle:
                # Add a PuzzleTimer for live view
                delay = 0.05 if not self.puzzle.debug else 0.1 # Introduce artificial delay for debug mode
                self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle, self.params['image'].get_value, delay)
                toggle_layout.addWidget(self.timer, 0, 0)

            if self.autolevel_toggle:
                def autolevel(value):
                    image = self["image"].value
                    if value and image is not None:
                        self.imgw.setImage(autolevels=True)
                    else:
                        self.imgw.setLevels([0, self.max_counts])
                self.autolevel_toggle = pzp.param.ParamCheckbox("autolevel", 0, autolevel)
                toggle_layout.addWidget(self.autolevel_toggle, 0, 2)

        # numba makes image updates slightly faster
        if self.use_numba:
            pg.setConfigOption('useNumba', True)

        return layout

    def call_stop(self):
        super().call_stop()
        if hasattr(self, "timer"):
            self.timer.stop()


#MARK: ImagePreview
class ImagePreview(Base):
    """
    Mixin for displaying an image preview in your Piece. See
    :mod:`pzp_hardware.generic.mixins.image_preview` above for usage.

    .. image:: ../images/pzp_hardware.generic.mixins.image_preview.ImagePreview.png
    """
    def custom_layout(self):
        layout = super().custom_layout()

        # Make an ImageView
        self.pw = pg.PlotWidget()
        layout.addWidget(self.pw)

        plot_item = self.pw.getPlotItem()
        plot_item.setAspectLocked(True)
        plot_item.invertY(True)

        self.imgw = pg.ImageItem(border='w', axisOrder='row-major', levels=[0, self.max_counts])
        plot_item.addItem(self.imgw)

        def update_image():
            self.imgw.setImage(
                self.params['image'].value,
                autoLevels=self.autolevel_toggle and self.autolevel_toggle.value
            )
        if self.autolevel_toggle:
            self.autolevel_toggle.set_value(0)
        update_later = pzp.threads.CallLater(update_image)
        self.params['image'].changed.connect(update_later)

        return layout


#MARK: LineoutImagePreview
class LineoutImagePreview(Base):
    """
    Mixin for displaying an image preview in your Piece, with two movable lines
    that let you plot the image's profile along them. An action is added to centre
    the lines (keyboard shortcut: ``c``), and a hidden param is included for the
    line crossing circle radius.

    See :mod:`pzp_hardware.generic.mixins.image_preview` above for mixin usage.

    .. image:: ../images/pzp_hardware.generic.mixins.image_preview.LineoutImagePreview.png
    """
    def define_actions(self):
        super().define_actions()

        @pzp.action.define(self, 'Centre lines', QtCore.Qt.Key.Key_C)
        def centre(self):
            shape = self.params['image'].value.shape
            self._inf_line_x.setValue(shape[0]//2)
            self._inf_line_y.setValue(shape[1]//2)

    def define_params(self):
        super().define_params()
        pzp.param.spinbox(self, 'circle_r', 200, visible=False)(None)

    def custom_layout(self):
        layout = super().custom_layout()

        # Make the plots
        self.gl = pg.GraphicsLayoutWidget()
        layout.addWidget(self.gl)
        self.gl.ci.layout.setRowStretchFactor(0, 5)
        self.gl.ci.layout.setColumnStretchFactor(0, 5)

        plot_main = self.gl.addPlot(0, 0)
        plot_x = self.gl.addPlot(1, 0)
        plot_x.setXLink(plot_main)
        plot_y = self.gl.addPlot(0, 1)
        plot_y.setYLink(plot_main)

        plot_main.setAspectLocked(True)
        plot_main.invertY(True)
        plot_y.invertY(True)

        self.imgw = pg.ImageItem(border='w', axisOrder='row-major', levels=[0, self.max_counts])
        plot_main.addItem(self.imgw)

        self._inf_line_x = pg.InfiniteLine(0, 0, movable=True)
        self._inf_line_y = pg.InfiniteLine(0, 90, movable=True)
        plot_main.addItem(self._inf_line_x)
        plot_main.addItem(self._inf_line_y)

        r = self.params['circle_r'].value
        self._circle = QtWidgets.QGraphicsEllipseItem(-r, -r, r*2, r*2)  # x, y, width, height
        self._circle.setPen(pg.mkPen((255, 255, 0, 150)))
        plot_main.addItem(self._circle)
        def update_circle():
            r = self.params['circle_r'].value
            self._circle.setRect(self._inf_line_y.value()-r,
                                 self._inf_line_x.value()-r,
                                 r*2, r*2)
        self.params['circle_r'].changed.connect(update_circle)


        plot_line_x = plot_x.plot([0], [0])
        plot_line_y = plot_y.plot([0], [0])

        def update_image():
            image_data = self.params['image'].value
            self.imgw.setImage(
                image_data,
                autoLevels=self.autolevel_toggle and self.autolevel_toggle.value
            )
            self._inf_line_x.setBounds((0, image_data.shape[0]-1))
            self._inf_line_y.setBounds((0, image_data.shape[1]-1))
            plot_line_x.setData(image_data[int(self._inf_line_x.value())])
            i = int(self._inf_line_y.value())
            plot_line_y.setData(image_data[:, i], range(len(image_data[:, i])))
            update_circle()
        update_later = pzp.threads.CallLater(update_image)
        self.params['image'].changed.connect(update_later)
        self._inf_line_x.sigPositionChanged.connect(update_image)
        self._inf_line_y.sigPositionChanged.connect(update_image)
        if self.autolevel_toggle:
            self.autolevel_toggle.set_value(0)

        return layout