"""Normalization functions."""
import ntpath

from eql.functions import FunctionSignature
from eql.types import TypeHint

extra_functions = {}


def add_function(f):
    """Register a normalization function."""
    extra_functions[f.name] = f
    return f


@add_function
class BaseName(FunctionSignature):
    """Get the base name of an image."""

    name = "baseName"
    argument_types = [TypeHint.String]

    @classmethod
    def run(cls, path):
        if path is not None:
            return ntpath.basename(path)


@add_function
class DirName(FunctionSignature):
    """Get the directory name from a path."""

    name = "dirName"
    argument_types = [TypeHint.String]
    return_value = TypeHint.String

    @classmethod
    def run(cls, path):
        if path is not None:
            return ntpath.dirname(path)


@add_function
class Split(FunctionSignature):
    """Get the directory name from a path."""

    name = "split"
    argument_types = [TypeHint.String, TypeHint.String, TypeHint.Numeric]
    return_value = TypeHint.String

    @classmethod
    def run(cls, value, delim, pos):
        """Split a string by a delimiter."""
        if value is not None:
            pieces = value.split(delim)
            if pos < len(pieces):
                return pieces[pos]


@add_function
class Coalesce(FunctionSignature):
    """Get the directory name from a path."""

    name = "coalesce"
    additional_types = TypeHint.Unknown
    return_value = TypeHint.Unknown

    @classmethod
    def run(cls, *args):
        """Split a string by a delimiter."""
        for arg in args:
            if arg is not None:
                return arg
