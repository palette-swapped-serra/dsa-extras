from .nmm_common import file_contents, normalize, number
from dsa.parsing.line_parsing import INDENT


def _emit_values(enum_name, filename):
    lines = file_contents(filename)
    next(lines) # skip line count
    yield [['enum'], [enum_name]]
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
        yield [INDENT, [f'0x{value:X}'], [name]]
    yield []


def enum_from_file(enum_name, filename):
    return list(_emit_values(enum_name, filename))
