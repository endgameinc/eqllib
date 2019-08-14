"""Tests for normalization of data and queries."""
import unittest
import eql
import eqllib


class TestNormalization(unittest.TestCase):
    """Tests for query and data normalization."""

    @classmethod
    def setUpClass(cls):
        cls.config = eqllib.Configuration.default()
        cls.sysmon_normalizer = cls.config.normalizers["Microsoft Sysmon"]

    def assert_normalization_match(self, standard_query, sysmon_query):
        parsed_original = eql.parse_query(standard_query)
        parsed_sysmon = eql.parse_query(sysmon_query)

        converted = self.sysmon_normalizer.normalize_ast(parsed_original)
        self.assertEqual(parsed_sysmon, converted)

    def test_normalize_kv(self):
        original_query = r"process where process_path == 'C:\\Windows\\System32\\cmd.exe'"
        sysmon_query = r"process where EventId in (1, 5) and Image == 'C:\\Windows\\System32\\cmd.exe'"

        self.assert_normalization_match(original_query, sysmon_query)

    def test_normalize_wildcards(self):
        original_query = r"process where process_name == 'cmd.exe'"
        sysmon_query = r"process where EventId in (1, 5) and Image == '*\\cmd.exe'"
        self.assert_normalization_match(original_query, sysmon_query)

    def test_normalize_in(self):
        original_query = r"process where process_name in ('cmd.exe', 'net.exe', 'whoami.exe')"
        sysmon_query = r"process where EventId in (1, 5) and " + \
                       r"wildcard(Image, '*\\cmd.exe', '*\\net.exe', '*\\whoami.exe')"
        self.assert_normalization_match(original_query, sysmon_query)

    def test_normalize_missing_field(self):
        original_query = r"process where missing_field == 'abc.exe'"
        sysmon_query = r"process where false"
        self.assert_normalization_match(original_query, sysmon_query)
