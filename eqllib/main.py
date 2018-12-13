from __future__ import print_function

import argparse
import json
import sys

import toml
from eql import parse_query, EqlError
from eql.schema import EVENT_TYPE_GENERIC
from eql.engines import Event
from eql.utils import stream_stdin_events, stream_file_events

from .loader import Configuration
from .normalization import NormalizedEngine
from .utils import recursive_glob


def parse(text):
    try:
        return parse_query(text, implied_base=True, implied_any=True)
    except EqlError as exc:
        print(exc, file=sys.stderr)
        sys.exit(2)


def stream_events(path, file_format, encoding):
    if not path:
        return stream_stdin_events(file_format)
    else:
        return stream_file_events(path, file_format, encoding)


def convert_query(data_source, query, config):
    """Convert a normalized query to a specific data source."""
    source = config.normalizers[data_source]
    query = parse(query)
    converted = source.normalize_ast(query)
    print(converted)


def run_query(data_source, query, input_file, file_format, encoding, config):
    """Convert a normalized query to a specific data source."""
    if data_source is None:
        data_source = next(iter(config.domains))

    source = config.normalizers[data_source]
    query = parse(query)
    query = config.normalizers[source.domain].normalize_ast(query)

    events = stream_events(input_file, file_format, encoding)

    engine = NormalizedEngine({'print': True})
    engine.add_query(query)
    engine.stream_events(source.data_normalizer(e) for e in events)


def survey_analytics(data_source, input_file, file_format, encoding, analytics, count, config):
    """Convert a normalized query to a specific data source."""
    if analytics:
        # Clear out the analytics
        config = Configuration(parent=Configuration.default())

        for folder in analytics:
            for path in recursive_glob(folder, "*.toml"):
                config.add_analytic(toml.load(path))

    if data_source is None:
        data_source = next(iter(config.domain_schemas))

    source = config.normalizers[data_source]
    domain = config.normalizers[source.domain]
    engine = NormalizedEngine({'print': True})

    events = stream_events(input_file, file_format, encoding)

    normalized_iter = (source.data_normalizer(e) for e in events)

    if count:
        engine.add_query(parse("| count analytic_name, analytic_id"))

        # First pass results to an engine to get analytic output, then pass those
        counter = NormalizedEngine()

        def pass_analytic_output(r):
            engine.stream_event(Event.from_data({'analytic_id': r.analytic_id, 'analytic_name': config.get_analytic(r.analytic_id).name}))

        counter.add_output_hook(pass_analytic_output)
        for analytic in config.analytics:
            analytic = domain.normalize_ast(analytic)
            counter.add_analytic(analytic)

        counter.stream_events(normalized_iter)
        engine.finalize()

    else:
        for analytic in config.analytics:
            analytic = domain.normalize_ast(analytic)
            engine.add_query(analytic.query)

        engine.stream_events(normalized_iter)


def convert_data(data_source, input_file, output_file, encoding, file_format, config):
    """Convert a normalized query to a specific data source."""
    if data_source is None:
        data_source = next(iter(config.domains))
    source = config.normalizers[data_source]
    events = list(stream_events(input_file, file_format, encoding))

    print("Found {} events".format(len(events)))
    converted_events = []
    for e in events:
        converted_evt = source.data_normalizer(e)
        if converted_evt.type != EVENT_TYPE_GENERIC:
            converted_events.append(converted_evt.data)

    with open(output_file, "w") as f:
        json.dump(converted_events, f, indent=4, sort_keys=True)

    print("Converted {} events".format(len(converted_events)))


def normalize_main():
    """Entry point for EQL command line utility."""
    config = Configuration.default_with_analytics()
    sources = [str(source) for source in config.sources]

    parser = argparse.ArgumentParser(description='EQL Analytics')
    subparsers = parser.add_subparsers(help='Sub Command Help')

    convert_query_parser = subparsers.add_parser('convert-query', help='Convert a query to specific data source')
    convert_query_parser.set_defaults(func=convert_query)
    convert_query_parser.add_argument('query', help='EQL query in common schema')

    convert_data_parser = subparsers.add_parser('convert-data', help='Convert data from a specific data source')
    convert_data_parser.set_defaults(func=convert_data)
    convert_data_parser.add_argument('input-file', help='Input JSON file')
    convert_data_parser.add_argument('output-file', help='Output JSON file')

    query_parser = subparsers.add_parser('query', help='Query over a data source')
    query_parser.set_defaults(func=run_query)
    query_parser.add_argument('query', help='EQL query in common schema')

    survey_parser = subparsers.add_parser('survey', help='Run multiple analytics over non-normalized JSON data')
    survey_parser.set_defaults(func=survey_analytics)
    survey_parser.add_argument('-c', '--count', help='Print counts per analytic', action='store_true')
    survey_parser.add_argument('analytics', nargs='*', help='Path to analytic file or directory')

    for p in (survey_parser, query_parser):
        p.add_argument('--file', '-f', dest='input-file', help='Target file(s) to query with EQL')

    for p in (convert_data_parser, survey_parser, query_parser):
        p.add_argument('--encoding', '-e', help='Encoding of input file', default="utf8")
        p.add_argument('--format', dest='file-format', choices=['json', 'jsonl', 'json.gz', 'jsonl.gz'])

    for p in (convert_query_parser, convert_data_parser, survey_parser, query_parser):
        p.add_argument('--source', '-s', choices=sources, dest='data-source', help='Data source', required=False)

    args = parser.parse_args()
    kv = {k.replace('-', '_'): v for k, v in vars(args).items()}
    func = kv.pop('func', None)
    if func:
        return func(config=config, **kv)
