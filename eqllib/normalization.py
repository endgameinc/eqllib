"""Normalization utilities for EQL compatibility."""
from __future__ import print_function
import datetime
import ntpath
from collections import OrderedDict
from eql.ast import *
from eql.parser import parse_expression, parse_query
from eql.engines import PythonEngine, Event
from eql.engines.base import BaseTranspiler, NodeMethods
from eql.schema import EVENT_TYPE_GENERIC

FILETIME_BASE = datetime.datetime(1601, 1, 1, 0, 0, 0)


class NormalizedEngine(PythonEngine):
    norm_functions = ('baseName', 'dirName', 'split', 'coalesce')

    def __init__(self, config=None):
        super(NormalizedEngine, self).__init__(config)

        self.add_custom_function('baseName', self._basename)
        self.add_custom_function('dirName', self._dirname)
        self.add_custom_function('split', self._split)
        self.add_custom_function('coalesce', self._coalesce)

    @staticmethod
    def _basename(path):
        if path is not None:
            return ntpath.basename(path)

    @staticmethod
    def _dirname(path):
        if path is not None:
            return ntpath.dirname(path)

    @staticmethod
    def _split(value, delim, pos):
        if value is not None:
            return value.split(delim)[pos]

    @staticmethod
    def _coalesce(*args):
        for arg in args:
            if arg is not None:
                return arg


class QueryNormalizer(BaseTranspiler):

    normalizers = NodeMethods()

    def __init__(self, normalizer):
        self.normalizer = normalizer  # type: Normalizer
        super(QueryNormalizer, self).__init__()

    @normalizers.add(EventQuery)
    def normalize_query(self, event_query, _):
        """Add filter_query to the converted condition."""
        event_type = event_query.event_type
        query = self.convert(event_query.query, event_type)

        if self.normalizer.config.get('filter_query') and event_type in self.normalizer.event_filters:
            query = self.normalizer.event_filters[event_type] & query
        return EventQuery(event_type, query)

    @normalizers.add(Field)
    def normalize_field(self, field, event_type):
        """Expand fields and enums to the target name or expression."""
        name = field.base
        enums = self.normalizer.event_enums.get(event_type, {}).get(name, {})
        path = field.path

        if len(path) == 1 and path[0] in enums:
            return enums[path[0]]

        # Also, replace a field using fields.mapping
        default = Null() if self.normalizer.strict else field
        global_converted = self.normalizer.field_mapping.get(name)
        event_converted = self.normalizer.event_field_mapping.get(event_type, {}).get(name)

        converted = event_converted or global_converted or default

        if isinstance(converted, Field) and field.path:
            converted.path = path
        return converted

    @normalizers.add(FunctionCall)
    def normalize_functions(self, func, event_type):
        if func.name == 'wildcard' and isinstance(func.arguments[0], Field):
            arguments = [self.convert(arg, event_type) for arg in func.arguments]
            base = arguments[0]
            if isinstance(base, FunctionCall) and base.name == 'coalesce':
                coalesce_args = base.arguments
                return Or([FunctionCall('wildcard', [c] + arguments[1:]) for c in coalesce_args])

    @normalizers.add(Comparison)
    def normalize_comparison(self, comparison, event_type):
        """Convert baseName(path) == 'a' -> path == '*\\a'."""
        if isinstance(comparison.left, FunctionCall) and comparison.left.name == 'coalesce' \
                and comparison.comparator == Comparison.EQ:
            return Or([self.convert(Comparison(a, Comparison.EQ, comparison.right), event_type)
                       for a in comparison.left.arguments])

        left = self.convert(comparison.left, event_type)
        right = self.convert(comparison.right, event_type)

        if isinstance(left, FunctionCall) and isinstance(right, String):
            func = left
            args = left.arguments

            if func.name == 'baseName' and isinstance(args[0], Field):
                func = FunctionCall('wildcard', [args[0], String("*\\" + right.value)])

            elif func.name == 'dirName' and isinstance(args[0], Field):
                func = FunctionCall('wildcard', [args[0], String(right.value + "\\*")])

            elif left.name == 'coalesce' and isinstance(args[0], Field):
                return Or([Comparison(a, Comparison.EQ, comparison.right) for a in args])
            else:
                return

            if comparison.comparator == Comparison.EQ:
                return func
            elif comparison.comparator == Comparison.NE:
                return ~ func

    @normalizers.add(InSet)
    def normalize_set(self, set_lookup, event_type):
        """Convert normalization functions for set lookups."""
        if set_lookup.is_literal():
            expression = self.convert(set_lookup.expression, event_type)
            if isinstance(expression, FunctionCall):
                func = expression
                args = func.arguments

                # Convert baseName(path) in ("a", "b", "c") -> wildcard(path, "*\\a", "*\\b", "*\\c")
                if func.name == 'baseName' and isinstance(args[0], Field) and \
                    all(isinstance(c, String) for c in set_lookup.container):
                    arguments = [args[0]]
                    arguments.extend(String("*\\" + c.value) for c in set_lookup.container)
                    return FunctionCall('wildcard', arguments)

                elif func.name == 'dirName' and isinstance(args[0], Field) and \
                    all(isinstance(c, String) for c in set_lookup.container):
                    arguments = [args[0]]
                    arguments.extend(String(c.value + "\\*") for c in set_lookup.container)
                    return FunctionCall('wildcard', arguments)

                elif func.name == 'coalesce':
                    args = [a for a in args if not (isinstance(a, Literal) and not a.value)]
                    return Or([InSet(a, set_lookup.container) for a in args])

        elif not set_lookup.is_dynamic():
            return self.convert(set_lookup.split_literals(), event_type)

    def convert(self, node, event_type=None, skip=False):
        cls = type(node)
        if cls in self.normalizers and not skip:
            converted = self.normalizers(self, node, event_type)
            if converted is not None:
                return converted.optimize()

        # Convert all the children and rebuild the current node
        if isinstance(node, EqlNode):
            children = [self.convert(v, event_type) for k, v in node.iter_slots()]
            return cls(*children).optimize()
        elif isinstance(node, (list, tuple)):
            return [self.convert(v, event_type) for v in node]
        elif isinstance(node, dict):
            return {self.convert(k, event_type): self.convert(v, event_type) for k, v in node.items()}
        else:
            return node


