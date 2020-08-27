import codecs
from functools import partial
from io import BytesIO
from itertools import product
import re


_CONFIG_PATTERN = re.compile(
    #   raw              text_code            count param_specs
    r'^([0-9a-fA-F]+\s+)?\[([0-9a-zA-Z=\s]*)\](\**)([0-9a-zA-Z|\s]*)$'
)


def _read_mapped(mapping, size, stream):
    start = stream.tell()
    for amount in range(size, 0, -1):
        data = stream.read(amount)
        try:
            return mapping[data]
        except KeyError:
            stream.seek(start)
            # If we run out of options, return None implicitly.


def _read_encoding(data, reader):
    start = reader.tell()
    try:
        return reader.read(1)
    except UnicodeDecodeError:
        chunk = data[start:reader.tell()]
        return f'[0x{chunk.hex()}]'


def _decode_gen(data, mapping, encoding):
    stream = BytesIO(data)
    candidates = (
        partial(_read_mapped, mapping, max(len(k) for k in mapping), stream),
        partial(_read_encoding, data, codecs.getreader(encoding)(stream))
    )
    while True:
        for method in candidates:
            result = method()
            if result:
                yield result
                break
        else:
            break


def decode(data, mapping, encoding):
    return ''.join(_decode_gen(data, mapping, encoding))


class Param:
    def __init__(self, names):
        self._names = names


    def parse(self, stream):
        value = self.decode(stream)
        assert value >= 0
        return str(value) if value >= len(self._names) else self._names[value]


    def format(self, text):
        try:
            value = self._names.index(text)
        except ValueError:
            value = int(text, 0)
        return self.encode(value)


class PortraitParam(Param):
    def decode(self, stream):
        data = stream.read(2)
        assert data != b'\xff\xff' # should have been special-cased.
        return int.from_bytes(data, 'little') - 257


    def encode(self, value):
        if value == -1:
            return b'\xff\xff'
        return (value + 257).to_bytes(2, 'little')


class ByteParam(Param):
    def decode(self, stream):
        return int.from_bytes(stream.read(1), 'little')


    def encode(self, value):
        return bytes([value])


def make_param(spec):
    kind, *names = spec.split('|')
    return {'PORTRAIT': PortraitParam, 'BYTE': ByteParam}[kind](names)


class TextCode:
    def __init__(self, raw, preferred_text, newline_count, params):
        self._raw = raw
        self._text = preferred_text
        self._newlines = '\n' * newline_count
        self._params = params


    def parse(self, stream):
        parsed_params = ''.join((' ' + p.parse(stream)) for p in self._params)
        return f'[{self._text}{parsed_params}]{self._newlines}'


    def format(self, values):
        if len(self._params) != len(values):
            raise ValueError('incorrect number of parameters')
        return self._raw + b''.join(
            p.format(v) for p, v in zip(self._params, values)
        )


def add_decode_mappings(mapping, raw, words, newline_count, param_specs):
    options = [word.split('=') for word in words]
    preferred = ' '.join(o[0] for o in options)
    params = [make_param(spec) for spec in param_specs]
    code = TextCode(raw, preferred, newline_count, params)
    for phrase in product(*options):
        mapping[' '.join(phrase)] = code


def parse_config_line(mapping, line):
    line = line.rstrip()
    if not line:
        return
    if line.startswith('#'):
        return
    # Let AttributeError propagate.
    raw, textcode, stars, specs = _CONFIG_PATTERN.match(line).groups()
    if raw is None:
        raw = ''
    add_decode_mappings(
        mapping, bytes.fromhex(raw), textcode.split(), len(stars), specs.split()
    )
