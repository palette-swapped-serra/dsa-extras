from . import ea_groups


_field_name_lookup = {
    # FIXME: flags in BLDT.
    (1, 1): 'Bit',
    # FIXME: part of FlaggedCoordinates, and some turn count values.
    (4, 1): 'Nybble',
    (8, 1): 'Byte',
    # FE8 ARROW traps.
    # EA raws flag the `X coordinate` as coordinates, which is
    # probably wrong (they don't use a Y coordinate AFAICT).
    (8, 2): 'Byte',
    (16, 1): 'Pair',
    # Explicit padding on FE7 MUSM.
    # TODO: Split into a byte and pair.
    (24, 1): 'Triple',
    (32, 1): 'Quad',
    (16, 2): 'ByteCoord',
    (32, 2): 'PairCoord',
    (64, 2): 'QuadCoord',
    (12, 2): 'FlaggedCoord',
    (32, 4): 'InventoryAI'
}


class _Field:
    def __init__(self, typename, size, value_name, fixed, **kwargs):
        self._typename = typename
        self._size = size
        self._value_name = value_name
        self._fixed = fixed
        self._flags = kwargs


    @property
    def size(self):
        return self._size


    @property
    def fixed_dump(self):
        # TODO don't just assume endianness?
        count = self._size // 8
        return ''.join(
            (f'..' for b in range(count))
            if self._fixed is None
            else (f'{b:02X}' for b in self._fixed.to_bytes(count, 'little'))
        )


    def _tokens_gen(self):
        yield '    '
        if self._value_name is None:
            assert self._fixed is not None
            yield (self._typename, str(self._fixed))
        else:
            assert self._fixed is None
            yield (self._typename,)
            yield (self._value_name,)
        for k, v in self._flags.items():
            yield (k, str(v))


    def tokens(self):
        return tuple(self._tokens_gen())


def _extract_flag(flags, names, converter, default):
    found = [n for n in names if n in flags]
    if len(found) == 0:
        return default
    if len(found) > 1:
        raise ValueError(f'{found} are mutually exclusive')
    name = found[0]
    result = flags[name]
    del flags[name]
    return converter(result)


def _integer_flag(items):
    if len(items) != 1:
        raise ValueError('bad integer flag')
    return int(items[0], 0)


def _coord_flag(items):
    if len(items) != 1:
        raise ValueError('bad coordinates flag')
    text = items[0]
    if '-' in text:
        text = text.split('-')[-1] # just use the upper bound.
    return int(text, 0)


def _boolean_flag(items):
    if len(items) != 0:
        raise ValueError('bad boolean flag')
    return True


def _referent_name(items):
    if len(items) == 0:
        return '' # we need to distinguish `-pointer` from no flag at all.
    if len(items) == 1:
        return items[0]
    raise ValueError('bad pointer target')


def _referent_field(size, name, fixed, referent):
    typename = {
        'EventMovement': 'BytePointer',
        'ASM': 'ThumbPointer'
    }.get(referent, 'QuadPointer')
    attributes = {'referent': referent} if referent else {}
    return (typename, size, name, fixed, attributes)


def _normal_field(size, name, fixed, flags):
    signed = _extract_flag(flags, {'signed'}, _boolean_flag, False)
    base = _extract_flag(flags, {'preferredBase'}, _integer_flag, None)
    coordinates = _extract_flag(
        flags, {'coordinate', 'coordinates'}, _coord_flag, 1
    )
    typename = _field_name_lookup[size, coordinates]
    attributes = {}
    if typename in {'Byte', 'Pair', 'Quad'}:
        # TODO: support for base/signed overrides in DSA
        # attributes = {'signed': signed, 'base': base}
        pass
    elif typename == 'Bit':
        # XXX Will need to clean these up manually.
        assert not signed and base == 2
    elif typename in {'PairCoord', 'ByteCoord', 'QuadCoord'}:
        # These are complex types, so it won't be possible to override
        # the signed/base settings and separate types are needed.
        base_tag = {10: '', None: 'Hex'}[base]
        sign_tag = 'Signed' if signed else ''
        typename = f'{sign_tag}{base_tag}{typename}'
    elif typename == 'InventoryAI':
        typename = 'AI' if name == 'AI' else 'Inventory'
    else:
        # TODO: clean up turn-phase and flagged-coordinates setups.
        assert typename in {'Nybble', 'FlaggedCoord'}
    return (typename, size, name, fixed, attributes)


def _create_field(field_datum):
    size, flags, name, fixed = field_datum
    referent = _extract_flag(flags, {'pointer'}, _referent_name, None)
    referent = ea_groups.lookup(referent)
    if referent is not None:
        data = _referent_field(size, name, fixed, referent)
    else:
        data = _normal_field(size, name, fixed, flags)
    if flags:
        raise ValueError(f'extra flags {set(flags.keys())}')
    typename, size, name, fixed, new_flags = data
    return _Field(typename, size, name, fixed, **new_flags)


def _pad(amount):
    if amount & 3:
        raise ValueError("padding doesn't start on nybble boundary")
    if amount & 4:
        yield _create_field((4, {}, None, 0))
        amount -= 4
    amount //= 8
    if amount & 1:
        yield _create_field((8, {}, None, 0))
        amount -= 1
    if amount & 2:
        yield _create_field((16, {}, None, 0))
        amount -= 2
    while amount > 0:
        yield _create_field((32, {}, None, 0))
        amount -= 4


def create_fields(total_size, data):
    position = 0
    for offset, field_datum in data:
        if offset < position:
            raise ValueError('overlapping fields')
        yield from _pad(offset - position)
        field = _create_field(field_datum)
        yield field
        position = offset + field_datum[0]
    if total_size < position:
        raise ValueError('fields extend past end')
