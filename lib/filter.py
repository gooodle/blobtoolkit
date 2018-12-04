#!/usr/bin/env python3

# pylint: disable=no-member, too-many-branches, too-many-locals

"""
Filter a BlobDir.

Usage:
    blobtools filter [--param STRING...] [--query-string STRING]  [--json JSON]
                     [--list TXT] [--invert] [--output DIRECTORY]
                     [--fasta FASTA] [--fastq FASTQ...] [--suffix STRING]
                     [--cov BAM] DIRECTORY

Arguments:
    DIRECTORY             Existing Blob directory.

Options:
    --param STRING        String of type param=value.
    --query-string STRING List of param=value pairs from url query string.
    --json JSON           JSON format list file as generated by BlobtoolKit Viewer.
    --list TXT            Space or newline separated list of identifiers.
    --invert              Invert filter (exclude matching records).
    --output DIRECTORY    Space or newline separated list of identifiers.
    --fasta FASTA         FASTA format assembly file to be filtered.
    --fastq FASTQ         FASTQ format read file to be filtered (requires --cov).
    --cov BAM             BAM/SAM/CRAM read alignment file.
    --suffix STRING       String to be added to filtered filename [Default: filtered]

"""

import re
import urllib
import math
from collections import defaultdict
from docopt import docopt
import file_io
import cov
import fasta
# from taxdump import Taxdump
from field import Identifier, Variable, Category
# from dataset import Metadata
from fetch import fetch_field, fetch_metadata

FIELDS = [{'flag': '--fasta', 'module': fasta, 'depends': ['identifiers']},
          {'flag': '--fastq', 'module': cov, 'depends': ['identifiers'], 'requires': ['--cov']}]


def parse_params(args, meta):
    """Parse and perform sanity checks on filer parameters."""
    strings = args.get('--param', [])
    valid = {'variable': ['Min', 'Max', 'Inv'], 'category': ['Keys', 'Inv']}
    if args.get('--query-string'):
        qstr = args['--query-string']
        qstr = re.sub(r'^.*\?', '', qstr)
        qstr = re.sub(r'#.*$', '', qstr)
        strings += urllib.parse.unquote(qstr).split('&')
    params = defaultdict(dict)
    for string in strings:
        print(string)
        try:
            key, value = string.split('=')
        except ValueError:
            print("WARN: Skipping string '%s', not a valid parameter" % string)
            continue
        try:
            field_id, param = key.split('--')
        except ValueError:
            print("WARN: Skipping string '%s', not a valid parameter" % string)
            continue
        if meta.has_field(field_id):
            field_meta = meta.field_meta(field_id)
            # if field_meta.get('range'):
            #     field_type = 'variable'
            # else:
            #     field_type = 'category'
            if param in valid[field_meta['type']]:
                params[field_id].update({param: value})
            else:
                print("WARN: '%s' is not a valid parameter for field '%s'" % (param, field_id))
        else:
            print("WARN: Skipping field '%s', not present in dataset" % field_id)
    return dict(params)


def filter_by_params(meta, directory, indices, params, invert_all):
    """Filter included set using params."""
    for field_id, filters in params.items():
        field = fetch_field(directory, field_id, meta)
        invert = invert_all
        if filters.get('Inv'):
            invert = not invert
        if isinstance(field, Category):
            keys = field.keys
            if filters.get('Keys'):
                keys = [int(x)
                        if x.isdigit() else field.keys.index(x)
                        for x in filters['Keys'].split(',')]
                if invert:
                    keys = [i for i, x in enumerate(field.keys) if i not in keys]
                keys = set(keys)
                indices = [i for i in indices if field.values[i] in keys]
        elif isinstance(field, Variable):
            low = -math.inf
            high = math.inf
            if filters.get('Min'):
                low = float(filters['Min'])
            if filters.get('Max'):
                high = float(filters['Max'])
            if invert:
                indices = [i for i in indices if field.values[i] < low or field.values[i] > high]
            else:
                indices = [i for i in indices if low <= field.values[i] <= high]
    return indices


