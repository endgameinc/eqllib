"""Command line utility for ``eqllib``."""
from __future__ import print_function

import argparse
import json
import re
import sys

import toml
from eql import parse_query, EqlError, Event
from eql.schema import EVENT_TYPE_GENERIC
from eql.utils import stream_stdin_events, stream_file_events
from eql.table import Table

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
    with config.domain_schemas[source.domain].eql_schema:
        query = parse(query)
    converted = source.normalize_ast(query)
    print(converted)


def print_table(results, columns):
    """Print a list of results as a table."""
    if not results:
        print("No results found")
        return

    columns = re.split(r"[,\s]+", columns)

    if columns == ["*"]:
        columns = list(sorted(set(k for result in results for k in result)))

    table = Table.from_list(columns, results)
    print(table)


def run_query(data_source, query, input_file, file_format, encoding, config):
    """Convert a normalized query to a specific data source."""
    if data_source is None:
        data_source = next(iter(config.domains))

    source = config.normalizers[data_source]
    with config.domain_schemas[source.domain].eql_schema:
        query = parse(query)

    query = config.normalizers[source.domain].normalize_ast(query)

    events = stream_events(input_file, file_format, encoding)

    engine = NormalizedEngine({'print': True})
    engine.add_query(query)
    engine.stream_events(source.data_normalizer(e) for e in events)


def survey_analytics(data_source, input_file, file_format, encoding, analytics, count, config, columns):
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
    engine = NormalizedEngine({'print': not columns})

    events = stream_events(input_file, file_format, encoding)
    results = []

    normalized_iter = (source.data_normalizer(e) for e in events)

    if count:
        if columns:
            if columns == "*":
                columns = "count,analytic_name,analytic_id"

            engine.add_query(parse("""
            | unique_count analytic_name, analytic_id
            | sort count, analytic_name, analytic_id
            """))

        else:
            engine.add_query(parse("| count analytic_name, analytic_id"))

        # First pass results to an engine to get analytic output, then pass those
        counter = NormalizedEngine()

        def pass_analytic_output(r):
            engine.stream_event(Event.from_data({
                'analytic_id': r.analytic_id,
                'analytic_name': config.get_analytic(r.analytic_id).name
            }))

        counter.add_output_hook(pass_analytic_output)
        for analytic in config.analytics:
            analytic = domain.normalize_ast(analytic)
            counter.add_analytic(analytic)

        if not columns:
            def append_results(r):
                for event in r.events:
                    results.append(event)

            engine.add_output_hook(append_results)

        counter.stream_events(normalized_iter)
        engine.finalize()

        if columns is not None:
            print_table(results, columns)

    else:
        def include_analytic_info(result):
            analytic = config.get_analytic(result.analytic_id)

            for event in result.events:
                event.data.setdefault("analytic_id", analytic.id)
                event.data.setdefault("analytic_name", analytic.name)
                event.data.setdefault("techniques", analytic.metadata.get("techniques", []))
                event.data.setdefault("tactics", analytic.metadata.get("tactics", []))

                results.append(event.data)

            if not columns:
                engine.print_events(result.events)

        for analytic in config.analytics:
            analytic = domain.normalize_ast(analytic)
            engine.add_analytic(analytic)
 
        engine.add_output_hook(include_analytic_info)
        engine.stream_events(normalized_iter)

        if columns is not None:
            print_table(results, columns)


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
        p.add_argument('--source', '-s', required=p is convert_query_parser,
                       choices=sources, dest='data-source', help='Data source')

    for p in (survey_parser, query_parser):
        p.add_argument('--table', '-t', dest='columns',
                       help='Arguments for columns. For all columns, input "*"')

    args = parser.parse_args()
    kv = {k.replace('-', '_'): v for k, v in vars(args).items()}
    func = kv.pop('func', None)
    if func:
        return func(config=config, **kv)
