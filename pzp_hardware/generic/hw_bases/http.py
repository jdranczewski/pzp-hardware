# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht


class Base(pzp.Piece):
    default_address = "http://127.0.0.1:80"

    def define_params(self):
        pzp.param.text(self, "address", self.default_address)(None)

    def setup(self):
        pht.requirements({
            "requests": {
                "pip": "requests",
                "url": "https://requests.readthedocs.io/en/latest/user/install/"
            }
        })
        import requests
        #: the Python ``requests`` library
        self.rq = requests

    def check_response(self, r):
        if not r.status_code == 200:
            raise Exception(f"Error in HTTP request: {r.text}")

