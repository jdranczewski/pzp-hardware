.. _getting-started:

Getting started
===============
This is a more detailed description of how you can work with ``pzp-hardware`` to implement your experiment automation. For a high-level overview, you can read :doc:`the home page <index>` first!

Puzzlepiece is a framework where a Puzzle (the top level window) is constructed out of Pieces (the modular GUI components corresponding to a piece of hardware or a task).
To use ``pzp-hardware`` you should be somewhat familiar with ``puzzlepiece``:

* Have a look at the high-level overview at https://puzzlepiece.readthedocs.io.
* Go through the ``puzzlepiece`` tutorial at https://puzzlepiece.readthedocs.io/en/stable/tutorial.html.
* Follow https://puzzlepiece.readthedocs.io/en/stable/python_lab.html if you're setting up a new Python environment.

Installation
------------
You can install this package from pip directly into your Python environment (see https://puzzlepiece.readthedocs.io/en/stable/python_lab.html for more details on Python environments)::

    pip install pzp-hardware

Note that this will not let you edit or add to the Pieces within the library -- which is fine in most cases! You can inherit from the Piece classes to add functionality, and develop your own Pieces independently.

If you would like to contribute changes to this library, you may
choose to clone the repository instead, and install a local, editable copy::

    git clone https://github.com/jdranczewski/pzp-hardware.git
    cd pzp-hardware
    pip install -e .

You should first create a fork on GitHub so you can track your own changes, and use your fork's URL in the command above.
This fork can be specific to your research group for example, with all the lab computers pulling from it.
See https://github.com/git-guides for git fundamentals, and https://puzzlepiece.readthedocs.io/en/stable/python_lab.html for how to set up git on a lab PC.

Specific hardware Pieces may have additional requirements!
They are listed in the documentation page for the Piece on this site, and you will be prompted to act on these when you first launch a given Piece.
The documentation also has detailed installation instructions for each Piece, as manufacturer APIs may have to be installed separately.
You can find a list of these documentation pages in :doc:`auto/pzp_hardware`.

Usage in Python files
---------------------
To use the Pieces in a Python script, you first need to import them, set up a Qt Application which will manage the GUI, assemble and show your Puzzle, and finally execute the Qt Application::

    import puzzlepiece as pzp
    from puzzlepiece.extras import hardware_tools as pht
    from pzp_hardware.thorlabs import camera, apt_stage

    # Create a Qt app, the backend that will run our GUI
    app = pzp.QApp()

    # Create a Puzzle, the main window of the application.
    with pzp.Puzzle(name="Test", debug=pht.debug_prompt()) as puzzle:
        puzzle.add_piece("camera", camera.Piece, row=0, column=0)
        puzzle.add_piece("stage", apt_stage.Piece, row=0, column=1, param_defaults={
            "serial": 1234 # you can provide default values for the params during setup
        })

    # Display the Puzzle and execute the Qt app
    puzzle.show()
    app.exec()

We use ``pht.debug_prompt()`` to prompt the user whether they want to launch in debug mode, which doesn't talk to hardware.
This is useful during development, and to test your measurement code, as it doesn't talk to any hardware and can be run on computers without the manufacturer APIs installed.

We use the Puzzle as a context manager in this example, so that if any of the Pieces raise exceptions while being added, the Puzzle can clean up other APIs and exit cleanly. This is not required, and the code below is also valid::

    # Note that ``debug=True`` is the default, so if you don't explicitly
    # disable debug mode, the Puzzle will not talk to any of your hardware.
    puzzle = pzp.Puzzle(debug=False)
    puzzle.add_piece("camera", camera.Piece, 0, 0)
    puzzle.add_piece("stage", apt_stage.Piece, 0, 1)
    puzzle.show()

But now if ``apt_stage`` raises an exception, the program will exit without cleaning up the ``camera`` API connection.

After saving the above as a Python file, you can directly launch it to get your GUI.
See https://puzzlepiece.readthedocs.io/en/stable/python_lab.html for more on setting up Python, and how you can set Python files to open using a virtual environment interpreter by default.

Usage in Jupyter Notebooks
--------------------------
You can construct your Puzzle from a Jupyter Notebook too, which will let you have an interactive GUI *and* an interactive Python shell that can talk to the GUI and your experimental equipment.
This is how I usually prefer to use puzzlepiece.

The code is similar to the one above, with the main difference being that we don't have to construct and run a Qt Application, and use the ``%gui qt`` "magic" instead::

    # Enable the IPython GUI integration
    %gui qt

    import puzzlepiece as pzp
    from puzzlepiece.extras import hardware_tools as pht
    from pzp_hardware.thorlabs import camera, apt_stage

    # Create a Puzzle, the main window of the application.
    with pzp.Puzzle(name="Test", debug=pht.debug_prompt()) as puzzle:
        puzzle.add_piece("camera", camera.Piece, row=0, column=0)
        puzzle.add_piece("stage", apt_stage.Piece, row=0, column=1, param_defaults={
            "serial": 1234 # you can provide default values for the params during setup
        })

    # Display the Puzzle
    puzzle.show()

We can now interact with the puzzle from other Notebook cells, for example::

    puzzle["camera:image"].get_value()

You can run ``from puzzlepiece.extras import ipython_shims`` to get access to various quality-of-life magics, see https://puzzlepiece.readthedocs.io/en/stable/puzzlepiece.extras.ipython_shims.html for details.

Conducting your measurement
---------------------------
The puzzlepiece tutorial at https://puzzlepiece.readthedocs.io/en/stable/tutorial.html is an interactive guide on how you can construct your measurement code, so it's the best place to start. In summary:

You can conduct your measurement in two main ways: from the GUI as a custom Piece, or from a Jupyter Notebook as a cell containing the measurement code.
In both cases your code will be setting or getting params, and calling actions, to interact with the puzzlepiece API.

Again, check out https://puzzlepiece.readthedocs.io/en/stable/tutorial.html for examples of both approaches.

Your own hardware Pieces
------------------------
If your hardware is not currently supported by ``pzp-hardware``, check out :doc:`writing_pieces` for details of how to create a Piece for it.