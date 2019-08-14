"""Tests for all analytics in eqllib."""
from __future__ import print_function, unicode_literals
import os
import unittest

import eqllib.utils
import sys
import toml


class TestAnalytics(unittest.TestCase):
    """Tests for all analytics in eqllib."""

    analytics_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "eqllib", "analytics")

    @classmethod
    def setUpClass(cls):
        # Load all analytics, will raise an exception if any have invalid syntax
        cls.config = eqllib.Configuration.default()

    def test_schema(self):
        schema = self.config.domain_schemas["security"].eql_schema
        new_config = eqllib.Configuration(parent=self.config)

        with schema:
            paths = list(eqllib.utils.recursive_glob(self.analytics_path, "*.toml"))
            paths.sort()
            self.assertGreaterEqual(len(paths), 0)

            for path in paths:
                try:
                    new_config.add_analytic(toml.load(path))
                except Exception:
                    print("Error loading file: {:s}".format(path), file=sys.stderr)
                    raise
