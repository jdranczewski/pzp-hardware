# This file is a part of pzp-hardware, a library of laboratory hardware support
# Pieces for the puzzlepiece GUI & automation framework.
# Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
Pieces for interacting with `Thorlabs scientific cameras <https://www.thorlabs.com/navigation.cfm?guide_id=2025>`__
using the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework.

Example usage (see :ref:`getting-started` for more details on using Pieces in general)::

    import puzzlepiece as pzp
    from pzp_hardware.thorlabs import camera

    app = pzp.QApp()
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("camera", camera.Piece, row=0, col=0)
    puzzle.show()
    app.exec()

Installation
------------
* Install ThorCam (not ThorImageCam) from https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=ThorCam
* Locate ``Scientific_Camera_Interfaces.zip``
  (usually in ``C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support``)
* Unzip the file to a convenient location
* In the unzipped folder, go to ``SDK/Python Toolki`` and install the provided package zip file in your Python
  environment, for example with ``pip install "<path to thorlabs_tsi_camera_python_sdk_package.zip>"``
* In the unzipped folder, locate ``SDK\Native Toolkit\dlls\Native_64_lib`` and copy its full path (starting with ``C:``
  or another drive letter)
* When running the Piece for the first time, you will be asked for the DLL directory - provide the one you copied above.

Requirements
------------
.. pzp_requirements:: pzp_hardware.thorlabs.camera

Available Pieces
----------------
"""
import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np
import os, sys

pht.requirements({
    "PIL": {
        "pip": "pillow",
        "url": "https://pillow.readthedocs.io/en/stable/installation/basic-installation.html"
    }
})
from PIL import Image

from pzp_hardware.generic.mixins import image_preview


class _Settings(pzp.piece.Popup):
    """
    Popup to handle showing settings (params and actions that are normally hidden).
    """
    def define_params(self):
        self.add_invisible_params()
        return super().define_params()

    def define_actions(self):
        self.add_child_actions(("Take background", "ROI", "Rediscover", "Trigger"))
        return super().define_actions()

class Base(pzp.Piece):
    """
    Base camera Piece without a preview. Can be used to get images and show settings
    without an explicit image view in the UI.
    """
    custom_horizontal = True

    def define_params(self):
        #region Connecting

        # Make a parameter for the serial number of the camera
        @pzp.param.dropdown(self, 'serial', '')
        def get_serials(self):
            if self.puzzle.debug:
                return None
            return self.puzzle.globals['tlc_sdk'].discover_available_cameras()

        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                # Do nothing if we're in debug mode
                return 1
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

        @pzp.param.disconnect(self)
        def disconnect():
            if self.puzzle.debug:
                return 0
            # Disconnect from the camera
            self.dispose()
            return 0
        #endregion

        #region Image, triggering
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

        @pzp.param.group("Triggering")
        @pzp.param.checkbox(self, "unlimited", 0, visible=False)
        @self._ensure_connected
        @self._ensure_disarmed
        def unlimited(self, value):
            if self.puzzle.debug:
                return value

            self.camera.frames_per_trigger_zero_for_unlimited = not value

        # Make a checkbox for arming the camera
        self._triggered = 0
        @pzp.param.group("Triggering")
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

        pzp.param.spinbox(self, "frame_buffer", 2, visible=False)(None).set_group("Triggering")
        #endregion

        #region Exposure
        # The exposure value can be set - that's what this function does
        @pzp.param.group("Exposure")
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
                return self.params['exposure'].value or 1
            # If we're connected and not in debug mode, return the exposure from the camera
            return self.camera.exposure_time_us / 1000

        @pzp.param.group("Exposure")
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
                return self.params['gain'].value or 0
            # If we're connected and not in debug mode, return the exposure from the camera
            return self.camera.gain

        @pzp.param.group("Exposure")
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

        @pzp.param.group("Exposure")
        @pzp.param.readout(self, 'counts', False)
        def get_counts(self):
            image = self.params['image'].get_value()
            return np.sum(image)

        @pzp.param.group("Exposure")
        @pzp.param.readout(self, 'max_counts', False)
        def get_counts(self):
            image = self.params['image'].get_value()
            return np.amax(image)
        #endregion

        @pzp.param.group("Region of interest")
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

        pzp.param.checkbox(self, 'sub_background', 0, visible=False)(None).set_group("Background")
        pzp.param.array(self, 'background', False)(None).set_group("Background")

        super().define_params()

    #MARK: Actions
    def define_actions(self):
        @pzp.action.define(self, 'Take background', visible=False)
        def take_background(self):
            background = self.params['image'].get_value()
            self.params['background'].set_value(background)

        @pzp.action.define(self, "ROI", visible=False)
        @self._ensure_connected
        def roi(self):
            self.open_popup(_ROI_Popup, "Camera Region of Interest")

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
            self.open_popup(_Settings, "Camera settings")

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

    #MARK: API setup
    def setup(self):
        # This function is called if not in debug mode to setup the hardware connection API
        if not self.puzzle.globals.require('tlc_sdk'):
            # If the SDK has not been set up yet, we set it up here
            pht.requirements({"thorlabs_tsi_sdk": {
                "url": "https://pzp-hardware.readthedocs.io/en/latest/pzp_hardware.thorlabs.camera.html#installation"
            }})
            dll_directory = r"C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support\Scientific Camera Interfaces\SDK\Native Toolkit\dlls\Native_64_lib"
            dll_directory = pht.config("thorcam_dll_directory", default=dll_directory, validator=pht.validator_path_exists)
            pht.add_dll_directory(dll_directory)

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


#MARK: ROI Popup
class _ROI_Popup(pzp.piece.Popup):
    """
    Popup for setting the camera's Region of Interest (ROI).
    """
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


#MARK: Main Pieces
class Piece(image_preview.ImagePreview, Base):
    """
    Like :class:`~pzp-hardware.thorlabs.camera.Base`, but includes a preview for the
    captured image. Can be made to run live.
    """
    live_toggle = True
    autolevel_toggle = True
    max_counts = 1023


class LineoutPiece(image_preview.LineoutImagePreview, Base):
    """
    Like :class:`~pzp-hardware.thorlabs.camera.Piece` above, but the preview includes
    two movable lines (horizontal and vertical), and plots that show the image profile
    along these lines. These can also act as a crosshair for alignment, and a circle is
    shown where they cross.
    """
    live_toggle = True
    autolevel_toggle = True
    max_counts = 1023


if __name__ == "__main__":
    from puzzlepiece.pieces import plotter
    # If running this file directly, make a Puzzle, add our Piece, and display it
    app = pzp.QApp()
    puzzle = pzp.Puzzle(app, "Camera", debug=True)
    puzzle.add_piece("camera", LineoutPiece, 0, 0)
    puzzle.show()
    app.exec()