def filter_by_json(identifiers, indices, json_file, invert):
    """Filter included set using json file."""
    data = file_io.load_yaml(json_file)
    id_set = set(data['identifiers'])
    if not invert:
        indices = [i for i in indices if identifiers[i] in id_set]
    else:
        indices = [i for i in indices if identifiers[i] not in id_set]
    return indices


def create_filtered_dataset(dataset_meta, indir, outdir, indices):
    """Write filtered records to new dataset."""
    meta = dataset_meta.to_dict()
    meta.update({'fields': [],
                 'origin': dataset_meta.dataset_id,
                 'records': len(indices)})
    meta = fetch_metadata(outdir, meta=meta)
    # meta = fetch_metadata(outdir, **args)
    for field_id in dataset_meta.list_fields():
        field_meta = dataset_meta.field_meta(field_id)
        if not field_meta.get('children'):
            field_meta.pop('data', False)
            keys = None
            slot = None
            headers = None
            full_field = fetch_field(indir, field_id, dataset_meta)
            if isinstance(full_field, (Variable, Identifier)):
                values = [full_field.values[i] for i in indices]
                if isinstance(full_field, Variable):
                    field_meta.update({'range': [min(values), max(values)]})
            elif isinstance(full_field, Category):
                full_values = full_field.expand_values()
                values = [full_values[i] for i in indices]
            else:
                full_values = full_field.expand_values()
                values = [full_values[i] for i in indices]
                slot = full_field.category_slot
                try:
                    headers = full_field.headers
                except AttributeError:
                    pass
                if field_meta.get('parent'):
                    parent_field = fetch_field(outdir, field_meta['parent'], dataset_meta)
                    if parent_field:
                        keys = parent_field.keys
            field = type(full_field)(field_id,
                                     meta=field_meta,
                                     values=values,
                                     fixed_keys=keys,
                                     category_slot=slot,
                                     headers=headers)
            parents = dataset_meta.field_parent_list(field_id)
            meta.add_field(parents, **field_meta, field_id=field_id)
            json_file = "%s/%s.json" % (outdir, field.field_id)
            file_io.write_file(json_file, field.values_to_dict())
    file_io.write_file("%s/meta.json" % outdir, meta.to_dict())


def main():
    """Entrypoint for blobtools filter."""
    args = docopt(__doc__)
    meta = fetch_metadata(args['DIRECTORY'], **args)
    params = parse_params(args, meta)
    identifiers = fetch_field(args['DIRECTORY'], 'identifiers', meta)
    indices = [index for index, value in enumerate(identifiers.values)]
    invert = args['--invert']
    if params:
        indices = filter_by_params(meta, args['DIRECTORY'], indices, params, invert)
    if args['--json']:
        indices = filter_by_json(identifiers.values, indices, args['--json'], invert)
    if args['--output']:
        create_filtered_dataset(meta, args['DIRECTORY'], args['--output'], indices)
    ids = [identifiers.values[i] for i in indices]
    for field in FIELDS:
        if args[field['flag']]:
            # for dep in field['depends']:
            #     if dep not in dependencies or not dependencies[dep]:
            #         dependencies[dep] = fetch_field(args['DIRECTORY'], dep)
            requirements = True
            if field.get('requires'):
                for flag in field['requires']:
                    if not args[flag]:
                        print("WARN: '%s' must be set to use option '%s'"
                              % (flag, field['flag']))
                        requirements = False
            if not requirements:
                continue
            field['module'].apply_filter(ids, args[field['flag']], **args)
    # else:
    #     ids = [identifiers.values[i] for i in indices]
    #     print('\n'.join(ids))
# file_io.write_file(json_file, data.values_to_dict())
# file_io.write_file("%s/meta.json" % args['DIRECTORY'], meta.to_dict())


if __name__ == '__main__':
    main()