class Normalizer(AstWalker):
    """Normalize data and queries to a data source."""

    def __init__(self, config):
        """Create the normalizer."""
        self.config = config
        self.strict = config['strict']
        self.domain = config['domain']
        self.name = config['name']
        self.time_field = config['timestamp']['field']
        self.time_format = config['timestamp']['format']

        # Parse out the EQL field mapping
        self.field_mapping = {field: parse_expression(eql_text)
                              for field, eql_text in self.config['fields']['mapping'].items()}

        # Parse out the EQL event types
        self.event_filters = OrderedDict()
        self.event_enums = OrderedDict()
        self.event_field_mapping = OrderedDict()

        for event_name, event_config in self.config['events'].items():
            self.event_filters[event_name] = parse_expression(event_config['filter'])
            self.event_enums[event_name] = OrderedDict()
            self.event_field_mapping[event_name] = OrderedDict()

            # Create a lookup for all of the event fields
            for field_name, mapped_expression in event_config.get('mapping', {}).items():
                self.event_field_mapping[event_name][field_name] = parse_expression(mapped_expression)

            # Now loop over all of the enums, and build a mapping for EQL
            for field_name, enum_mapping in event_config.get('enum', {}).items():
                self.event_enums[event_name][field_name] = OrderedDict()

                for enum_option, enum_expr in enum_mapping.items():
                    self.event_enums[event_name][field_name][enum_option] = parse_expression(enum_expr)

        self._current_event_type = None
        self.data_normalizer = self.get_data_normalizer()
        self.normalize_ast = QueryNormalizer(self).convert

    def get_scoper(self):
        """Get a nested object for an EQL field."""
        scope = self.config['fields'].get('scope')
        if scope is None:
            return

        field = parse_expression(scope)  # type: Field
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

    def get_data_normalizer(self):
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
                raise ValueError("Unable to normalize. Double check that the input schema matches {}".format(self.name))

            ts = data[self.time_field]
            if self.time_format != 'filetime':
                ts = int((datetime.datetime.strptime(ts, self.time_format) - FILETIME_BASE).total_seconds() * 1e7)

            # Determine the event type first
            evt = Event(None, None, data)
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
            scoped_evt = Event(None, None, scoped)
            for normalized, converter in global_mapping.items():
                value = converter(scoped_evt)
                if value is not None:
                    output[normalized] = value

            for enum_name, enum_options in enum_converters.get(event_type, []):
                for enum_option, enum_checker in enum_options:
                    if enum_checker(evt):
                        output[enum_name] = enum_option
                        break

            for normalized, converter in event_mapping.get(event_type, {}).items():
                value = converter(scoped_evt)
                if value is not None:
                    output[normalized] = value

            output['event_type'] = event_type
            output['timestamp'] = ts

            converted_event = Event(event_type, ts, output)
            return converted_event

        return normalize_callback

