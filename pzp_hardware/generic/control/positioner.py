import puzzlepiece as pzp
from qtpy import QtWidgets
import pyqtgraph as pg
import numpy as np

class Piece(pzp.Piece):
    def define_params(self):
        pzp.param.text(self, "source", "camera:image", visible=False)(None)
        pzp.param.text(self, "xy", "piezo:x_set, piezo:y_set", visible=False)(None)
        pzp.param.spinbox(self, "threshold", 0)(None)
        pzp.param.spinbox(self, "mult", 50, visible=False)(None)
        pzp.param.text(self, "mults", "1,-1", visible=False)(None)
        pzp.param.spinbox(self, "tolerance", 1., visible=False)(None)


        @pzp.param.array(self, "image", visible=False)
        def image(self):
            param = pzp.parse.parse_params(self["source"].value, self.puzzle)[0]
            image = param.get_value().copy()
            image[image < self["threshold"].value] = 0
            return image
        
        @pzp.param.array(self, "cg")
        def cg(self):
            image = self["image"].get_value().astype(float)
            x1, y1 = self.roi_item.pos()
            x2, y2 = self.roi_item.size()
            x2 += x1
            y2 += y1
            x1, x2, y1, y2 = (int(np.round(x)) for x in (x1, x2, y1, y2))
            x1 = x1 if x1>0 else 0
            y1 = y1 if y1>0 else 0

            sliced_image = image[y1:y2, x1:x2]
            x = np.arange(sliced_image.shape[1])
            y = np.arange(sliced_image.shape[0])
            xx, yy = np.meshgrid(x, y)
            A = sliced_image.sum()
            if A == 0:
                centre = (x1 + sliced_image.shape[1]//2, y1 + sliced_image.shape[0]//2)
            else:
                centre = (
                    np.sum(xx * sliced_image) / A + x1,
                    np.sum(yy * sliced_image) / A + y1,
                )
            self.ind_target.setPos((centre[0], centre[1]))
            return centre
        
    def define_actions(self):
        @pzp.action.define(self, "Move")
        def move(self):
            self.stop = False
            self.timer.stop()
            goal = np.asarray(self.goal_target.pos())
            mults = [int(x) for x in self["mults"].get_value().split(",")]
            xy = pzp.parse.parse_params(self["xy"].value, self.puzzle)
            tolerance = self["tolerance"].value ** 2
            for i in range(50):
                cg = self["cg"].get_value()
                if np.sum(np.square(goal - cg)) < tolerance or self.stop:
                    break
                for axis in range(2):
                    diff = goal[axis] - cg[axis]
                    current = xy[axis].get_value()
                    xy[axis].set_value(current + diff * self["mult"].value * 0.0001 * mults[axis])
                self.puzzle.process_events()
            self["cg"].get_value()

        @pzp.action.define(self, "Settings")
        def settings(self):
            self.open_popup(Settings, "Positioner settings")

        
    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle, self.params['cg'].get_value, 0.1)
        layout.addWidget(self.timer)

        # Make an ImageView
        self.pw = pg.PlotWidget()
        layout.addWidget(self.pw)

        plot_item = self.pw.getPlotItem()
        plot_item.setAspectLocked(True)
        plot_item.invertY(True)
        plot_item.showGrid(True, True)

        self.imgw = pg.ImageItem(border='w', axisOrder='row-major')
        plot_item.addItem(self.imgw)

        def update_image():
            self.imgw.setImage(self['image'].value)
        update_later = pzp.threads.CallLater(update_image)
        self.params['image'].changed.connect(update_later)

        # Make a ROI
        self.roi_item = pg.ROI([0, 0], [200, 200], pen=(255, 255, 0, 200))
        self.roi_item.addScaleHandle([0.5, 1], [0.5, 0.5])
        self.roi_item.addScaleHandle([1, 0.5], [0.5, 0.5])
        self.imgw.update()
        plot_item.addItem(self.roi_item)

        # Make an indicator target
        self.ind_target = pg.TargetItem((0, 0), movable=False, pen=(100, 100, 255))
        plot_item.addItem(self.ind_target)

        self.goal_target = pg.TargetItem((0, 0))
        plot_item.addItem(self.goal_target)
        self.goal_target.setZValue(10)

        return layout
    
    def call_stop(self):
        self.timer.stop()
        return super().call_stop()


class Settings(pzp.piece.Popup):
    def define_params(self):
        self.add_child_params(("source", "xy", "mult", "mults", "tolerance"))
    