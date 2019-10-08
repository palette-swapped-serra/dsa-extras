from .nmm_common import file_contents, normalize, number
from dsa.parsing.line_parsing import INDENT


def _raw(filename):
    lines = file_contents(filename)
    next(lines) # skip line count
    seen = set()
    for line in lines:
        value, basename = line.split(None, 1)
        value = int(value, 0)
        basename = normalize(basename)
        name = basename
        i = 2
        while name in seen:
            name = number(basename, i)
            i += 1
        seen.add(name)
        yield (name, value)


def _emit_values(enum_name, items):
    yield [['enum'], [enum_name]]
    for name, value in items:
        yield [INDENT, [f'0x{value:X}'], [name]]
    yield []


def enum_from_file(enum_name, filename):
    items = list(_raw(filename))
    return list(_emit_values(enum_name, items))
