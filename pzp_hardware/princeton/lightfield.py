# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
:module_title:`Lightfield software Piece`

Pieces for interacting with `Thorlabs scientific cameras <https://www.thorlabs.com/navigation.cfm?guide_id=2025>`__
using the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework.

Example usage (see :ref:`getting-started` for more details on using Pieces in general)::

    import puzzlepiece as pzp
    from pzp_hardware.princeton import lightfield

    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("lightfield", lightfield.Piece, row=0, column=0)
    puzzle.show()
    app.exec()

Installation
------------
* It's complicated

Requirements
------------
.. pzp_requirements:: pzp_hardware.princeton.lightfield

Available Pieces
----------------
"""

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
import numpy as np
import pyqtgraph as pg
import time
from pyqtgraph.Qt import QtWidgets

class Piece(pzp.Piece):
    def __init__(self, puzzle):
        super().__init__(puzzle, custom_horizontal=True)
        self.wls = [0]
        self.values = [0]

    def define_params(self):
        def make_param(name, value, setting, post_set=None, post_get=None):
            @pzp.param.spinbox(self, name, value)
            @self._ensure
            @self._stop
            def setter(self, value):
                if self.puzzle.debug:
                    return value

                # https://github.com/pythonnet/pythonnet/issues/1755
                original_value = value
                if isinstance(value, int):
                    value = self.imports.Int32(value)
                self.experiment.SetValue(setting, value)
                if post_set is not None:
                    post_set(original_value)

            @setter.set_getter(self)
            @self._ensure
            @self._stop
            def setter(self):
                if self.puzzle.debug:
                    return self[name].value

                value = self.experiment.GetValue(setting)
                if post_get is not None:
                    post_get()
                return value

        def set_bgfile(value):
            self.experiment.SetValue(self.imports.ExperimentSettings.OnlineCorrectionsBackgroundCorrectionReferenceFile,
                                    "D:\\jbd17_automation\\libraries\\lightfield_files\\{}.spe".format(int(value)))
            if not self.experiment.IsReadyToRun:
                raise Exception("A background file doesn't exist")

        if self.puzzle.debug:
            make_param("integration", 300, None)
            make_param("center", 875, None)
            make_param("roi", 1, None)
        else:
            make_param("integration", 300, self.imports.CameraSettings.ShutterTimingExposureTime, post_set=set_bgfile)
            make_param("center", 875, self.imports.SpectrometerSettings.GratingCenterWavelength)
            make_param("roi", 1, self.imports.CameraSettings.ReadoutControlRegionsOfInterestSelection)

        pzp.param.text(self, "filename", "jdr")(None)

        @pzp.param.array(self, "values")
        @self._ensure
        def values(self):
            if self.puzzle.debug:
                self.wls = np.arange(100)
                self.values = np.random.random((20, 100))
                return self.values

            # Hardware implementation
            self.experiment.Stop()
            while self.experiment.IsRunning:
                time.sleep(0.1)
            dataset = self.experiment.Capture(1)
            frame = dataset.GetFrame(0, 0)
            data = frame.GetData()
            width = frame.Width

            # print(self.values.shape)
            # self.wls = np.array([x for x in self.experiment.SystemColumnCalibration])
            self.wls = np.array(list(self.experiment.SystemColumnCalibration))
            binning = len(self.wls) // width
            self.wls = self.wls[binning//2::binning]
            self.values = self.imports.convert_buffer(data, frame.Format).reshape((-1, len(self.wls)))

            # Try to dispose of all the things
            dataset.Dispose()
            # frame.Dispose() doesn't work
            # data.Dispose() doesn't work
            return self.values

        @pzp.param.array(self, "wls", visible=False)
        def wls(self):
            return self.wls

        @pzp.readout.define(self, "counts", "{:.2f}")
        def capture(self):
            values = self.params['values'].get_value()
            return np.sum(values)

        @pzp.readout.define(self, "saturated", visible=False)
        def saturated(self):
            return 1 if np.amax(self.values) > 6e4 else 0

        @pzp.readout.define(self, "max_counts", "{:.2f}", visible=True)
        def max_counts(self):
            values = self.params['values'].get_value()
            return np.amax(self.values)

    def define_actions(self):
        @pzp.action.define(self, "Launch")
        def launch(self):
            if self.puzzle.debug:
                return

            # Hardware implementation
            self.automation = self.imports.Automation(True, self.imports.List[self.imports.String]())
            self.experiment = self.automation.LightFieldApplication.Experiment
            # self.experiment.Load(r'D:\jbd17_automation\libraries\lightfield_files\Experiments\jbd17_base_binned.lfe')
            self.wls = np.array([x for x in self.experiment.SystemColumnCalibration])

        @pzp.action.define(self, "Acquire")
        @self._ensure
        def acquire(self):
            if self.puzzle.debug:
                self.readouts['counts'].get_value()
                return

            # Hardware implementation
            self.experiment.Stop()
            while self.experiment.IsRunning:
                time.sleep(0.1)
            filename = self.params['filename'].get_value()
            filename = pzp.parse.format(filename, self.puzzle)
            # print('set', filename)
            self.experiment.SetValue(
                self.imports.ExperimentSettings.FileNameGenerationBaseFileName,
                self.imports.Path.GetFileName(filename))

            # print('acquire', filename)

            self.experiment.Acquire()
            while self.experiment.IsRunning:
                time.sleep(0.05)

            fname = self.automation.LightFieldApplication.FileManager.GetRecentlyAcquiredFileNames()[0]
            spe_files = self.imports.sl.load_from_files([fname])
            self.wls = spe_files.wavelength
            self.values = np.squeeze(spe_files.data)
            self.readouts['counts'].set_value(np.sum(self.values))

        @pzp.action.define(self, "Pop out")
        def popout(self):
            self.open_popup(PopupViewer, "Lightfield")

    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle, self.params['values'].get_value, .1)
        layout.addWidget(self.timer)

        self.gl = pg.GraphicsLayoutWidget()
        layout.addWidget(self.gl)

        self.plot1 = self.gl.addPlot(0, 0)
        self.plot_line = self.plot1.plot([0], [0])
        self.plot2 = self.gl.addPlot(0, 1)
        # pg.setConfigOption('useNumba', True)
        self.plot_image = pg.ImageItem(border='w', axisOrder='row-major')
        self.plot2.addItem(self.plot_image)
        self.plot2.invertY(True)

        update_later = pzp.threads.CallLater(self.update_plot)
        self.readouts['values'].changed.connect(update_later)

        return layout

    def update_plot(self):
        self.plot_line.setData(self.wls, np.sum(self.values, axis=0))
        self.plot_image.setImage(self.values)

    @pzp.piece.ensurer
    def _ensure(self):
        if not self.puzzle.debug and not hasattr(self, 'automation'):
            raise Exception("You have to launch Lightfield first.")

    @pzp.piece.ensurer
    def _stop(self):
        if not self.puzzle.debug:
            self.experiment.Stop()
            while self.experiment.IsRunning:
                time.sleep(0.1)

    def setup(self):
        pht.requirements({
            "pythonnet": {
                "pip": "pythonnet",
                "url": "https://pythonnet.github.io/pythonnet/python.html#installation"
            },
            "pygetwindow": {
                "pip": "PyGetWindow",
                "url": "https://pypi.org/project/PyGetWindow/"
            },
            "spe_loader": {
                "pip": "spe2py",
                "url": "https://pypi.org/project/spe2py/"
            }
        })
        import pzp_hardware.princeton._lightfield as _lightfield
        import pygetwindow
        self.imports = _lightfield
        self.pygetwindow = pygetwindow

    def handle_close(self, event):
        if not self.puzzle.debug and len(self.pygetwindow.getWindowsWithTitle(" - LightField")):
            box = QtWidgets.QMessageBox()
            box.setText("Please close Lightfield.")
            box.exec()

class PopupViewer(pzp.piece.Popup):
    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle, self.parent_piece['values'].get_value, .1)
        layout.addWidget(self.timer)

        self.gl = pg.GraphicsLayoutWidget()
        layout.addWidget(self.gl)

        self.plot1 = self.gl.addPlot(0, 0)
        values = self.parent_piece['values'].value
        if values is not None:
            self.plot_line = self.plot1.plot(self.parent_piece.wls, np.sum(values, axis=0))
        else:
            self.plot_line = self.plot1.plot([0], [0])
        self.plot2 = self.gl.addPlot(0, 1)
        # pg.setConfigOption('useNumba', True)
        self.plot_image = pg.ImageItem(self.parent_piece['values'].value, border='w', axisOrder='row-major')
        self.plot2.addItem(self.plot_image)
        self.plot2.invertY(True)

        def update_plot():
            self.plot_line.setData(self.parent_piece.wls, np.sum(self.parent_piece['values'].value, axis=0))
            self.plot_image.setImage(self.parent_piece['values'].value)

        update_later = pzp.threads.CallLater(update_plot)
        self.parent_piece['values'].changed.connect(update_later)

        return layout


if __name__ == "__main__":
    # If running this file directly, make a Puzzle, add our Piece, and display it
    app = pzp.QApp()
    puzzle = pzp.Puzzle(name="Camera", debug=pht.debug_prompt())
    puzzle.add_piece("camera", Piece, 0, 0)
    puzzle.show()
    app.exec()