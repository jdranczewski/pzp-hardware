import puzzlepiece as pzp
from pyqtgraph.Qt import QtWidgets, QtCore
import requests

class Piece(pzp.Piece):
    url = 'http://127.0.0.1:8000/12030/v0/PublicAPI'
    def define_params(self):
        @pzp.param.spinbox(self, 'wl', 633)
        def set_wavelength(self, value):
            if self.puzzle.debug:
                return value
            
            r = requests.put(self.url + '/Optical/WavelengthControl/SetWavelength', json={'Interaction': '*', 'Wavelength': value})
            if not r.status_code == 200:
                raise Exception(f"Error setting wavelength: {r.text}")
            return value
        
        @set_wavelength.set_getter(self)
        def get_wavelength(self):
            if self.puzzle.debug:
                return 633
            
            r = requests.get(self.url + '/Optical/WavelengthControl/Output/Wavelength')
            if not r.status_code == 200:
                raise Exception(f"Error getting wavelength: {r.text}")
            return int(r.text)
        
        @pzp.param.checkbox(self, 'shutter', 0)
        def shutter(self, value):
            if self.puzzle.debug:
                return value
            
            endpoint = '/OpenShutter' if value else '/CloseShutter'
            
            r = requests.put(self.url + '/ShutterInterlock' + endpoint)
            if not r.status_code == 200:
                raise Exception(f"Error opening/closing shutter: {r.text}")
            
            return value
        
        @shutter.set_getter(self)
        def check_shutter(self):
            if self.puzzle.debug:
                return 1

            r = requests.get(self.url + '/ShutterInterlock/IsShutterOpen')
            if not r.status_code == 200:
                raise Exception(f"Error getting shutter state: {r.text}")
            
            return r.text == 'true'


    def define_actions(self):
        @pzp.action.define(self, 'Close shutter', QtCore.Qt.Key.Key_F5, visible=False)
        def panic(self):
            self.params['shutter'].set_value(0)
            
if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    puzzle = pzp.Puzzle(app, "Topas", debug=False)
    puzzle.add_piece("topas", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()