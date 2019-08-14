"""Utility functions for loading."""
import fnmatch
import os


def recursive_glob(root, pattern):
    if root is None:
        return

    if os.path.isfile(root) and fnmatch.fnmatch(root, pattern):
        yield root
        return

    for base, dirs, files in os.walk(root):
        matches = fnmatch.filter(files, pattern)
        for filename in matches:
            yield os.path.join(base, filename)
