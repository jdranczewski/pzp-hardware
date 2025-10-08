Puzzlepiece Hardware (pzp-hardware)
===================================

.. image:: docs/source/pzp-hardware.svg

**Laboratory hardware support Pieces for the puzzlepiece GUI & automation framework.**

Puzzlepiece is a GUI-forward Python framework for automating experimental setups and rapid
user interface creation. You can find its documentation and tutorial at
https://puzzlepiece.readthedocs.io. This library provides "Pieces" (GUI components) for
commonly used laboratory hardware, so that you can easily assemble your automation
application (a "Puzzle") out of them.

**This package is currently a work in progress.** The Pieces shown in the documentation
have been fully ported to the new standard, but they may require a version of puzzlepiece
that has not been released yet.

* Documentation: https://pzp-hardware.readthedocs.io
* Repository: https://github.com/jdranczewski/pzp-hardware

Installation
------------
You can install this package from pip::

    pip install pzp-hardware

If you would like to develop your own Pieces and contribute changes to this library, you may
choose to clone the repository instead, and install a local, editable copy::

    git clone https://github.com/jdranczewski/pzp-hardware.git
    cd pzp-hardware
    pip install -e .

Once installed, you can use the Pieces provided like you would any other Piece in puzzlepiece::

    import puzzlepiece as pzp
    from pzp_hardware.thorlabs import camera

    app = pzp.QApp()
    # Set debug to False to interact with hardware, or you can explore and test in debug mode,
    # which is the default, and doesn't require the hardware APIs to be present
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("camera", camera.Piece, row=0, col=0)
    puzzle.show()
    app.exec()

Check out `Getting started <https://pzp-hardware.readthedocs.io/en/latest/getting_started.html>`__ for more details!

Structure
---------
The library consists of a number of manufacturer folders, with each containing Python files that each interface with
a specific hardware/software provided by that manufacturer. The library contains all files on installation, but they
need to be specifically imported, so that you never have to import the full library, just the parts you require::

    from pzp_hardware.thorlabs import camera, apt_stage
    from pzp_hardware.vialux import dmd

See `Modules <https://pzp-hardware.readthedocs.io/en/latest/modules.html>`__ for all currently supported hardware.

Development and contributing
----------------------------
Puzzlepiece provides a unified API for all of your devices, so the best laboratory automation experience is
if you have Pieces for all of your hardware. If your hardware is not supported by ``pzp-hardware``, you can
create a Piece yourself -- puzzlepiece aims to make that as easy as possible! You can create a fork
of the `main repository <https://github.com/jdranczewski/pzp-hardware>`__, and we welcome
`pull requests <https://github.com/jdranczewski/pzp-hardware/pulls>`__ adding support for new hardware.

**Your Piece should broadly follow the same conventions as the ones currently in the repository.** For example,
image-based Pieces like cameras, DMDs, or SLMs should have an ``image`` param, allowing you to use the standard
preview layouts provided in
``pzp_hardware.generic.mixins.image_preview``.
Your Piece should work reliably
in debug mode to allow testing. You can use
`puzzlepiece.extras.hardware_tools <https://puzzlepiece.readthedocs.io/en/stable/puzzlepiece.extras.hardware_tools.html>`__
to make integration with manufacturer APIs and DLLs easier, and in particular you should indicate requirements
specific to your Piece with
`puzzlepiece.extras.hardware_tools.requirements <https://puzzlepiece.readthedocs.io/en/stable/puzzlepiece.extras.hardware_tools.html#puzzlepiece.extras.hardware_tools.requirements>`__
(these are automatically parsed to appear in this documentation).

**Documentation is key to your users being able to find, install, and use the Piece.** Pull requests that don't
include at least basic documentation for the new Piece will not be merged. Documentation should be included in
your Piece's Python file, mostly as a docstring at the top, with docstrings in the Pieces that you want exposed
in the docs. It's also recommended to include a screenshot of your Piece, but an explicit list of params is not
required, as the user can inspect this in debug mode. **Check out the template on GitHub.**