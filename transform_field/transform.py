#!/usr/bin/env python3

import sys
import hashlib
import re

from datetime import datetime
from dateutil import parser


def is_transform_required(record, when):
    """Detects if the transformation is required or not based on
    the defined conditions and the actual values in a record"""
    transform_required = False

    # Check if conditional transformation matches criterias
    if when:

        # Evaluate every condition
        for condition in when:
            column_to_match = condition.get('column')
            column_value = record.get(column_to_match, "")
            cond_equals = condition.get('equals')
            cond_pattern = condition.get('regex_match')

            # Exact condition
            if cond_equals:
                if column_value == cond_equals:
                    transform_required = True
                else:
                    transform_required = False
                    break

            # Regex based condition
            if cond_pattern:
                matcher = re.compile(cond_pattern)
                if matcher.search(column_value):
                    transform_required = True

                # Condition does not meet, exit the loop
                else:
                    transform_required = False
                    break

    # Transformation is always required if 'when' condition not defined
    else:
        transform_required = True

    return transform_required


def extract_email_domain(string):
    if not isinstance(string, str):
        raise ValueError(f'{string} is not a string')

    split_string = string.split('@')
    if len(split_string) > 1:
        # Extract last entry
        return split_string[-1]

    return string

def extract_email_prefix(string):
    if not isinstance(string, str):
        raise ValueError(f'{string} is not a string')

    split_string = string.split('@')
    if len(split_string) > 1:
        # Extract last entry
        return split_string[0]

    return string

def prefix_hash_email(string):
    domain = extract_email_domain(string)
    prefix = extract_email_prefix(string)
    prefix_hash = hashlib.sha256(prefix.encode('utf-8')).hexdigest()

    return f'{prefix_hash}@{domain}'

def do_transform(record, field, trans_type, when=None):
    """Transform a value by a certain transformation type.
    Optionally can set conditional criterias based on other
    values of the record"""
    try:
        value = record.get(field)

        # Do transformation only if required
        if is_transform_required(record, when):

            # Transforms any input to NULL
            if trans_type == "SET-NULL":
                return None
            # Transforms string input to hash
            elif trans_type == "HASH":
                return hashlib.sha256(value.encode('utf-8')).hexdigest()
            # Transforms string input to hash skipping first n characters, e.g. HASH-SKIP-FIRST-2
            elif 'HASH-SKIP-FIRST' in trans_type:
                return value[:int(trans_type[-1])] + hashlib.sha256(value.encode('utf-8')[int(trans_type[-1]):]).hexdigest()
            # Transforms any date to stg
            elif trans_type == "MASK-DATE":
                return parser.parse(value).replace(month=1, day=1).isoformat()
            # Transforms any number to zero
            elif trans_type == "MASK-NUMBER":
                return 0
            # Transforms any value to "hidden"
            elif trans_type == "MASK-HIDDEN":
                return 'hidden'
            # Transforms any value to only email domain
            elif trans_type == 'EMAIL-DOMAIN-EXTRACTION':
                return extract_email_domain(value)
            # Transforms any value to only prefix hash & email domain
            elif trans_type == 'EMAIL-PREFIX-HASH':
                return prefix_hash_email(value)
            # Return the original value if cannot find transformation type
            else:
                return value

        # Return the original value if cannot find transformation type
        else:
            return value

    # Return the original value if cannot transform
    except Exception:
        return value


def do_nested_transform(record,
                        field,
                        nested_field,
                        trans_type,
                        when=None):
    # """Transform a value by a certain transformation type.
    # Optionally can set conditional criterias based on other
    # values of the record"""
    try:

        nested_record = record.get(field)

        if isinstance(nested_record, list):

            new_record = []
            for item in nested_record:
                transformed = do_transform(item,
                                           nested_field,
                                           trans_type,
                                           when=when)
                item[nested_field] = transformed
                new_record.append(item)

            return new_record

        elif isinstance(nested_record, dict):
            transformed = do_transform(nested_record,
                                       nested_field,
                                       trans_type,
                                       when=when)
            item[nested_field] = transformed
            return item

        else:
            raise Exception(f'unnesting of {record} failed')

    # Return the original value if cannot transform
    except Exception:
        return nested_record
