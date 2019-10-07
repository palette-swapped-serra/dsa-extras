from .nmm_common import file_contents, in_folder, name_stem, normalize, number
from .nmm_type import add_type
from dsa.parsing.line_parsing import INDENT, Comment


def _get_typename(name, size):
    if name is None:
        # FIXME handle larger fields as ascii?
        return {1: 'Byte', 2: 'Pair', 4: 'Quad'}.get(size, f'{size} bytes')
    return number(name, size * 8)


def _padding(amount):
    if amount & 1:
        yield [INDENT, ['Byte', '0'], Comment('padding')]
        amount -= 1
    if amount & 2:
        yield [INDENT, ['Pair', '0'], Comment('padding')]
        amount -= 2
    while amount > 0:
        yield [INDENT, ['Quad', '0'], Comment('padding')]
        amount -= 4
    if amount < 0:
        raise ValueError('NMM fields are out of order')


def _nmm_header(lines):
    if next(lines) != '1':
        raise ValueError('invalid header format - version is not 1')
    title = next(lines) # ignored
    chunk_offset = next(lines)
    if not chunk_offset.startswith('0x'):
        raise ValueError('chunk_offset must be hex')
    chunk_offset = int(chunk_offset, 0)
    count = int(next(lines))
    size = int(next(lines))
    names = next(lines) # index file - ignore for now.
    if next(lines) != 'NULL':
        raise ValueError('invalid header format - missing NULL')
    return chunk_offset, count, size


def _nmm_chunks(lines):
    while True:
        try:
            field_name = next(lines)
        except StopIteration:
            break # EOF
        else:
            try:
                yield _nmm_chunk(field_name, lines)
            except StopIteration: # couldn't read the rest of the chunk.
                raise ValueError('incomplete entry at EOF')


def _nmm_chunk(field_name, lines):
    field_offset = int(next(lines))
    size = int(next(lines))
    widget = next(lines) # ignored
    filename = next(lines)
    return field_name, field_offset, size, filename


def read_nmm(type_data, nmm_file):
    # populate type_data while producing struct_data etc. from the file.
    lines = file_contents(nmm_file)
    chunk_offset, count, chunk_size = _nmm_header(lines)
    struct_data = {}
    for field_name, field_offset, field_size, type_file in _nmm_chunks(lines):
        if type_file == 'NULL':
            typename = None
        else:
            typename = name_stem(type_file)
            type_file = in_folder(nmm_file, type_file)
            add_type(type_data, typename, field_size, type_file)
        struct_data[field_offset] = (typename, field_name, field_size)
    return struct_data, chunk_offset, count, chunk_size


def emit_structgroup(type_data, group_data):
    struct_data, chunk_offset, count, struct_size = group_data
    # Each NMM struct needs to go in its own structgroup.
    yield [
        ['align', '4'], ['endian', 'little'], ['count', str(count)],
        Comment(f'offset = 0x{chunk_offset:X}')
    ]
    yield []
    yield [['DATA']]
    struct_offset = 0
    for field_offset, field_data in sorted(struct_data.items()):
        typename, field_name, size = field_data
        yield from _padding(field_offset - struct_offset)
        struct_offset = field_offset + size
        yield [
            INDENT, [_get_typename(typename, size)], [normalize(field_name)]
        ]
    yield from _padding(struct_size - struct_offset)