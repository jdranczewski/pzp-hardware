import puzzlepiece as pzp
from puzzlepiece.extras import datagrid
import pyqtgraph as pg
from qtpy import QtWidgets, QtGui, QtCore
import numpy as np
from PIL import Image, ImageDraw
from skimage.transform import ProjectiveTransform, AffineTransform, warp

class CanvasObject(datagrid.Row):
    _default_name = ""

    def __init__(self, parent=None, puzzle=None):
        super().__init__(parent, puzzle)
        self._plot_item = self.make_plot_item()

    def define_params(self):
        pzp.param.text(self, "name", self._default_name)(None)
        pzp.param.slider(self, "colour", 255, 0, 255, True, 1)(None)
        pzp.param.spinbox(self, "zorder", 0)(None)

    def define_actions(self):
        @pzp.action.define(self, "Remove")
        def delete(self):
            self.parent.remove_row(self.parent.get_index(self))

    @property
    def plot_item(self):
        return self._plot_item
    
    def make_plot_item(self):
        pass

    def draw(self, draw, transform):
        raise NotImplementedError

class Square(CanvasObject):
    _default_name = "square"
    def define_actions(self):
        @pzp.action.define(self, "Reset")
        def reset(self):
            self.plot_item.setSize(200, 200)
            self.plot_item.setAngle(0)
            self.plot_item.setPos(self.parent.parent_piece.shape / 2 - 100)
        return super().define_actions()

    def make_plot_item(self):
        roi_item = pg.ROI(
            self.parent.parent_piece.shape / 2 - 100,
            [200, 200], pen=(255, 255, 0, 200)
        )
        roi_item.addScaleHandle([0.5, 1], [0.5, 0.])
        roi_item.addScaleHandle([1, 0.5], [0., 0.5])
        roi_item.addScaleHandle([1, 0], [0., 1.], lockAspect=True)
        roi_item.addRotateHandle([1, 1], [0.5, 0.5])
        return roi_item
    
    def draw(self, image, draw, transform, colour=None):
        points = (0, 0), (0, 200), (200, 200), (200, 0)

        params = self.plot_item.saveState()
        local_t = AffineTransform(
            scale=np.asarray(params["size"])/200,
            rotation=params["angle"]/180*np.pi,
            translation=params["pos"]
        )
        points = local_t._apply_mat(points, local_t.params)

        if transform is not None:
            points = transform._apply_mat(np.asarray(points), transform.params)
        draw.polygon([tuple(x) for x in points], colour or self["colour"].value)


class Triangle(Square):
    _default_name = "triangle"
    def draw(self, image, draw, transform, colour=None):
        points = (0, 200), (200, 200), (100, 200-100*np.sqrt(3))

        params = self.plot_item.saveState()
        local_t = AffineTransform(
            scale=np.asarray(params["size"])/200,
            rotation=params["angle"]/180*np.pi,
            translation=params["pos"]
        )
        points = local_t._apply_mat(points, local_t.params)

        if transform is not None:
            points = transform._apply_mat(np.asarray(points), transform.params)
        draw.polygon([tuple(x) for x in points], colour or self["colour"].value)


class Circle(Square):
    _default_name = "circle"
    def draw(self, image, draw, transform, colour=None):
        N = 32
        phase = 2 * np.pi / N
        points = [(100+100*np.sin(i*phase), 100+100*np.cos(i*phase)) for i in range(N)]

        params = self.plot_item.saveState()
        local_t = AffineTransform(
            scale=np.asarray(params["size"])/200,
            rotation=params["angle"]/180*np.pi,
            translation=params["pos"]
        )
        points = local_t._apply_mat(points, local_t.params)

        if transform is not None:
            points = transform._apply_mat(np.asarray(points), transform.params)
        draw.polygon([tuple(x) for x in points], colour or self["colour"].value)


