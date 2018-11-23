#!/usr/bin/env python3

# pylint: disable=c-extension-no-member

"""
Example module with functions to read, write and parse files.

Simple tests are included in docstrings and run using doctest.

Further tests are implemented in a separate file using pytest
(tests/unit_tests/test_file_io.py) to avoid adding test-specific code to
docstrings.
"""

import gzip
import pathlib
import yaml
import ujson


def read_file(filename):
    r"""
    Read a whole file into memory.

    >>> read_file('tests/files/infile')
    'testfile content\n'
    >>> read_file('nofile')

    """
    try:
        with stream_file(filename) as fh:
            return fh.read()
    except AttributeError:
        return None


def stream_file(filename):
    """
    Stream a file, line by lineself.

    Automatically detect gzipped files based on suffix.
    """
    if '.gz' in pathlib.Path(filename).suffixes:
        try:
            return gzip.open(filename, 'rt')
        except OSError:
            return None
    try:
        return open(filename, 'r')
    except IOError:
        return None


def load_yaml(filename):
    """
    Parse a JSON/YAML file.

    load_yaml('identifiers.yaml')
    """
    data = read_file(filename)
    if data is None:
        return data
    if '.json' in filename:
        content = ujson.loads(data)
    elif '.yaml' in filename:
        content = yaml.load(data)
    else:
        content = data
    return content


def write_file(filename, data):
    """
    Write a file, use suffix to determine type and compression.

    - types: '.json', '.yaml'
    - compression: None, '.gz'

    write_file('variable.json.gz')
    """
    if '.json' in filename:
        content = ujson.dumps(data, indent=1)
    elif '.yaml' in filename:
        content = yaml.dump(data, indent=1)
    else:
        content = data
    if '.gz' in filename:
        try:
            with gzip.open(filename, 'wt') as fh:
                fh.write(content)
        except OSError:
            return False
    else:
        try:
            with open(filename, 'wt') as fh:
                fh.write(content)
        except IOError:
            return False
    return True


if __name__ == '__main__':
    import doctest
    doctest.testmod()
