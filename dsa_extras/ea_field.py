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
    (4, 1): 'CoordFlags',
    (32, 4): 'InventoryAI'
}


class _Field:
    def __init__(self, typename, size, value_name, fixed, **kwargs):
        self._typename = typename
        self._size = size
        self._value_name = value_name
        self._fixed = fixed
        if 'referent' in kwargs and kwargs['referent'] == '':
            del kwargs['referent']
        if 'signed' in kwargs and not kwargs['signed']:
            del kwargs['signed']
        if 'base' in kwargs and kwargs['base'] is None:
            del kwargs['base']
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


def create_field(size, flags, name, fixed):
    """Modifies `flags` as a side effect, removing the flags relevant
    to Type creation."""
    referent = _extract_flag(flags, {'pointer'}, _referent_name, None)
    referent = ea_groups.lookup(referent)
    if referent is not None:
        # should not be any more flags.
        typename = {
            'EventMovement': 'BytePointer',
            'ASM': 'ThumbPointer'
        }.get(referent, 'QuadPointer')
        return _Field(typename, size, name, fixed, referent=referent)
    signed = _extract_flag(flags, {'signed'}, _boolean_flag, False)
    base = _extract_flag(flags, {'preferredBase'}, _integer_flag, None)
    coordinates = _extract_flag(
        flags, {'coordinate', 'coordinates'}, _coord_flag, 1
    )
    return _Field(
        _field_name_lookup[size, coordinates],
        size, name, fixed, signed=signed, base=base
    )
