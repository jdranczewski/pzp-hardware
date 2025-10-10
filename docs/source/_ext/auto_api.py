from __future__ import annotations
from docutils import nodes

from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.util.typing import ExtensionMetadata
from sphinx.util import logging

import os
import re


logger = logging.getLogger(__name__)


def _capture_heading(fname):
    try:
        with open(fname) as f:
            head = ""
            for i, line in enumerate(f):
                head += line
                if i > 19:
                    break
            result = re.search(r".. module_title:: (.+)", head)
            if result is None:
                return None
            return result.group(1)
    except FileNotFoundError:
        return None


def _make_fname(path: str) -> str:
    components = os.path.normpath(path).split(os.path.sep)
    last_index = len(components) - 1 - components[::-1].index("pzp_hardware")
    components = components[last_index:]
    last_component = components[-1].split(".")
    if len(last_component) > 1:
        del last_component[-1]
    components[-1] = ".".join(last_component)
    components.append("rst")
    return ".".join(components)

def _process_file(folder: str, file: str, destination: str) -> str:
    heading = _capture_heading(os.path.join(folder, file))
    if heading is None:
        return None

    fname = _make_fname(os.path.join(folder, file))
    with open(os.path.join(destination, fname), "w") as f:
        f.write(f"""{heading}
{"=" * len(heading)}

.. automodule:: {fname.replace(".rst", "")}
   :members:
   :show-inheritance:
""")
    return fname

def _process_folder(folder: str, destination: str) -> None:
    heading = _capture_heading(os.path.join(folder, "__init__.py"))
    if heading is None:
        return None

    ld = os.listdir(folder)
    files = sorted([x for x in ld if os.path.isfile(os.path.join(folder, x))])
    dirs = sorted([x for x in ld if x not in files and x != "__pycache__"])
    files = [file for file in files if file.split(".")[-1] == "py" and file[0] != "_"]

    # Make a doc file for this folder
    folder_fname = _make_fname(folder)

    text = (f"""{heading}
{"=" * len(heading)}

.. automodule:: {folder_fname.replace(".rst", "")}

.. toctree::
   :maxdepth: 2

""")

    # Handle files
    for file in files:
        fname = _process_file(folder, file, destination)
        if fname:
            text += f"   {fname.replace('.rst', '')}\n"

    # Handle directories
    for dir in dirs:
        fname = _process_folder(os.path.join(folder, dir), destination)
        if fname:
            text += f"   {fname.replace('.rst', '')}\n"

    with open(os.path.join(destination, folder_fname), "w") as f:
        f.write(text)

    return folder_fname

def generate_docs(app: Sphinx) -> None:
    pass
    # Find pzp_hardware
    # Traverse it and make the files if needed
    src = "../../pzp_hardware" if os.path.exists("../../pzp_hardware") else "../pzp_hardware"
    destination = "./source" if os.path.exists("./source") else "../source"
    destination = os.path.join(destination, "auto")
    # destination = os.path.join(destination, "auto")
    if not os.path.exists(destination):
        os.mkdir(destination)
    _process_folder(src, destination)

class ModuleTitleDirective(SphinxDirective):
    """
    A directive that parses the given module for calls to
    ``puzzlepiece.extras.hardware_tools.requirements`` and
    produces a requirement list with pip commands and
    installation links.
    """
    required_arguments = 1

    def run(self) -> list[nodes.Node]:
        return []

def setup(app: Sphinx) -> ExtensionMetadata:
    app.connect('builder-inited', generate_docs)
    app.add_directive('module_title', ModuleTitleDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }