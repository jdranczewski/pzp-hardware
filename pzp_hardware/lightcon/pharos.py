import puzzlepiece as pzp
from pyqtgraph.Qt import QtWidgets
import requests

class Piece(pzp.Piece):
    url = "http://127.0.0.1:20022/v0"
    def define_params(self):
        @pzp.param.readout(self, 'full_state', visible=False)
        def basic(self):
            if self.puzzle.debug:
                return ''
            
            r = requests.get(f'{self.url}/Basic')
            if not r.status_code == 200:
                raise Exception(f"Error getting state: {r.text}")
            state = str(r.json()).replace(',', ',\n')
            return state
        
        @pzp.param.readout(self, 'state', visible=True)
        def basic(self):
            if self.puzzle.debug:
                return ''
            
            r = requests.get(f'{self.url}/Basic')
            if not r.status_code == 200:
                raise Exception(f"Error getting state: {r.text}")
            return r.json()['GeneralStatus']

        @pzp.param.checkbox(self, "output", 0)
        def output(self, value):
            if self.puzzle.debug:
                return value
            
            if value:
                r = requests.post(f'{self.url}/Basic/EnableOutput')
            else:
                r = requests.post(f'{self.url}/Basic/CloseOutput')
            if not r.status_code == 200:
                raise Exception(f"Error setting state: {r.text}")
            return value
        
        @output.set_getter(self)
        def output(self):
            if self.puzzle.debug:
                return 0
            
            r = requests.get(f'{self.url}/Basic/IsOutputEnabled')
            if not r.status_code == 200:
                raise Exception(f"Error getting state: {r.text}")
            return r.text == 'true'
        
        @pzp.param.spinbox(self, "divider", 1, v_min=1)
        def divider(self, value):
            if self.puzzle.debug:
                return value
            
            r = requests.put(f'{self.url}/Basic/TargetPpDivider', str(value))
            if not r.status_code == 200:
                raise Exception(f"Error setting divider: {r.text}")
            return value
        
        @divider.set_getter(self)
        def divider(self):
            if self.puzzle.debug:
                return 1
            
            r = requests.get(f'{self.url}/Basic/TargetPpDivider')
            if not r.status_code == 200:
                raise Exception(f"Error getting divider: {r.text}")
            return int(r.text)

    def define_actions(self):
        @pzp.action.define(self, 'State')
        def state(self):
            state = self.params['full_state'].get_value()

            box = QtWidgets.QMessageBox()
            box.setText(state)
            box.exec()
        
        @pzp.action.define(self, 'Standby')
        def shutdown(self, confirm=True):
            if confirm:
                mb = QtWidgets.QMessageBox
                if mb.question(self.puzzle, 'Shutdown', 'Do you want to go to standby?') != mb.StandardButton.Yes:
                    return

            if self.puzzle.debug:
                return
            
            r = requests.post(f'{self.url}/Basic/GoToStandby')
            if not r.status_code == 200:
                raise Exception(f"Error shutting down")
            
if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    puzzle = pzp.Puzzle(app, "Pharos", debug=True)
    puzzle.add_piece("pharos", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()