import ast, functools, re


hexspec = re.compile('([0-9a-fA-F]{2})(?:-([0-9a-fA-F]{2}))?')


def check_ranges(bases, lookups, values):
    result = []
    for base, lookup, value in zip(bases, lookups, values):
        if lookup is None:
            if value != base:
                return None
            continue
        index = value - base
        if 0 <= index < len(lookup):
            result.append(lookup[index])
        else:
            return None
    return result


def _format_by_tag(tag, bases, lookups, values):
    params = check_ranges(bases, lookups, values)
    return None if params is None else tag.format(*params)


def _format_by_literal(literal, bases, values):
    return literal if values == bases else None


def _format_by_encoding(encoding, bases, lookups, values):
    params = check_ranges(bases, lookups, values)
    return None if params is None else bytes(values).decode(encoding)


def _extract_hexes(line):
    bases, lookups, positions = [], [], []
    while True:
        line = line.lstrip()
        match = hexspec.match(line.lstrip())
        if match is None:
            return line, bases, lookups, positions
        base = int(match.group(1), 16)
        bases.append(base)
        if match.group(2) is None:
            lookups.append(None)
        else:
            positions.append(len(lookups))
            size = int(match.group(2), 16) - base + 1
            if size < 2:
                raise ValueError('range must have at least two values')
            lookups.append([f'0x{x:02X}' for x in range(size)])
        line = line[match.end():]


def _make_template_formatter(text, bases, lookups, positions):
    if text == '*': # have to special-case logic for an empty label.
        label, params = '', ('*',)
    else:
        label, *params = text.split()
    label = label.replace('{', '{{').replace('}', '}}')
    placeholders = ' {}' * len(params)
    if not label:
        placeholders = placeholders[1:] # trim unnecessary space
    tag = f'[{label}{placeholders}]'
    if len(positions) != len(params):
        raise ValueError('incorrect number of parameters')
    for position, param in zip(positions, params):
        if param == '*':
            continue
        options = param.split('|')
        if len(options) != len(lookups[position]):
            raise ValueError('incorrect number of options for parameter')
        lookups[position] = options
    return functools.partial(_format_by_tag, tag, bases, lookups)


def _make_formatter(line):
    text, bases, lookups, positions = _extract_hexes(line)
    if text.startswith('['):
        if not text.endswith(']'):
            raise ValueError('unmatched [')
        formatter = _make_template_formatter(
            text[1:-1], bases, lookups, positions
        )
    elif text.startswith(('"', "'")):
        formatter = functools.partial(
            _format_by_literal, ast.literal_eval(text), bases
        )
    else:
        formatter = functools.partial(
            _format_by_encoding, text, bases, lookups
        )
    return formatter, len(bases)


def _apply_formatters(formatters, data):
    for formatter, size in formatters:
        result = formatter(data[:size])
        if result is not None:
            break
    else:
        raise ValueError('no valid format found')
    return result, size


def make_decoder(filename):
    with open(filename) as f:
        formatters = [
            _make_formatter(line.strip())
            for line in f
            if line.strip() and (not line.startswith('#'))
        ]
    return functools.lru_cache(None)(
        functools.partial(_apply_formatters, formatters)
    )
