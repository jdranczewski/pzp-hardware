import puzzlepiece as pzp
from qtpy import QtCore

class Piece(pzp.Piece):
    def define_params(self):
        pzp.param.text(self, 'params', '')(None)
        pzp.param.spinbox(self, 'delta', .05)(None)


    def define_actions(self):
        @pzp.action.define(self, 'Minus', QtCore.Qt.Key.Key_Minus)
        def plus(self):
            delta = self.params['delta'].get_value()
            self._nudge(-delta)

        @pzp.action.define(self, 'Plus', QtCore.Qt.Key.Key_Plus)
        def plus(self):
            delta = self.params['delta'].get_value()
            self._nudge(delta)


    def _nudge(self, delta):
        params = pzp.parse.parse_params(self.params['params'].value, self.puzzle)
        for param in params:
            current = param.get_value()
            param.set_value(current + delta)

if __name__ == "__main__":
    app = pzp.QApp([])
    puzzle = pzp.Puzzle(app, "Nudge", debug=True)
    puzzle.add_piece("nudge", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()