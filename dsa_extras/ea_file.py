from . import ea_groups
from .ea_field import create_fields


def _extract_single(value, name):
    if len(value) > 1:
        raise ValueError(f'only a single {name} may be specified')
    return value[0]


def _collate(priority, language, game):
    language = set(language) | set(game)
    # Assorted hacks to sort/collate the raws properly.
    group = ea_groups.lookup(priority)
    if group is None:
        language = set() # suppress generation entirely
    elif language == {'FE6', 'FE7', 'FE8'} and group != 'EventTrigger':
        language = {'FE'} # should be just the shop items list.
    return group, language


def _trim_kwargs(kwargs):
    extra = set(kwargs.keys())
    # Unsupported stuff that we can just ignore.
    # DSA doesn't allow for repeating structs this way, at least for now.
    extra.discard('repeatable')
    # EA associates alignment with structs; DSA associates it with pointers
    # and/or structgroups.
    # So we ignore this information, and hard-code the pointer alignments.
    # The 'moveManual' groups should have an alignment of 1, so we swap
    # `QuadPointer` for `BytePointer` where the referent is moveManual.
    extra.discard('offsetMod')
    # Manually turn these into group terminators.
    # the 'moveManual' groups should have a terminator of "04".
    extra.discard('terminatingList')
    # The kind of verification EA did is not applicable for us.
    extra.discard('unsafe')
    return extra


def _header_flags(
    game=(), language=(), priority=('',), indexMode=('1',), **kwargs
):
    if game and language:
        raise ValueError('specify `game` or `language`, not both')
    priority = _extract_single(priority, 'priority')
    group, language = _collate(priority, language, game)
    factor = int(_extract_single(indexMode, 'indexMode'), 0)
    extra = _trim_kwargs(kwargs)
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
        'sections': tuple((l, group) for l in language),
        'factor': factor,
        'is_terminator': terminator,
        'is_last': last
    }


class EAStruct:
    def __init__(self, name, tag_value, size, flags):
        self._sections = flags['sections']
        self._name = name
        self._size = size * flags['factor']
        self._factor = flags['factor']
        self._field_data = {}
        self._is_terminator = flags['is_terminator']
        self._is_last = flags['is_last']
        if tag_value:
            self._field_data[0] = (16, {}, None, tag_value)
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
        field_datum = (size, flags, name, fixed)
        if position in self._field_data:
            raise ValueError(f'already have a field at offset {position}')
        self._field_data[position] = field_datum


    def data(self):
        fields_data = sorted(self._field_data.items())
        fingerprint = []
        token_lines = []
        for field_fingerprint, tokens in create_fields(self._size, fields_data):
            fingerprint.extend(field_fingerprint)
            token_lines.append(tokens)
        return (
            self._sections, self._name, self._is_terminator, self._is_last,
            tuple(fingerprint), tuple(token_lines)
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
    parsed_flags = _header_flags(**_flags_dict(flags))
    return (name.strip(), int(tag_value, 0), int(size, 0), parsed_flags)


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
