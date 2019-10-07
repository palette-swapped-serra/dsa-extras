def _header_flags(language=(), priority=(None,), indexMode=('1',), **kwargs):
    language = set(language)
    if language == {'FE6', 'FE7', 'FE8'}:
        language = {'FE'}
    if len(priority) > 1:
        raise ValueError('only a single priority may be specified')
    priority = priority[0]
    if len(indexMode) > 1:
        raise ValueError('only a single indexMode may be specified')
    extra = set(kwargs.keys())
    if extra == {'end', 'noDisassembly'}:
        terminator = True
    elif extra:
        raise ValueError(f'got unexpected kwargs: {set(kwargs.keys())}')
    else:
        terminator = False
    return {
        'sections': tuple((l, priority) for l in language),
        'factor': int(indexMode[0], 0),
        'is_terminator': terminator
    }


def _extract_flag(flags, name, converter, default):
    if name not in flags:
        return default
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
    def __init__(self, name, signed, base, referent, size):
        self._name = name
        self._signed = signed
        self._base = base
        self._referent = referent
        self._size = size


    @property
    def size(self):
        return self._size


    @classmethod
    def create(cls, size, flags):
        """Modifies `flags` as a side effect, removing the flags relevant
        to Type creation."""
        referent = _extract_flag(flags, 'pointer', _referent_name, None)
        if referent is not None:
            # should not be any more flags.
            return cls('GBAPointer', None, None, referent, size)
        signed = _extract_flag(flags, 'signed', _boolean_flag, False)
        base = _extract_flag(flags, 'preferredBase', _integer_flag, None)
        coordinates = _extract_flag(flags, 'coordinates', _coord_flag, 1)
        return cls({
            (8, 1): 'Byte',
            (16, 1): 'Pair',
            (32, 1): 'Quad',
            (16, 2): 'ByteCoord',
            (32, 2): 'PairCoord',
            (64, 2): 'QuadCoord',
            (12, 2): 'FlaggedCoord',
            (4, 1): 'CoordFlags',
            (32, 4): 'InventoryAI'
        }[size, coordinates], signed, base, None, size)


    def __repr__(self):
        if self._referent is not None:
            return f'{self._name}<ref: {self._referent}>'
        else:
            return f'{self._name}<base: {self._base}><signed: {self._signed}>'


class EAStruct:
    def __init__(self, name, tag_value, size, flags):
        self._sections = flags['sections']
        self._name = name
        self._size = size * flags['factor']
        self._factor = flags['factor']
        self._fields = {}
        self._is_terminator = flags['is_terminator']
        if tag_value:
            self._add_field(0, 16, str(tag_value), {'fixed': []})


    def add_field(self, position, size, name_or_fixed, flags):
        self._add_field(
            position * self._factor, size * self._factor, name_or_fixed, flags
        )


    def _add_field(self, position, size, name, flags):
        fixed = None # unless the appropriate flag is set.
        if 'fixed' in flags:
            if flags['fixed']:
                raise ValueError(f'`fixed` flag cannot have an argument')
            del flags['fixed']
            name, fixed = None, int(name, 0)
        type_data = FieldType.create(size, flags)
        if flags:
            raise ValueError(f'extra flags {set(flags.keys())}')
        if position in self._fields:
            raise ValueError(f'already have a field at offset {position}')
        self._fields[position] = (type_data, name, fixed)


    def _fields_gen(self):
        position = 0
        for offset, data in sorted(self._fields.items()):
            if offset < position:
                raise ValueError('overlapping fields')
            if offset > position:
                yield (offset - position, None, 0, {}) # padding
            yield data
            position = offset + data[0].size
        if position > self._size:
            raise ValueError('fields extend past end')
        if position < self._size:
            yield (self._size - position, None, 0, {}) # padding


    def data(self):
        return (
            self._name, self._sections, self._is_terminator,
            tuple(self._fields_gen())
        )


def _flags_item(word):
    name, *parts = word.split(':')
    if not name.startswith('-'):
        raise ValueError('invalid flag')
    return name[1:], parts


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
