from .nmm_common import file_contents, in_folder, name_stem, number, words
from .nmm_type import add_type


def _pad(kind):
    return ('    ', (kind, '0'), ('# padding',))


def _padding(amount):
    if amount & 1:
        yield _pad('Byte')
        amount -= 1
    if amount & 2:
        yield _pad('Pair')
        amount -= 2
    while amount > 0:
        yield _pad('Quad')
        amount -= 4
    if amount < 0:
        raise ValueError('NMM fields overlap')


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
    print("Reading NMM:", nmm_file)
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


def fix_type_and_name(typename, name, size):
    parts = words(name)
    filtered = [w for w in parts if w.lower() != 'pointer']
    is_pointer = len(filtered) != len(parts)
    if not filtered:
        filtered = parts # preserve names that are just 'pointer'
    new_typename = (
        'BytePointer' # don't make any alignment assumptions.
        if is_pointer
        else {1: 'Byte', 2: 'Pair', 4: 'Quad'}.get(size, f'{size} bytes')
        if typename is None
        else number(typename, size * 8)
    )
    return new_typename, ' '.join(filtered)


def emit_structgroup(type_data, group_data):
    struct_data, chunk_offset, count, struct_size = group_data
    # Each NMM struct needs to go in its own structgroup.
    yield (
        '', ('align', '4'), ('count', str(count)),
        (f'# offset = {hex(chunk_offset)}',)
    )
    yield ('',)
    yield ('', ('DATA',))
    struct_offset = 0
    for field_offset, field_data in sorted(struct_data.items()):
        typename, field_name, size = field_data
        yield from _padding(field_offset - struct_offset)
        struct_offset = field_offset + size
        typename, field_name = fix_type_and_name(typename, field_name, size)
        yield ('    ', (typename,), (field_name,))
    yield from _padding(struct_size - struct_offset)
