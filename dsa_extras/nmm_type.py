from .nmm_common import number
from .nmm_enum import enum_from_file
from dsa.parsing.line_parsing import INDENT, Comment


def _emit_typeheader(name, size):
    yield [['type'], [number(name, size)]]
    yield [INDENT, [str(size)], ['value'], ['values', name]]
    yield []


def emit_types(type_data):
    for name, (values, sizes) in type_data.items():
        for size in sizes:
            yield from _emit_typeheader(name, size)
        yield from values # enum block was prepared ahead of time


def add_type(type_data, name, size, filename):
    size *= 8 # convert byte count to bit count
    if name in type_data:
        values, sizes = type_data[name]
        sizes.add(size)
    else:
        type_data[name] = (enum_from_file(name, filename), {size})
