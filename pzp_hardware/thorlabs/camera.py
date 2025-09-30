import puzzlepiece as pzp
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np
import os, sys
from PIL import Image

class Settings(pzp.piece.Popup):
    def define_params(self):
        self.add_child_params(("unlimited", "armed", "black", "frame_buffer", "counts", "max_counts", "sub_background"))
        return super().define_params()
    
    def define_actions(self):
        self.add_child_actions(("Take background", "ROI", "Rediscover", "Trigger"))
        return super().define_actions()

class Base(pzp.Piece):
    def __init__(self, puzzle):
        # Move the custom_layout to the right of the generated inputs
        super().__init__(puzzle, custom_horizontal=True)
        # self.image will store the image the camera takes
        self.image = None

    def define_params(self):
        # Make a parameter for the serial number of the camera
        @pzp.param.dropdown(self, 'serial', '')
        def get_serials(self):
            if self.puzzle.debug:
                return None
            return self.puzzle.globals['tlc_sdk'].discover_available_cameras()

        # Make a checkbox for connecting to the camera. Clicking the checkbox will call
        # the function below - if checked, the function gets value=1, otherwise 0
        @pzp.param.checkbox(self, "connected", 0)
        def connect(self, value):
            if self.puzzle.debug:
                # Do nothing if we're in debug mode
                return 1
            # Check if we're currently connected by seing what the state of the checkbox was
            current_value = self.params['connected'].value

            if value and not current_value:
                # Connect to the camera
                try:
                    # See the Thorlabs camera SDK for the details of the functions that are called here
                    # Also see the setup() method below to see where self._TLCameraSDK came from.
                    self.camera = self.puzzle.globals['tlc_sdk'].open_camera(self.params['serial'].get_value())
                    self.camera.image_poll_timeout_ms = 1000
                    if self["unlimited"].value is not None:
                        self.camera.frames_per_trigger_zero_for_unlimited = not self["unlimited"].value
                    else:
                        self.camera.frames_per_trigger_zero_for_unlimited = 1
                    return 1
                except Exception as e:
                    self.dispose()
                    raise e
            elif current_value:
                # Disconnect from the camera
                self.dispose()
                return 0
            
        @pzp.param.checkbox(self, "unlimited", 0, visible=False)
        @self._ensure_disarmed
        @self._ensure_connected
        def unlimited(self, value):
            if self.puzzle.debug:
                return value

            self.camera.frames_per_trigger_zero_for_unlimited = not value
            
        # Make a checkbox for arming the camera
        self._triggered = 0
        @pzp.param.checkbox(self, "armed", 0, visible=False)
        @self._ensure_connected
        def armed(self, value):
            if self.puzzle.debug:
                return 1
            current_value = self.params['armed'].value
            
            if value and not current_value:
                # Arm and trigger the camera
                self.camera.arm(self["frame_buffer"].value)
                self._triggered = 0
                return 1
            elif not value and current_value:
                self.camera.disarm()
                self._triggered = 0
                return 0
            return current_value
            
        # The exposure value can be set - that's what this function does
        @pzp.param.spinbox(self, "exposure", 25.)
        @self._ensure_connected
        def exposure(self, value):
            if self.puzzle.debug:
                return value
            # If we're connected and not in debug mode, set the exposure
            self.camera.exposure_time_us = int(value*1000)

        # The exposure can also be read from the camera (it stores is internally),
        # so here we register a 'getter' for the exposure param - a function
        # called to see what the current exposure value is.
        @exposure.set_getter(self)
        @self._ensure_connected
        def get_exposure(self):
            if self.puzzle.debug:
                return self.params['exposure'].value
            # If we're connected and not in debug mode, return the exposure from the camera
            return self.camera.exposure_time_us / 1000

        @pzp.param.spinbox(self, "gain", 0)
        @self._ensure_connected
        def gain(self, value):
            if self.puzzle.debug:
                return value
            self.camera.gain = value

        @gain.set_getter(self)
        @self._ensure_connected
        def gain(self):
            if self.puzzle.debug:
                return self.params['gain'].value
            # If we're connected and not in debug mode, return the exposure from the camera
            return self.camera.gain
        
        @pzp.param.spinbox(self, "black", 0, visible=False)
        @self._ensure_connected
        def black(self, value):
            if self.puzzle.debug:
                return value
            self.camera.black_level = value

        @black.set_getter(self)
        @self._ensure_connected
        def black(self):
            if self.puzzle.debug:
                return self.params['black'].value
            # If we're connected and not in debug mode, return the exposure from the camera
            return self.camera.black_level
        
        @pzp.param.array(self, 'roi', False)
        @self._ensure_connected
        def roi(self):
            if not self.puzzle.debug:
                return self.camera.roi
            return [0, 0, 99, 79]
            
        @roi.set_setter(self)
        @self._ensure_connected
        @self._ensure_disarmed
        def roi(self, value):
            if not self.puzzle.debug:
                self.camera.roi = value
        
        @pzp.param.array(self, 'image')
        @self._ensure_connected
        @self._ensure_armed
        def get_image(self):
            if self.puzzle.debug:
                # If we're in debug mode, we just return random noise
                image = np.random.random((1080, 1440))*1024
            else:
                if not self["unlimited"].value or not self._triggered:
                    self.actions["Trigger"]()
                frame = self.camera.get_pending_frame_or_null()
                if frame is None:
                    raise Exception('Acquisition did not complete within the timeout...')
                # Copy the image we got and save a reference internally
                image = frame.image_buffer[:,::-1].copy()
            if self.params['sub_background'].get_value():
                image -= self.params['background'].get_value()
            return image
            
        @pzp.param.readout(self, 'counts', False)
        def get_counts(self):
            image = self.params['image'].get_value()
            return np.sum(image)
        
        @pzp.param.readout(self, 'max_counts', False)
        def get_counts(self):
            image = self.params['image'].get_value()
            return np.amax(image)
        
        pzp.param.checkbox(self, 'sub_background', 0, visible=False)(None)
        pzp.param.array(self, 'background', False)(None)
        pzp.param.spinbox(self, "frame_buffer", 2, visible=False)(None)

    def define_actions(self):
        @pzp.action.define(self, 'Take background', visible=False)
        def take_background(self):
            background = self.params['image'].get_value()
            self.params['background'].set_value(background)

        @pzp.action.define(self, "ROI", visible=False)
        @self._ensure_connected
        def roi(self):
            self.open_popup(ROI_Popup)

        @pzp.action.define(self, "Reset ROI", visible=False)
        @self._ensure_connected
        @self._ensure_disarmed
        def reset_roi(self):
            if not self.puzzle.debug:
                self.params['roi'].set_value([0, 0, self.camera.roi_range[-2], self.camera.roi_range[-1]])

        @pzp.action.define(self, 'Save image')
        def save_image(self, filename=None):
            image = self.params['image'].value
            if image is None:
                image = self.params['image'].get_value()

            if filename is None:
                filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                    self.puzzle, 'Save file as...', 
                    '.', "Image files (*.png)")
            
            Image.fromarray((image // 4).astype(np.uint8)).save(filename)
        
        @pzp.action.define(self, "Rediscover", visible=False)
        def rediscover(self):
            if not self.puzzle.debug:
                self.params["serial"].input.addItems(
                    self.puzzle.globals['tlc_sdk'].discover_available_cameras()
                )

        @pzp.action.define(self, "Trigger", visible=False)
        def trigger(self):
            self._triggered = True
            if not self.puzzle.debug:
                self.camera.issue_software_trigger()

        @pzp.action.define(self, "Settings")
        def settings(self):
            self.open_popup(Settings, "Camera settings")

    @pzp.piece.ensurer
    def _ensure_connected(self):
        if not self.puzzle.debug and not self.params['connected'].value:
            raise Exception('Camera not connected')
        
    @pzp.piece.ensurer
    def _ensure_armed(self):
        if not self.params['armed'].value:
            self.params['armed'].set_value(1)
    
    @pzp.piece.ensurer
    def _ensure_disarmed(self):
        if self.params['armed'].value:
            self.params['armed'].set_value(0)

    def setup(self):
        # This function is called if not in debug mode to setup the hardware connection API
        if not self.puzzle.globals.require('tlc_sdk'):
            # If the SDK has not been set up yet, we set it up here
            dll_directory = r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support\Scientific Camera Interfaces\SDK\Native Toolkit\dlls\Native_64_lib"
            os.environ["PATH"] = dll_directory + os.pathsep + os.environ["PATH"]
            os.add_dll_directory(dll_directory)
            from thorlabs_tsi_sdk.tl_camera import TLCameraSDK
            self.puzzle.globals['tlc_sdk'] = TLCameraSDK()

    def dispose(self):
        # This function 'disposes' of the camera, effectively disconnecting us
        if hasattr(self, 'camera'):
            self.camera.dispose()
            del self.camera

    def handle_close(self, event):
        # This function is called when the Puzzle is closed, enabling us to disconnect
        # from the camera and SDK before the app shuts down
        if not self.puzzle.debug:
            # Disconnect from the camera
            self.dispose()
        if not self.puzzle.debug and self.puzzle.globals.release('tlc_sdk'):
            # If we are the last Piece using the SDK, we shut the SDK down
            self.puzzle.globals['tlc_sdk'].dispose()
            del self.puzzle.globals['tlc_sdk']


class ROI_Popup(pzp.piece.Popup):
    def define_actions(self):
        @pzp.action.define(self, "set_roi_from_camera", visible=False)
        def set_roi_from_camera(self):
            camera_roi = self.parent_piece.params['roi'].get_value()
            self.roi_item.setPos(camera_roi[:2])
            self.roi_item.setSize([camera_roi[2]-camera_roi[0]+1, camera_roi[3]-camera_roi[1]+1])

        @pzp.action.define(self, "Capture ref")
        def capture_reference(self):
            if not self.puzzle.debug:
                original_roi = self.parent_piece.params['roi'].get_value()
                self.parent_piece.params['armed'].set_value(0)
                self.parent_piece.actions['Reset ROI']()
            self.parent_piece.params['armed'].set_value(1)
            image = self.parent_piece.params['image'].get_value()
            self._rows, self._cols = image.shape
            self.imgw.setImage(image[:,::-1])
            if not self.puzzle.debug:
                self.parent_piece.params['armed'].set_value(0)
                self.parent_piece.params['roi'].set_value(original_roi)

        @pzp.action.define(self, "Set ROI")
        def set_roi(self):
            x1, y1 = self.roi_item.pos()
            x2, y2 = self.roi_item.size()
            x2 += x1 - 1
            y2 += y1 - 1
            x1, x2, y1, y2 = (int(np.round(x)) for x in (x1, x2, y1, y2))
            x1 = x1 if x1>0 else 0
            y1 = y1 if y1>0 else 0
            x2 = x2 if x2<self._cols-1 else self._cols-1
            y2 = y2 if y2<self._rows-1 else self._rows-1
            self.parent_piece.params['armed'].set_value(0)
            self.parent_piece.params['roi'].set_value((x1, y1, x2, y2))
            self.actions['set_roi_from_camera']()

        @pzp.action.define(self, "Centre")
        def centre_roi(self):
            pos, size = self.roi_item.pos(), self.roi_item.size()
            self.roi_item.setPos((self._cols/2 - size[0]/2, self._rows/2 - size[1]/2))

        @pzp.action.define(self, "Reset")
        def reset_roi(self):
            self.roi_item.setPos((0, 0))
            self.roi_item.setSize((self._cols, self._rows))

    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        # Make an ImageView
        self.pw = pg.PlotWidget()
        layout.addWidget(self.pw)

        plot_item = self.pw.getPlotItem()
        plot_item.setAspectLocked(True)
        plot_item.invertY(True)
        plot_item.showGrid(True, True)

        self.imgw = pg.ImageItem(border='w', axisOrder='row-major')
        plot_item.addItem(self.imgw)

        # Make a ROI
        self.roi_item = pg.ROI([0, 0], [10, 10], pen=(255, 255, 0, 200))
        self.roi_item.addScaleHandle([0.5, 1], [0.5, 0.5])
        self.roi_item.addScaleHandle([1, 0.5], [0.5, 0.5])
        self.actions['set_roi_from_camera']()
        self.actions['Capture ref']()
        self.imgw.update()
        plot_item.addItem(self.roi_item)

        return layout
    
class Piece(Base):
    def define_params(self):
        super().define_params()

        @pzp.param.checkbox(self, "autolevel", 0)
        def autolevel(self, value):
            image = self["image"].value
            if value and image is not None:
                self.imgw.setLevels([np.amin(image), np.amax(image)])
            else:
                self.imgw.setLevels([0, 1024])

    # Within this function we can define any other GUI objects we want to display beyond the 
    # params and actions (which are generated by default)
    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        # Add a PuzzleTimer for live view
        delay = 0.05 if not self.puzzle.debug else 0.1 # Introduce artificial delay for debug mode
        self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle, self.params['image'].get_value, delay)
        layout.addWidget(self.timer)

        # Make an ImageView
        self.pw = pg.PlotWidget()
        layout.addWidget(self.pw)

        plot_item = self.pw.getPlotItem()
        plot_item.setAspectLocked(True)
        plot_item.invertY(True)

        # numba makes this slightly faster, uncomment if needed
        # pg.setConfigOption('useNumba', True)
        self.imgw = pg.ImageItem(border='w', axisOrder='row-major', levels=[0, 1024])
        self["autolevel"].set_value(0)
        plot_item.addItem(self.imgw)

        def update_image():
            self.imgw.setImage(self.params['image'].value, autoLevels=self["autolevel"].value)
        update_later = pzp.threads.CallLater(update_image)
        self.params['image'].changed.connect(update_later)

        # histogram = pg.HistogramLUTWidget(orientation='horizontal')
        # layout.addWidget(histogram)
        # histogram.setImageItem(self.imgw)

        return layout
    
    def call_stop(self):
        self.timer.stop()

class LineoutPiece(Piece):
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
        layout = QtWidgets.QVBoxLayout()

        # Add a PuzzleTimer for live view
        self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle, self.params['image'].get_value, 0.1)
        layout.addWidget(self.timer)

        # Make the plots
        self.gl = pg.GraphicsLayoutWidget()
        layout.addWidget(self.gl)
        self.gl.ci.layout.setRowStretchFactor(0, 2)
        self.gl.ci.layout.setColumnStretchFactor(0, 2)

        plot_main = self.gl.addPlot(0, 0)
        plot_x = self.gl.addPlot(1, 0)
        plot_x.setXLink(plot_main)
        plot_y = self.gl.addPlot(0, 1)
        plot_y.setYLink(plot_main)

        plot_main.setAspectLocked(True)
        plot_main.invertY(True)
        plot_y.invertY(True)

        # numba makes this slightly faster, uncomment if needed
        # pg.setConfigOption('useNumba', True)
        self.imgw = pg.ImageItem(border='w', axisOrder='row-major', levels=[0, 1024])
        self["autolevel"].set_value(0)
        plot_main.addItem(self.imgw)

        self._inf_line_x = pg.InfiniteLine(0, 0, movable=True)
        self._inf_line_y = pg.InfiniteLine(0, 90, movable=True)
        plot_main.addItem(self._inf_line_x)
        plot_main.addItem(self._inf_line_y)

        r = self.params['circle_r'].value
        self._circle = QtWidgets.QGraphicsEllipseItem(-r, -r, r*2, r*2)  # x, y, width, height
        self._circle.setPen(pg.mkPen((255, 255, 0, 150)))
        plot_main.addItem(self._circle)

        plot_line_x = plot_x.plot([0], [0])
        plot_line_y = plot_y.plot([0], [0])

        def update_image():
            image_data = self.params['image'].value
            self.imgw.setImage(image_data, autoLevels=self["autolevel"].value)
            r = self.params['circle_r'].value
            self._circle.setRect(self._inf_line_y.value()-r,
                                 self._inf_line_x.value()-r,
                                 r*2, r*2)
            plot_line_x.setData(image_data[int(self._inf_line_x.value())])
            i = int(self._inf_line_y.value())
            plot_line_y.setData(image_data[:, i], range(len(image_data[:, i])))
        update_later = pzp.threads.CallLater(update_image)
        self.params['image'].changed.connect(update_later)
        self._inf_line_x.sigPositionChanged.connect(update_image)
        self._inf_line_y.sigPositionChanged.connect(update_image)

        return layout
    
    def call_stop(self):
        self.timer.stop()


if __name__ == "__main__":
    from puzzlepiece.pieces import plotter
    # If running this file directly, make a Puzzle, add our Piece, and display it
    app = QtWidgets.QApplication([])
    puzzle = pzp.Puzzle(app, "Camera", debug=True)
    puzzle.add_piece("camera", LineoutPiece(puzzle), 0, 0)
    puzzle.add_piece("plotter", plotter := plotter.Piece(puzzle), 0, 1)
    plotter.params['param'].set_value("camera:counts")
    puzzle.show()
    app.exec()