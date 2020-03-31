"""Normalization utilities for EQL compatibility."""
from __future__ import print_function, unicode_literals
import datetime
from collections import OrderedDict
import eql
from eql.ast import *  # noqa: F403
from eql.schema import EVENT_TYPE_GENERIC
from eql.walkers import DepthFirstWalker
from .functions import extra_functions

FILETIME_BASE = datetime.datetime(1601, 1, 1, 0, 0, 0)


class NormalizedEngine(eql.PythonEngine):
    """Add normalization functions to the engine."""

    def __init__(self, config=None):
        config = config or {}
        config.setdefault('functions', {}).update(extra_functions)
        super(NormalizedEngine, self).__init__(config)


class QueryNormalizer(DepthFirstWalker):
    """Class for converting queries from a domain to a specific source."""

    def __init__(self, normalizer):
        self.normalizer = normalizer
        DepthFirstWalker.__init__(self)

    def walk(self, node, *args, **kwargs):
        """Optimize nodes while walking."""
        node = super(QueryNormalizer, self).walk(node, *args, **kwargs)
        if isinstance(node, BaseNode):
            node = node.optimize()
        return node

    def _walk_event_query(self, event_query):
        """Add filter_query to the converted condition."""
        if self.normalizer.config.get('filter_query') and self.current_event_type in self.normalizer.event_filters:
            event_query.query = (self.normalizer.event_filters[self.current_event_type] & event_query.query).optimize()
        return event_query

    def _scope_to_event(self, node, event_index):  # type: (BaseNode, int) -> BaseNode
        """Scope all fields within an AST to events[event_index]."""
        if event_index is not None and len(self.output_event_types) > 1:
            node = self.copy_node(node)

            for nested_field in node:
                if isinstance(nested_field, Field) and event_index is not None:
                    subpath = [event_index] + nested_field.full_path
                    nested_field.base = "events"
                    nested_field.path = subpath

        return node

    def _walk_field(self, field):
        """Expand fields and enums to the target name or expression."""
        if self.in_pipes:
            event_index, event_field = field.query_multiple_events()
            event_type = self.output_event_types[event_index]
        else:
            event_index = None
            event_field = field
            event_type = self.current_event_type

        name = event_field.base
        enums = self.normalizer.event_enums.get(event_type, {}).get(name, {})
        path = event_field.path

        if len(path) == 1 and path[0] in enums:
            value = enums[path[0]]
            value = self._scope_to_event(value, event_index)
            return value

        # Also, replace a field using fields.mapping
        default = Null() if self.normalizer.strict else event_field
        global_converted = self.normalizer.field_mapping.get(name)
        event_converted = self.normalizer.event_field_mapping.get(event_type, {}).get(name)

        converted = event_converted or global_converted or default

        if isinstance(converted, Field) and path:
            converted.path = path

        converted = self._scope_to_event(converted, event_index)
        return converted

    def _wildcard_coalesce(self, coalesce_arguments, strings):
        """Convert coalesce(a,b,c) == "*wc*" to coalesce(a, "*wc*") or coalesce(b, "*wc") ..."""
        wildcards = [String(s) for s in strings]
        return Or([FunctionCall('wildcard', [c] + wildcards) for c in coalesce_arguments])

    def _wildcard_dirname(self, dirname_args, strings):
        r"""Convert directory == '*foo*' to path == '*foo*\\*'."""
        wildcards = [String(s.rstrip("*") + "*\\*") for s in strings]
        return FunctionCall('wildcard', dirname_args + wildcards)

    def _wildcard_basename(self, basename_args, strings):
        r"""Convert name == '*foo*' to path == '*\\*foo*'."""
        wildcards = [String("*\\*" + s.lstrip("*")) for s in strings]
        return FunctionCall('wildcard', basename_args + wildcards)

    def _walk_function_call(self, node):
        """Convert wildcards between multiple fields."""
        if node.name == 'wildcard' and len(node.arguments) >= 2:
            base = node.arguments[0]
            if isinstance(base, FunctionCall):
                method = getattr(self, "_wildcard_" + base.name.lower(), None)
                if callable(method):
                    strings = [n.value for n in node.arguments[1:]]
                    return method(base.arguments, strings)
        return node

    def _walk_comparison(self, comparison):
        r"""Convert baseName(path) == 'a' -> path == '*\\a'."""
        if isinstance(comparison.left, FunctionCall) and comparison.left.name == 'coalesce' \
                and comparison.comparator == Comparison.EQ:
            return Or([self._walk_comparison(Comparison(a, Comparison.EQ, comparison.right))
                       for a in comparison.left.arguments])

        if isinstance(comparison.left, FunctionCall) and isinstance(comparison.right, String) and \
                comparison.comparator in (Comparison.EQ, Comparison.NE):
            func = comparison.left
            args = comparison.left.arguments

            if func.name == 'baseName':
                if isinstance(args[0], Field):
                    func = FunctionCall('wildcard', [args[0], String("*\\" + comparison.right.value)])
                else:
                    return args[0]

            elif func.name == 'dirName':
                if isinstance(args[0], Field):
                    func = FunctionCall('wildcard', [args[0], String(comparison.right.value + "\\*")])
                else:
                    return args[0]

            elif func.name == 'coalesce' and isinstance(args[0], Field):
                return Or([Comparison(a, Comparison.EQ, comparison.right) for a in args])
            else:
                return comparison

            if comparison.comparator == Comparison.EQ:
                return func
            elif comparison.comparator == Comparison.NE:
                return ~ func
        return comparison

    def _walk_in_set(self, set_lookup):
        """Convert wildcard checks for `in` checks."""
        if set_lookup.is_literal():
            expression = set_lookup.expression
            if isinstance(expression, FunctionCall):
                func = expression
                args = func.arguments
                all_strings = all(isinstance(c, String) for c in set_lookup.container)

                # Convert baseName(path) in ("a", "b", "c") -> wildcard(path, "*\\a", "*\\b", "*\\c")
                if func.name == 'baseName' and isinstance(args[0], Field) and all_strings:
                    arguments = [args[0]]
                    arguments.extend(String("*\\" + c.value) for c in set_lookup.container)
                    return FunctionCall('wildcard', arguments)

                elif func.name == 'dirName' and isinstance(args[0], Field) and all_strings:
                    arguments = [args[0]]
                    arguments.extend(String(c.value + "\\*") for c in set_lookup.container)
                    return FunctionCall('wildcard', arguments)

                elif func.name == 'coalesce':
                    args = [a for a in args if not (isinstance(a, Literal) and not a.value)]
                    return Or([InSet(a, set_lookup.container) for a in args])
        elif not set_lookup.is_dynamic():
            return set_lookup.split_literals()

        return set_lookup

    def _walk_piped_query(self, node):
        """Catch queries to make sure that no normalization functions are present."""
        for tree in node:
            if isinstance(tree, FunctionCall) and tree.name in extra_functions:
                raise eql.EqlCompileError("Failed to normalize {}".format(tree))
        return node

    def _walk_pipe_command(self, node):
        """Replace file-based arguments to functions with the full path."""
        for i, argument in enumerate(node.arguments):
            if isinstance(argument, FunctionCall) and argument.name in ("baseName", "dirName"):
                node.arguments[i] = argument.arguments[0]

        return node


