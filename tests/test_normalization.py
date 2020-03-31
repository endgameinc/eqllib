"""Tests for normalization of data and queries."""
import unittest
import eql.tests
import eqllib


class TestNormalization(unittest.TestCase):
    """Tests for query and data normalization."""

    @classmethod
    def setUpClass(cls):
        cls.config = eqllib.Configuration.default()

    def assert_normalization_match(self, standard_query, converted, source="Microsoft Sysmon"):
        parsed_original = eql.parse_query(standard_query)
        parsed_converted = eql.parse_query(converted)

        normalizer = self.config.normalizers[source]
        converted = normalizer.normalize_ast(parsed_original)
        self.assertEqual(str(parsed_converted), str(converted))

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

    def test_normalize_sequence_with_pipe_fields_sysmon(self):
        original_query = r"""
        sequence
            [file where file_name == "tmp.bat"]
            [process where process_name == "cmd.exe"]
        | unique events[1].process_path
        """
        sysmon_query = r"""
        sequence
          [file where EventId in (11, 15) and TargetFilename == "*\\tmp.bat"]
          [process where EventId in (1, 5) and Image == "*\\cmd.exe"]
        | unique events[1].Image
        """
        self.assert_normalization_match(original_query, sysmon_query)

    def test_normalize_sequence_with_pipe_fields_endgame(self):
        original_query = r"""
        sequence
            [file where file_name == "tmp.bat"]
            [process where process_name == "cmd.exe"]
        | unique events[1].process_path
        """
        eg_query = r"""
        sequence
            [file where file_name == "tmp.bat"]
            [process where process_name == "cmd.exe"]
        | unique events[1].process_path
        """
        self.assert_normalization_match(original_query, eg_query, source="Endgame Platform")

    def test_eql_analytics(self):
        """Test that normal EQL queries are unmodified by normalization."""
        normalizer = eqllib.Normalizer({"strict": False,
                                        "domain": None,
                                        "events": {},
                                        "name": "Generic Normalizer",
                                        "timestamp": {
                                            "field": "timestamp",
                                            "format": "filetime"
                                        }})
        for query in eql.tests.TestEngine.get_example_queries():
            query = query["query"]
            normalized = normalizer.normalize_ast(query)
            self.assertEqual(query, normalized)

    def test_normalize_wildcard_basename(self):
        original = "registry where registry_value == '*foo*'"
        converted = "registry where key_path == '*\\\\*foo*'"
        self.assert_normalization_match(original, converted, source="Endgame Platform")

    def test_normalize_wildcard_dirname(self):
        original = "registry where registry_key == '*foo*'"
        converted = "registry where key_path == '*foo*\\\\*'"
        self.assert_normalization_match(original, converted, source="Endgame Platform")

    def test_normalize_wildcard_dirname_argument(self):
        original = "registry where true | unique registry_key"
        converted = "registry where true | unique key_path"
        self.assert_normalization_match(original, converted, source="Endgame Platform")

    def test_invalid_normalization(self):
        original = eql.parse_query("registry where concat(registry_key) == 'blah'")

        with self.assertRaises(eql.EqlCompileError):
            normalizer = self.config.normalizers["Endgame Platform"]
            normalizer.normalize_ast(original)
