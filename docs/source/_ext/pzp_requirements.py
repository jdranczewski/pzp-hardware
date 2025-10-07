from __future__ import annotations
from docutils import nodes

from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.util.typing import ExtensionMetadata
from sphinx.util import logging

import ast
import os

logger = logging.getLogger(__name__)

class _ParserFindPHT(ast.NodeVisitor):
    """
    Figure out what name was assinged to ``puzzlepiece.extras.hardware_tools``.
    """
    def __init__(self, tree, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.found = None
        self.visit(tree)

    def visit_ImportFrom(self, node):
        if node.module == "puzzlepiece.extras":
            for name in node.names:
                if name.name == "hardware_tools":
                    self.found = name.asname if hasattr(name, "asname") else name.name


class _ParserFindRequirements(ast.NodeVisitor):
    """
    Find calls to ``puzzlepiece.extras.hardware_tools.requirements`` and gather the
    requirement specifications given to the function.
    """
    def __init__(self, tree, pht, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.found = []
        self._pht_name = pht
        self.visit(tree)

    def visit_Call(self, node):
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == self._pht_name
            and node.func.attr == "requirements"
        ):
            try:
                self.found.append(ast.literal_eval(node.args[0]))
            except Exception as e:
                logger.warn(f"Exception while parsing for requirements: {e}")


class RequirementsDirective(SphinxDirective):
    """
    A directive that parses the given module for calls to
    ``puzzlepiece.extras.hardware_tools.requirements`` and
    produces a requirement list with pip commands and
    installation links.
    """
    required_arguments = 1

    def run(self) -> list[nodes.Node]:
        # Read the file correspodning to the module
        try:
            with open(f"../{self.arguments[0].replace('.', '/')}.py", "r") as f:
                tree = ast.parse(f.read())
        except FileNotFoundError:
            try:
                with open(f"../../{self.arguments[0].replace('.', '/')}.py", "r") as f:
                    tree = ast.parse(f.read())
            except FileNotFoundError:
                raise FileNotFoundError(os.path.abspath(f"{self.arguments[0].replace('.', '/')}.py"))

        # Find the name used for hardware_tools
        pht = _ParserFindPHT(tree).found
        if pht is not None:
            # If hardware_tools was found, find all calls to hardware_tools.requirements
            # and compile the arguments given
            all_args = {
                key: args[key] if isinstance(args, dict) else None
                for args in _ParserFindRequirements(tree, pht).found
                for key in args
            }
            # Make a list of requirements based on the gathered specifications
            if len(all_args):
                source = ""
                for arg in all_args:
                    source += f"* **{arg}**"
                    spec = all_args[arg]
                    if spec and "pip" in spec:
                        source += f" -- ``pip install {spec['pip']}``"
                    if spec and "url" in spec:
                        source += f" -- `Instructions <{spec['url']}>`__"
                    source += "\n"
                paragraph_node = nodes.paragraph(
                    text="This Piece has additional requirements. You will be asked to install "
                    "them at runtime, or you may choose to install them ahead of time."
                )
                return [paragraph_node, *self.parse_text_to_nodes(source)]

        # Fallback to a generic message
        paragraph_node = nodes.paragraph(text="This Piece does not have additional requirements.")
        return [paragraph_node]


def setup(app: Sphinx) -> ExtensionMetadata:
    app.add_directive('pzp_requirements', RequirementsDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }