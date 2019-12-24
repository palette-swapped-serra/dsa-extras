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
    (32, 1): 'Quad',
    (16, 2): 'ByteCoord',
    (32, 2): 'PairCoord',
    (64, 2): 'QuadCoord',
    (12, 2): 'FlaggedCoord',
    (32, 4): 'InventoryAI'
}


def _process_field(typename, size, value_name, fixed, attributes):
    count = size // 8
    # the type of `fingerprint` sequence doesn't matter, since it will be
    # concatenated into the struct's fingerprint anyway.
    if fixed is None:
        assert value_name is not None
        # The value 256 ensures more specific results come before general ones.
        fingerprint = [256] * count
        tokens = ['    ', (typename,), (value_name,)]
    else:
        assert value_name is None
        fingerprint = fixed.to_bytes(count, 'little')
        tokens = ['    ', (typename, str(fixed))]
    tokens.extend((k, str(v)) for k, v in sorted(attributes.items()))
    return fingerprint, tuple(tokens)


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
        if name is not None and 'pointer' not in name.lower():
            # Special-case the type for certain field names, but ignore
            # fields whose names indicate that they're pointers. (If no
            # referent is specified, they'll end up here, which is awkward.)
            if 'event' in name.lower():
                # We can always shrink these down to a Byte, and the main loop
                # will implicitly pad as needed. But we need to recognize them
                # as such because the EventID type is hard-coded to that size.
                size = 8
                typename = 'EventID'
            elif 'char' in name.lower():
                size = 8
                typename = 'CharacterID'
            elif 'class' in name.lower():
                size = 8
                typename = 'ClassID'
    elif typename == 'Bit':
        # Battle data flags.
        # XXX Will need to clean these up manually.
        assert not signed and base == 2
    elif typename == 'ByteCoord' and name == 'Turns':
        # HAX: Special case for fields with this name.
        typename = 'Turn'
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
    return data


def _pad(amount):
    if amount & 3:
        raise ValueError("padding doesn't start on nybble boundary")
    if amount & 4:
        yield ('Nybble', 4, None, 0, {})
        amount -= 4
    amount //= 8
    if amount & 1:
        yield ('Byte', 8, None, 0, {})
        amount -= 1
    if amount & 2:
        yield ('Pair', 16, None, 0, {})
        amount -= 2
    while amount > 0:
        yield ('Quad', 32, None, 0, {})
        amount -= 4


def _update(prev_field, typename, size, name, fixed, attributes):
    if prev_field == 'FlaggedCoord':
        assert typename == 'Nybble' and fixed is None
        # skip this one and reset prev_field state.
        return None, None, 0
    if prev_field == 'Nybble':
        assert typename == 'Nybble' and fixed is None
        # reset state; emit a fixed type.
        return None, 'Phase' if name == 'TurnMoment' else 'MapChangeType', 8
    # if we get this far, prev_field should be None, and we may set it.
    assert prev_field is None
    if typename == 'FlaggedCoord':
        # expect a matching nybble, but do yield this.
        return 'FlaggedCoord', typename, 16
    if typename == 'Nybble':
        # leading zero nybble with variable follower. Don't emit this time.
        return 'Nybble', None, 0
    # Normal handling.
    return None, typename, size


def _create_raw_fields(total_size, data):
    position = 0
    prev_field = None
    for offset, field_datum in data:
        if offset < position:
            raise ValueError('overlapping fields')
        yield from _pad(offset - position)
        typename, size, name, fixed, attributes = _create_field(field_datum)
        yield typename, size, name, fixed, attributes
        position = offset + size
    if total_size < position:
        raise ValueError('fields extend past end')


def create_fields(total_size, data):
    prev_field = None
    # Filter through the raw field data and possibly suppress some fields
    # and modify others; for each field to emit, process into a field
    # fingerprint and the output tokens.
    for raw in _create_raw_fields(total_size, data):
        typename, size, name, fixed, attributes = raw
        prev_field, typename, size = _update(prev_field, *raw)
        if typename is not None:
            yield _process_field(typename, size, name, fixed, attributes)
