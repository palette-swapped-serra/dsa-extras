class EAStructFlags:
    def __init__(
        self, language=(), priority=(None,), indexMode=('1',), **kwargs
    ):
        if len(priority) > 1:
            raise ValueError('only a single priority may be specified')
        priority = priority[0]
        if len(indexMode) > 1:
            raise ValueError('only a single indexMode may be specified')
        self._factor = int(indexMode[0], 0)
        extra = set(kwargs.keys())
        if extra == {'end', 'noDisassembly'}:
            self._is_terminator = True
        elif extra:
            raise ValueError(f'got unexpected kwargs: {set(kwargs.keys())}')
        else:
            self._is_terminator = False
        self._sections = tuple((priority, l) for l in language)


    @property
    def sections(self):
        return self._sections


    @property
    def factor(self):
        return self._factor


    @property
    def is_terminator(self):
        return self._is_terminator


class EAStruct:
    def __init__(self, name, tag_value, size, flags):
        self._sections = flags.sections
        self._name = name
        self._size = size * flags.factor
        self._factor = flags.factor
        self._fields = {}
        self._is_terminator = flags.is_terminator
        if tag_value:
            self._add_field(0, 16, tag_value, {})


    def add_field(self, position, size, name_or_fixed, flags):
        self._add_field(
            position * self._factor, size * self._factor, name_or_fixed, flags
        )


    def _add_field(self, position, size, name_or_fixed, flags):
        name = name_or_fixed if isinstance(name_or_fixed, str) else None
        fixed = name_or_fixed if isinstance(name_or_fixed, int) else None
        if position in self._fields:
            raise ValueError(f'already have a field at offset {position}')
        self._fields[position] = (size, name, fixed, flags)


    def _fields_gen(self):
        position = 0
        for offset, data in sorted(self._fields.items()):
            if offset < position:
                raise ValueError('overlapping fields')
            if offset > position:
                yield (offset - position, None, 0, {}) # padding
            yield data
            position = offset + data[0]
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
        EAStructFlags(**_flags_dict(flags))
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