class Normalizer(object):
    """Normalize data and queries to a data source."""

    def __init__(self, config):
        """Create the normalizer."""
        object.__init__(self)
        self.config = config
        self.strict = config['strict']
        self.domain = config['domain']
        self.name = config['name']
        self.time_field = config['timestamp']['field']
        self.time_format = config['timestamp']['format']

        # Parse out the EQL field mapping
        with eql.ParserConfig(custom_functions=extra_functions.values()):
            self.field_mapping = {field: eql.parse_expression(eql_text)
                                  for field, eql_text in self.config.get('fields', {}).get('mapping', {}).items()}

            # Parse out the EQL event types
            self.event_filters = OrderedDict()
            self.event_enums = OrderedDict()
            self.event_field_mapping = OrderedDict()

            for event_name, event_config in self.config.get('events', {}).items():
                self.event_filters[event_name] = eql.parse_expression(event_config['filter'])
                self.event_enums[event_name] = OrderedDict()
                self.event_field_mapping[event_name] = OrderedDict()

                # Create a lookup for all of the event fields
                for field_name, mapped_expression in event_config.get('mapping', {}).items():
                    self.event_field_mapping[event_name][field_name] = eql.parse_expression(mapped_expression)

                # Now loop over all of the enums, and build a mapping for EQL
                for field_name, enum_mapping in event_config.get('enum', {}).items():
                    self.event_enums[event_name][field_name] = OrderedDict()

                    for enum_option, enum_expr in enum_mapping.items():
                        self.event_enums[event_name][field_name][enum_option] = eql.parse_expression(enum_expr)

        self._current_event_type = None
        self.data_normalizer = self.get_data_normalizer()
        self.query_normalizer = QueryNormalizer(self)

    def normalize_ast(self, node):
        """Convert an AST from a domain to a source."""
        return QueryNormalizer(self).walk(node)

    def get_scoper(self):
        """Get a nested object for an EQL field."""
        scope = self.config.get('fields', {}).get('scope')
        if scope is None:
            return

        field = eql.parse_expression(scope)  # type: Field
        keys = [field.base] + field.path

        def walk_path(value):
            for key in keys:
                if value is None:
                    break
                elif isinstance(value, dict):
                    value = value.get(key)
                elif key < len(value):
                    value = value[key]
                else:
                    value = None

            return value or {}

        return walk_path

    def get_data_normalizer(self):  # noqa: C901
        """Get a function that converts dictionaries to the normalized field names."""
        engine = NormalizedEngine()

        event_updates = []
        enum_converters = OrderedDict()

        def convert_eql(e, scoped=True):
            """Convert an EQL expression into a callback function."""
            return engine.convert(e, scoped=scoped)

        # Create callback functions for mapping the enums to the expanded version
        for event_name, enum_lookup in self.event_enums.items():
            event_enums = []
            enum_converters[event_name] = event_enums

            for enum_name, enum_mapping in enum_lookup.items():
                current_mapping = [(option, convert_eql(expr)) for option, expr in enum_mapping.items()]
                event_enums.append((enum_name, current_mapping))

        # Get a callback function for checking the event type
        for event_name, filter_expression in self.event_filters.items():
            event_updates.append((event_name, convert_eql(filter_expression)))

        scoper = self.get_scoper()

        global_mapping = {}
        event_mapping = {}

        # Now add a converter for all the fields
        for field, mapped_field in self.field_mapping.items():
            global_mapping[field] = engine.convert(mapped_field, scoped=True)

        # Convert event-specific fields
        for event_type, field_mapping in self.event_field_mapping.items():
            event_mapping[event_type] = OrderedDict()

            for field, mapped_field in field_mapping.items():
                event_mapping[event_type][field] = engine.convert(mapped_field, scoped=True)

        def normalize_callback(data):
            """Normalize an event to the common schema."""
            scoped = scoper(data) if scoper else data
            output = {} if self.strict else scoped.copy()

            if self.time_field not in data:
                raise ValueError("Unable to normalize. Check that the input schema matches {}".format(self.name))

            ts = data[self.time_field]
            if self.time_format != 'filetime':
                ts = int((datetime.datetime.strptime(ts, self.time_format) - FILETIME_BASE).total_seconds() * 1e7)

            # Determine the event type first
            evt = eql.Event(None, None, data)
            if data.get('event_type') in event_updates:
                event_type = data['event_type']
            else:
                for name, check_type in event_updates:
                    if check_type(evt):
                        event_type = name
                        break
                else:
                    event_type = EVENT_TYPE_GENERIC

            # Convert the global fields
            scoped_evt = eql.Event(None, None, scoped)
            for normalized, converter in global_mapping.items():
                value = converter(scoped_evt)
                if value is not None:
                    output[normalized] = value

            # check the enums, but not against the scoped fields
            for enum_name, enum_options in enum_converters.get(event_type, []):
                for enum_option, enum_checker in enum_options:
                    if enum_checker(evt):
                        output[enum_name] = enum_option
                        break

            # check the mappings against the scoped fields
            for normalized, converter in event_mapping.get(event_type, {}).items():
                value = converter(scoped_evt)
                if value is not None:
                    output[normalized] = value

            output['event_type'] = event_type
            output['timestamp'] = ts

            converted_event = eql.Event(event_type, ts, output)
            return converted_event

        return normalize_callback
