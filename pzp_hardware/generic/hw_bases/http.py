# This file is a part of pzp-hardware, a library of laboratory hardware support Pieces
# for the puzzlepiece GUI & automation framework. Check out https://pzp-hardware.readthedocs.io
# Licensed under the Apache License 2.0 - https://github.com/jdranczewski/pzp-hardware/blob/main/LICENSE

"""
:module_title:`HTTP Piece`

A base Piece for implementing HTTP request communication
using the `puzzlepiece <https://puzzlepiece.readthedocs.io>`__ framework.

Defines an address param, ``self.rq`` is a reference to the
`requests <https://requests.readthedocs.io/en/latest/>`__
library, and ``self.check_response`` raises an exception if the response code
is not 200.

Example implementation::

    import puzzlepiece as pzp
    from pzp_hardware.generic.hw_bases import http

    class Piece(http.Base):
        default_address = "https://pzp-hardware.readthedocs.io" # change the default address

        def define_params(self):
            super().define_params()
            address = self["address"]

            @pzp.param.readout(self, 'online')
            def online():
                if self.puzzle.debug:
                    return True
                r = self.rq.get(f"{address.value}/en/latest/getting_started.html")
                self.check_response(r)
                return r.text

For a full Piece implemented using this base, see :class:`pzp_hardware.lightcon.pharos.Piece`.

Requirements
------------
.. pzp_requirements:: pzp_hardware.generic.hw_bases.http
"""

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht


class Base(pzp.Piece):
    """
    .. image:: ../images/pzp_hardware.generic.hw_bases.http.Base.png

    Base Piece implementing HTTP request communication.
    """
    #: Default value for the address param (set in your child class)
    default_address = "http://127.0.0.1:80"
    #: A reference to the requests library (available only when not in debug mode)
    rq = None

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
        """
        Raise an exception if the response code is not 200 (OK).

        :param r: HTTP request response
        """
        if not r.status_code == 200:
            raise Exception(f"Error ({r.status_code}) in HTTP request: {r.text}")