class LinesSettings(pzp.piece.Popup):
    def define_params(self):
        self.add_child_params(("points", "colours", "width"))

    def define_actions(self):
        @pzp.action.define(self, "Reset colours")
        def reset_colours(self):
            self["colours"].set_value(np.array(None))

class Lines(Square):
    _default_name = "lines"
    def define_params(self):
        super().define_params()
        points = pzp.param.array(self, "points", False)(None)
        @points.set_setter(self)
        def set_points(self, value):
            value = np.copy(value)
            value /= np.amax(value, 0) / 200
            return value
        pzp.param.array(self, "colours", False)(None)
        pzp.param.spinbox(self, "width", 5, visible=False)(None)
    
    def define_actions(self):
        super().define_actions()
        
        @pzp.action.define(self, "Settings")
        def settings(self):
            self.open_popup(LinesSettings, f"{self['name'].value} settings")
    
    def draw(self, image, draw, transform):
        if self["points"].value is not None:
            points = self["points"].value

            params = self.plot_item.saveState()
            local_t = AffineTransform(
                scale=np.asarray(params["size"])/200,
                rotation=params["angle"]/180*np.pi,
                translation=params["pos"]
            )
            points = local_t._apply_mat(points, local_t.params)

            if transform is not None:
                points = transform._apply_mat(points, transform.params)
            if self["colours"].value is None or self["colours"].value.shape == ():
                for i in range(0, len(points), 2):
                    draw.line([tuple(points[i]), tuple(points[i+1])], self["colour"].value, self["width"].value)
            else:
                for i in range(0, len(points), 2):
                    draw.line([tuple(points[i]), tuple(points[i+1])], int(self["colours"].value[i//2]), self["width"].value)

class CanvasImage(Square):
    _default_name = "image"
    def define_params(self):
        super().define_params()
        image = pzp.param.array(self, "image", False)(None)
        @image.set_setter(self)
        def image(self, value):
            return np.pad(value, ((1, 0), (1, 0)))
        image.set_value(np.random.random((200, 200)) * 255)

        self._mask = Image.new("1", tuple(self.parent.parent_piece.shape), 0)
        self._mask_draw = ImageDraw.Draw(self._mask)

        self._mask_dmd = Image.new("1", tuple(self.parent.parent_piece.tshape), 0)
        self._mask_draw_dmd = ImageDraw.Draw(self._mask_dmd)

    def draw(self, image, draw, transform):
        to_display = self["image"].get_value()

        params = self.plot_item.saveState()
        scale = np.asarray(params["size"])/to_display.shape
        local_t = AffineTransform(
            scale=scale,
            rotation=params["angle"]/180*np.pi,
            translation=params["pos"]
        )

        warped = warp(
            to_display,
            local_t.inverse,
            order=0,
            output_shape=self.parent.parent_piece.shape[::-1]
        )

        if transform is None:
            self._mask_draw.rectangle(((0, 0), self._mask.size), 0)
            super().draw(image, self._mask_draw, transform, 1)
            image.paste(Image.fromarray(warped), None, self._mask)
        else:
            self._mask_draw_dmd.rectangle(((0, 0), self._mask_dmd.size), 0)
            super().draw(image, self._mask_draw_dmd, transform, 1)
            
            warped = warp(
                warped,
                transform.inverse,
                order=0,
                output_shape=self.parent.parent_piece.tshape[::-1],
            )
            image.paste(Image.fromarray(warped), None, self._mask_dmd)

class AddObject(pzp.piece.Popup):
    def define_params(self):
        keys = list(self.parent_piece.kinds.keys())
        pzp.param.dropdown(self, "kind", keys[0])(keys)

    def define_actions(self):
        @pzp.action.define(self, "Add")
        def add(self):
            self.parent_piece.add_object_by_name(self["kind"].value)

class Callibration(pzp.piece.Popup):
    def define_params(self):
        self.add_child_params(("camera_source", "camera_image"))

    def define_actions(self):
        @pzp.action.define(self, "Draw pattern")
        def draw_pattern(self):
            # Make the callibration image
            self.image = Image.new("L", tuple(self.parent_piece.tshape), 0)
            self.draw = ImageDraw.Draw(self.image)
            radius = 200
            centre = np.array((self.parent_piece.tshape[0] // 2, self.parent_piece.tshape[1] // 2))
            self.points = []
            for i in range(4):
                vector = np.array((np.sin(i*np.pi/2), -np.cos(i*np.pi/2))) * radius
                self.draw.line((*(centre + vector), *(centre + vector*.7)), 255, 10)
                self.points.append(centre + vector)
                for j in range(i+1):
                    self.draw.line((*(centre + vector*(.6-.1*j)), *(centre + vector*(.55-.1*j))), 255, 10)
            # Display the callibration image on the DMD
            try:
                param = pzp.parse.parse_params(self.parent_piece["destination"].value, self.puzzle)[0]
            except (ValueError, SyntaxError):
                raise Exception("Could not find a destination image.")
            param.set_value(np.asarray(self.image))

        @pzp.action.define(self, "Save")
        def save(self):
            self.parent_piece.tform.estimate([x.pos() for x in self.targets], self.points)
            self.parent_piece._auto_project()

    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle, self.params['camera_image'].get_value, 0.1)
        layout.addWidget(self.timer)

        # Display a plot with a preview from the camera
        pw = pg.PlotWidget()
        layout.addWidget(pw)
        self.plot = pw.getPlotItem()
        self.plot.setAspectLocked(True)
        self.plot.invertY(True)

        self.image_item = pg.ImageItem(border='w', axisOrder='row-major')
        self.plot.addItem(self.image_item)

        def update_image():
            self.image_item.setImage(self['camera_image'].value)
        update_later = pzp.threads.CallLater(update_image)
        self.params['camera_image'].changed.connect(update_later)

        self.actions["Draw pattern"]()

        # Add a ROI
        points = np.array([[0,0], [100,0], [100,100], [0,100], [0, 0]])
        if np.sum(self.parent_piece.tform.params) != 3:
            points = self.parent_piece.tform._apply_mat(self.points, self.parent_piece.tform._inv_matrix)
        self.line = self.plot.plot()
        self.targets = []
        def update_line():
            coordinates = np.array([x.pos() for x in self.targets] + [self.targets[0].pos()])
            self.line.setData(*coordinates.T)
        for i, point in enumerate(points[:4]):
            self.plot.addItem(target := pg.TargetItem(point, label=str(i+1)))
            target.sigPositionChanged.connect(update_line)
            self.targets.append(target)
        update_line()

        return layout

class Piece(pzp.Piece):
    shape = np.array((1280, 800))
    shape = np.array((1440, 1080))
    tshape = np.array((1280, 800))

    kinds = {
        "square": Square,
        "triangle": Triangle,
        "circle": Circle,
        "lines": Lines,
        "image": CanvasImage
    }

    def param_layout(self, wrap=2):
        return super().param_layout(wrap)

    def define_params(self):
        pzp.param.text(self, "camera_source", "camera:image", visible=False)(None)

        @pzp.param.array(self, "camera_image", True)
        def image(self):
            param = pzp.parse.parse_params(self["camera_source"].value, self.puzzle)[0]
            return param.get_value()
        
        def draw_image(draw, image, tform):
            draw.rectangle(((0, 0), image.size), 0)
            zorders = [row["zorder"].value for row in self.dg.rows]
            rows = [x for y, x in sorted(zip(zorders, self.dg.rows), key=lambda pair: pair[0])]
            for row in rows:
                row.draw(image, draw, tform)
            return np.asarray(image)
        
        @pzp.param.array(self, "image")
        def image(self):
            return draw_image(self.draw, self.image, None)
        
        @pzp.param.array(self, "transformed", False)
        def transformed(self):
            return draw_image(self.tdraw, self.timage, self.tform)
        
        self.tform = ProjectiveTransform()
        
        pzp.param.text(self, "destination", "")(None)
        auto_project = pzp.param.checkbox(self, "auto_project", 0)(None)
        auto_project.changed.connect(self._auto_project)
        pzp.param.checkbox(self, "show_camera", 0)(None)
        pzp.param.checkbox(self, "auto_camera", 0)(None)

    def define_actions(self):
        @pzp.action.define(self, "Callibrate")
        def callibrate(self):
            self.open_popup(Callibration, "Callibrate canvas")

        @pzp.action.define(self, "Project")
        def project(self):
            param = pzp.parse.parse_params(self["destination"].value, self.puzzle)[0]
            param.set_value(self["transformed"].get_value())

        @pzp.action.define(self, "Add object")
        def add_object(self):
            self.open_popup(AddObject, "Add canvas object")

    def add_object_by_name(self, kind):
        row = self.dg.add_row(self.kinds[kind])
        self.plot.addItem(row.plot_item)
        row.actions["Remove"].called.connect(lambda: self.plot.removeItem(row.plot_item))
        row.plot_item.sigHoverEvent.connect(lambda: self.dg.select_row(self.dg.get_index(row)))
        row.plot_item.sigRegionChanged.connect(self["image"].get_value)
        row.plot_item.sigRegionChanged.connect(self._auto_project)
        return row

    def get_object(self, name):
        for row in self.dg.rows:
            if row["name"].value == name:
                return row
    
    def _auto_project(self):
        if self["auto_project"].value:
            self.actions["Project"]()
            if self["auto_camera"].value:
                self["camera_image"].get_value()

    def custom_layout(self):
        layout = QtWidgets.QGridLayout()

        self.dg = datagrid.DataGrid(CanvasObject, self.puzzle, self)
        self.dg.data_changed.connect(self["image"].get_value)
        self.dg.data_changed.connect(self._auto_project)
        layout.addWidget(self.dg, 0, 0)

        pw = pg.PlotWidget()
        layout.addWidget(pw, 1, 0)
        self.plot = pw.getPlotItem()
        self.plot.setAspectLocked(True)
        self.plot.invertY(True)

        self.camera_item = pg.ImageItem(border='w', axisOrder='row-major')
        self.plot.addItem(self.camera_item)

        self.image = Image.new("L", tuple(self.shape), 0)
        self.image_item = pg.ImageItem(np.asarray(self.image), border='w', axisOrder='row-major', levels=[0, 255])
        self.plot.addItem(self.image_item)
        self.draw = ImageDraw.Draw(self.image)
        
        self.timage = Image.new("L", tuple(self.tshape), 0)
        self.tdraw = ImageDraw.Draw(self.timage)

        def update_camera():
            self.camera_item.setImage(self['camera_image'].value)
        update_later_camera = pzp.threads.CallLater(update_camera)
        self.params['camera_image'].changed.connect(update_later_camera)

        def update_image():
            self.image_item.setImage(self['image'].value, autoLevels=False)
        update_later = pzp.threads.CallLater(update_image)
        self.params['image'].changed.connect(update_later)

        white, red = (
            pg.ColorMap(None, ((0, 0, 0), (255, 255, 255))),
            pg.ColorMap(None, ((0, 0, 0), (255, 0, 0))),
        )
        def switch_camera():
            if self["show_camera"].value:
                self.image_item.setOpacity(.5)
                self.image_item.setColorMap(red)
            else:
                self.image_item.setOpacity(1)
                self.image_item.setColorMap(white)
        self["show_camera"].changed.connect(switch_camera)

        return layout
    
if __name__ == "__main__":
    app = pzp.QApp([])
    puzzle = pzp.Puzzle()
    puzzle.add_piece("canvas", Piece, 0, 0)
    puzzle.show()
    app.exec()