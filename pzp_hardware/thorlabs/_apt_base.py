# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

r"""
Installation
------------
* Install the APT Software from https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=9019
* Locate the ``APT Server`` folder in the APT installation directory
  (usually ``C:\Program Files\Thorlabs\APT\APT Server``) and copy its path.
* When running the Piece for the first time, you will be asked for the DLL directory -
  provide the one you copied above.

Requirements
------------
.. pzp_requirements:: pzp_hardware.thorlabs._apt_base

Troubleshooting
---------------
If APT or your application crashes while connected to a stage, subsequent attempts to load APT
will likely crash. To fix this, you can:

* Restart the affected stages
* Restart the affected computer
* Use the Kinesis software to perform a quick fix (the fastest method, but requires additional software):

  - Install Kinesis from https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=10285
  - Close any instance of APT
  - Launch Kinesis and wait for it to fully load and detect the stages
  - Close Kinesis
  - APT should work normally now!

Note that there can only be one isntance of the APT server running at any time. If you are connected
to a stage in this Piece and would like to use APT in another application, disconnect from the stage in
the Piece. If you are not connected to a stage, you can still release APT from the puzzlepiece process
by using this Piece's Cleanup action (available from the Tree view, button at the bottom of the Puzzle or F1).
"""

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht


class APTBase(pzp.Piece):
    """
    Base for Pieces that have to interface with ThorLabs APT.
    """
    def define_params(self):
        @pzp.param.dropdown(self, 'serial', "", visible=True)
        def get_motors():
            if not self.puzzle.debug:
                return [x[1] for x in self.puzzle.globals['apt'].list_available_devices()]

        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                return 1
            self._ensure_apt()
            try:
                serial = int(self.params['serial'].get_value())
            except ValueError:
                raise Exception("Motor serial number is not a valid integer")
            self.motor = self.puzzle.globals['apt'].Motor(serial)
            return 1

        @pzp.param.disconnect(self)
        def disconnect():
            if self.puzzle.debug:
                return 0
            if hasattr(self, 'motor'):
                del self.motor
            self._apt_cleanup()
            return 0

        # Disconnecting APT in one Piece results in all Pieces disconnecting
        # (a limitation of APT)
        def global_deleted(name):
            if name == "apt":
                self["connected"].set_value(False)
        self.puzzle.globals.deleted.connect(global_deleted)

    def define_actions(self):
        @pzp.action.define(self, "Cleanup", visible=False)
        def cleanup():
            self._apt_cleanup()

    def _ensure_apt(self):
        if "apt" not in self.puzzle.globals:
            pht.add_dll_directory(pht.config(
                "APT_dll_directory",
                default=r"C:\Program Files\Thorlabs\APT\APT Server",
                validator=pht.validator_path_exists
            ))
            pht.requirements({
                "thorlabs_apt": {
                    "pip": "thorlabs-apt"
                }
            })
            import thorlabs_apt
            if thorlabs_apt.core._lib is None:
                thorlabs_apt.core._lib = thorlabs_apt.core._load_library()
            self.puzzle.globals['apt'] = thorlabs_apt

    def _apt_cleanup(self):
        if 'apt' in self.puzzle.globals:
            self.puzzle.globals['apt'].core._cleanup()
            self.puzzle.globals['apt'].core._lib = None
            del self.puzzle.globals['apt']

    @pzp.piece.ensurer
    def _ensure(self):
        if self.puzzle.debug:
            return
        if 'apt' in self.puzzle.globals and hasattr(self, 'motor'):
            return
        raise Exception('Motor not connected')

    def setup(self):
        self._ensure_apt()

    def handle_close(self, event):
        self._apt_cleanup()
        super().handle_close(event)
