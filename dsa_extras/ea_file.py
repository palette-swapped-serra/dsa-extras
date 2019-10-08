from dsa.parsing.line_parsing import INDENT


def _header_flags(
    game=(), language=(), priority=('',), indexMode=('1',), **kwargs
):
    if game and language:
        raise ValueError('specify `game` or `language`, not both')
    language = set(language) | set(game)
    if language == {'FE6', 'FE7', 'FE8'}:
        language = {'FE'}
    if len(priority) > 1:
        raise ValueError('only a single priority may be specified')
    priority = priority[0]
    if len(indexMode) > 1:
        raise ValueError('only a single indexMode may be specified')
    extra = set(kwargs.keys())
    # Unsupported stuff that we can just ignore.
    # DSA doesn't allow for repeating structs this way, at least for now.
    extra.discard('repeatable')
    # EA associates alignment with structs; we want to associate it with groups.
    # So we ignore this information, and hard-code the group alignment.
    # The 'moveManual' groups should have an alignment of 1.
    extra.discard('offsetMod')
    # Manually turn these into group terminators.
    # the 'moveManual' groups should have a terminator of "04".
    extra.discard('terminatingList')
    # The kind of verification EA did is not applicable for us.
    extra.discard('unsafe')
    terminator, last = False, False
    if extra == {'end', 'noDisassembly'}:
        terminator = True
    elif extra == {'end'}:
        last = True
    elif extra == {'noDisassembly'}:
        # TEXTCG
        print('Warning: keeping an opcode EA wanted to skip for disassembly')
    elif extra:
        raise ValueError(f'got unexpected kwargs: {extra}')
    return {
        'sections': tuple((l, priority) for l in language),
        'factor': int(indexMode[0], 0),
        'is_terminator': terminator,
        'is_last': last
    }


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


class FieldType:
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


    @classmethod
    def create(cls, size, flags, name, fixed):
        """Modifies `flags` as a side effect, removing the flags relevant
        to Type creation."""
        referent = _extract_flag(flags, {'pointer'}, _referent_name, None)
        if referent is not None:
            # should not be any more flags.
            return cls('GBAPointer', size, name, fixed, referent=referent)
        signed = _extract_flag(flags, {'signed'}, _boolean_flag, False)
        base = _extract_flag(flags, {'preferredBase'}, _integer_flag, None)
        coordinates = _extract_flag(
            flags, {'coordinate', 'coordinates'}, _coord_flag, 1
        )
        return cls({
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
        }[size, coordinates], size, name, fixed, signed=signed, base=base)


    def _tokens_gen(self):
        yield INDENT
        if self._value_name is None:
            assert self._fixed is not None
            yield (self._typename, str(self._fixed))
        else:
            assert self._fixed is None
            yield (self._typename,)
            yield (self._value_name,)
        for k, v in self._flags.items():
            yield k, str(v)


    def tokens(self):
        return tuple(self._tokens_gen())


def _pad(amount, message):
    if amount & 3:
        raise ValueError("padding doesn't start on nybble boundary")
    if amount & 4:
        yield FieldType.create(4, {}, None, 0)
        amount -= 4
    amount //= 8
    if amount & 1:
        yield FieldType.create(8, {}, None, 0)
        amount -= 1
    if amount & 2:
        yield FieldType.create(16, {}, None, 0)
        amount -= 2
    while amount > 0:
        yield FieldType.create(32, {}, None, 0)
        amount -= 4
    if amount < 0:
        raise ValueError(message)


class EAStruct:
    def __init__(self, name, tag_value, size, flags):
        self._sections = flags['sections']
        self._name = name
        self._size = size * flags['factor']
        self._factor = flags['factor']
        self._fields = {}
        self._is_terminator = flags['is_terminator']
        self._is_last = flags['is_last']
        if tag_value:
            self._fields[0] = FieldType('Pair', 16, None, tag_value)
        elif self._size == 0:
            print('Warning: fixing struct size')
            self._size = 16 # SHLI is 2 bytes.


    def add_field(self, position, size, name, flags):
        position *= self._factor
        size *= self._factor
        fixed = None # unless the appropriate flag is set.
        if 'fixed' in flags:
            if flags['fixed']:
                raise ValueError(f'`fixed` flag cannot have an argument')
            del flags['fixed']
            name, fixed = None, int(name, 0)
        field = FieldType.create(size, flags, name, fixed)
        if flags:
            raise ValueError(f'extra flags {set(flags.keys())}')
        if position in self._fields:
            raise ValueError(f'already have a field at offset {position}')
        self._fields[position] = field


    def _fields_gen(self):
        position = 0
        for offset, field in sorted(self._fields.items()):
            yield from _pad(offset - position, 'overlapping fields')
            yield field
            position = offset + field.size
        yield from _pad(self._size - position, 'fields extend past end')


    def data(self):
        return (
            self._name, self._sections, self._is_terminator,
            tuple(self._fields_gen())
        )


def _flags_item(word):
    name, *parts = word.split(':')
    if name.startswith('-'): # almost always present, but don't require it
        name = name[1:]
    return name, parts


def _flags_dict(flags_text):
    return dict(map(_flags_item, flags_text.split()))


def _comma_items(text):
    result = text.split(',')
    if len(result) > 4:
        raise ValueError('too many commas')
    if len(result) < 3:
        raise ValueError('not enough commas')
    if len(result) == 3:
        result.append('')
    return result


def _parse_header(text):
    name, tag_value, size, flags = _comma_items(text)
    return (
        name.strip(), int(tag_value, 0), int(size, 0),
        _header_flags(**_flags_dict(flags))
    )


def _parse_indented(text):
    name, position, size, flags = _comma_items(text)
    return int(position, 0), int(size, 0), name.strip(), _flags_dict(flags)


def _get_lines(filename):
    with open(filename) as f:
        for line in f:
            full_line = line.partition('#')[0].rstrip()
            if full_line:
                line = full_line.lstrip()
                yield line, (line != full_line)


def parse_file(filename):
    # Comments have been stripped already.
    structs = []
    for line, indented in _get_lines(filename):
        if indented:
            if not structs:
                raise ValueError('indented line before first block')
            structs[-1].add_field(*_parse_indented(line))
        else:
            structs.append(EAStruct(*_parse_header(line)))
    return [s.data() for s in structs]
