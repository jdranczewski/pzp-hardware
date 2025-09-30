import puzzlepiece as pzp

#TODO: changes needed to the way disconnecting is currently handled

class Piece(pzp.Piece):
    def __init__(self, puzzle, custom_horizontal=False, *args, **kwargs):
        self._debug_pos = 0
        super().__init__(puzzle, custom_horizontal, *args, **kwargs)

    def define_params(self):
        @pzp.param.dropdown(self, 'serial', 27258755, visible=True)
        def get_motors(self):
            if not self.puzzle.debug:
                return [x[1] for x in self.puzzle.globals['apt'].list_available_devices()]

        pzp.param.base_param(self, 'connected', 0)(None)

        @pzp.param.spinbox(self, 'pos', 0.)
        @self._ensure
        def move_to(self, value):
            if self.puzzle.debug:
                self._debug_pos = value
                return value
            self.motor.move_to(value, blocking=True)

        @move_to.set_getter(self)
        @self._ensure
        def get_position(self):
            if self.puzzle.debug:
                return self._debug_pos
            return self.motor.position
        
    def define_actions(self):
        @pzp.action.define(self, 'Init')
        def init(self):
            if not self.puzzle.debug and not self._ensure(capture_exception=True):
                self._ensure_apt()
                self.motor = self.puzzle.globals['apt'].Motor(int(self.params['serial'].get_value()))
            self.params['connected'].set_value(1)

        @pzp.action.define(self, 'Cleanup')
        def cleanup(self):
            if not self.puzzle.debug:
                self._apt_cleanup()
                if hasattr(self, 'motor'):
                    del self.motor
            self.params['connected'].set_value(0)

        @pzp.action.define(self, 'Home')
        @self._ensure
        def home(self):
            if self.puzzle.debug:
                self.param['pos'].set_value(0)
            self.motor.move_home(blocking=True)
            self.params['pos'].get_value()

        @pzp.action.define(self, 'Identify')
        @self._ensure
        def identify(self):
            if self.puzzle.debug:
                return
            self.motor.identify()

    def _apt_import(self):
        import thorlabs_apt
        import ctypes

        if thorlabs_apt.core.cleaned:
            thorlabs_apt.core._lib = thorlabs_apt.core._load_library()

        self._ctypes = ctypes
        self.puzzle.globals['apt'] = thorlabs_apt
    
    def _ensure_apt(self):
        if not 'apt' in self.puzzle.globals:
            self._apt_import()

    def _apt_cleanup(self):
        if 'apt' in self.puzzle.globals:
            self.puzzle.globals['apt'].core._cleanup()
            del self.puzzle.globals['apt']

    @pzp.piece.ensurer
    def _ensure(self):
        if self.puzzle.debug:
            return
        if 'apt' in self.puzzle.globals and hasattr(self, 'motor'):
            return
        self.params['connected'].set_value(0)
        raise Exception('Motor not connected')
    
    def setup(self):
        self._ensure_apt()
        
    def handle_close(self, event):
        if not self.puzzle.debug and self._ensure(capture_exception=True):
            self._apt_cleanup()
        super().handle_close(event)

            
if __name__ == "__main__":
    app = pzp.QApp([])
    puzzle = pzp.Puzzle(app, "ND stage", debug=False)
    puzzle.add_piece("nd_stage", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()