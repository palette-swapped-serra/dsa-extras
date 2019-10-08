from dsa.errors import UserError, MappingError
from dsa.parsing.line_parsing import line_parser
from dsa.parsing.token_parsing import single_parser
import zlib


# Most of these errors should never be seen by a user attempting to supply
# valid PNGs in good faith.
class BAD_PNG_HEADER(UserError):
    """Not a valid PNG file (PNG signature not detected)"""


class PNG_EOF(UserError):
    """Unexpected end of PNG file"""


class PNG_CHECKSUM(UserError):
    """PNG file contained invalid checksum for `{chunk}` chunk"""


class BAD_PLTE(UserError):
    """PNG file has invalid palette (not a multiple of 3 bytes)"""


class BAD_IEND(UserError):
    """PNG file corrupt at end (bad IEND chunk)"""


class UNSUPPORTED_PNG(UserError):
    """PNG file not supported (must be 8bpp palettized, non-interlaced)"""


class BAD_FILTER(MappingError):
    """PNG file had invalid image data (filter method = `{key}`)"""


class DUPLICATE_CHUNK(UserError):
    """PNG file contains disallowed duplicate `{chunk}` chunk"""


class MISSING_CHUNK(MappingError):
    """PNG file missing `{key}` chunk"""


class BAD_PALETTE_DATA(UserError):
    """Palette data must be a multiple of 32 bytes long"""


class TOO_MANY_PALETTES(UserError):
    """Too many palettes (max 16)"""


class BAD_BITMAP_DATA(UserError):
    """Bitmap data must be a multiple of 64 bytes long"""


def _num(quad):
    return int.from_bytes(quad, 'big')


def _quad(value):
    return value.to_bytes(4, 'big')


def _chunk(name, data):
    chunk = name + data
    return _quad(len(data)) + chunk + _quad(zlib.crc32(chunk))


def _compress(rows):
    # No filters are applied by the compressor.
    # We need to prepend a 0 filter-type byte to the beginning of each row.
    return zlib.compress(b'\x00' + b'\x00'.join(rows))


_PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


def _to_png(rows, plte):
    # rows = 8bpp raw bitmap data, as a list of bytes objects
    # palette = 48-byte chunk specifying 16 palette indices
    result = bytearray(_PNG_SIGNATURE)
    result.extend(_chunk(
        b'IHDR', 
        len(rows[0]).to_bytes(4, 'big') + # width
        len(rows).to_bytes(4, 'big') + # height
        bytes([8, 3, 0, 0, 0]) # bit depth, palettized, not interlaced
    ))
    result.extend(_chunk(b'PLTE', plte))
    result.extend(_chunk(b'IDAT', _compress(rows)))
    result.extend(_chunk(b'IEND', b''))
    return bytes(result)


def _png_chunk_gen(raw):
    position = 0
    def read(amount):
        nonlocal position
        result = raw[position:position+amount]
        position += amount
        return result
    header = read(8)
    BAD_PNG_HEADER.require(header == _PNG_SIGNATURE)
    while True:
        size = read(4)
        if not size:
            break
        size = int.from_bytes(size, 'big')
        name = read(4)
        data = read(size)
        checksum = read(4)
        PNG_EOF.require(len(checksum) == 4)
        PNG_CHECKSUM.require(_quad(zlib.crc32(name + data)) == checksum, chunk=name)
        yield (name, data)


def _validate(plte, iend):
    BAD_PLTE.require(len(plte) % 3 == 0)
    BAD_IEND.require(iend == b'')


def _parse_header(ihdr):
    width, height = _num(ihdr[:4]), _num(ihdr[4:8])
    UNSUPPORTED_PNG.require(ihdr[8:] == b'\x08\x03\x00\x00\x00')
    return width, height


def _process_scanline(method, prev_line, this_line):
    left = 0
    result = bytearray()
    for up, this, diag in zip(prev_line, this_line, bytes(1) + prev_line[:-1]):
        average = (left + up) // 2
        reference = left + up - diag
        paeth = min((left, up, diag), key = lambda x: abs(reference - x))
        prediction = BAD_FILTER.get({
            0: 0, 1: left, 2: up, 3: average, 4: paeth
        }, method)
        # PNG spec says we do unsigned math throughout here.
        left = (this + prediction) & 0xff
        result.append(left)
    return bytes(result)


def _scanlines(width, height, idat):
    data = zlib.decompress(idat)
    bytes_per_line = width + 1
    prev_line = b'\x00' * width
    for line_start in range(0, height*bytes_per_line, bytes_per_line):
        method = data[line_start]
        this_line = data[line_start+1:line_start+bytes_per_line]
        this_line = _process_scanline(method, prev_line, this_line)
        yield this_line
        prev_line = this_line


def _png_data(raw):
    result = {}
    for name, data in _png_chunk_gen(raw):
        if name not in result:
            result[name] = data
            continue
        # concatenate IDAT chunks, refuse duplicates of anything else.
        DUPLICATE_CHUNK.require(name == b'IDAT', chunk=name)
        result[name] += data
    plte = MISSING_CHUNK.get(result, b'PLTE')
    iend = MISSING_CHUNK.get(result, b'IEND')
    _validate(plte, iend)
    width, height = _parse_header(MISSING_CHUNK.get(result, b'IHDR'))
    idat = MISSING_CHUNK.get(result, b'IDAT')
    return plte, idat, width, height


def rgb_to_xy(r, g, b):
    value = ((r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10))
    return value.to_bytes(2, 'little')


def xy_to_rgb(x, y):
    return bytes([(x & 0x1f), ((x >> 5) | (y << 3) & 3), ((y >> 2) & 0x1f)])


def _compact_palette(plte):
    return b''.join(rgb_to_xy(r, g, b) for r, g, b in zip(*([iter(plte)] * 3)))


def _expand_palette(tile):
    return b''.join(xy_to_rgb(x, y) for x, y in zip(*([iter(tile)] * 3)))


_DUMMY_ROWS = [
    b''.join(bytes([x]) * 16 for x in range(16))
] * 16


_DUMMY_PLTE = b''.join(bytes([x]) * 3 for x in range(0, 0x11 * 16, 0x11))


def _unpack(data, width):
    if width is None:
        count, remainder = divmod(len(data), 32)
        BAD_PALETTE_DATA.require(remainder == 0)
        # Interpret as palette data.
        TOO_MANY_PALETTES.require(count <= 16)
        plte = _expand_palette(data)
        rows = _DUMMY_ROWS * len(palettes)
    else:
        size = len(data)
        # Data should already be expanded to 8bpp, with 8x8 tiles arranged.
        BAD_BITMAP_DATA.require(size % 64 == 0)
        stride = 8 * width
        plte = _DUMMY_PLTE
        rows = [data[i:i+stride] for i in range(0, size, stride)]
    return _to_png(rows, plte)


# Filter interface.
def pack(data, params):
    use_palette, = line_parser(
        '`gbaimg` filter parameters',
        single_parser(
            'palette flag', {None: False, 'true': True, 'false': False}
        )
    )(params)
    plte, idat, width, height = _png_data(data)
    return _compact_palette(plte) if use_palette else b''.join(
        _scanlines(width, height, idat)
    )


class View:
    def __init__(self, base_get, params):
        self._width, = line_parser(
            '`gbaimg` filter parameters',
            single_parser('width of image in tiles', 'integer?')
        )(params)
        raw = base_get(0, None)
        self._data = _unpack(base_get(0, None), self._width)


    def get(self, offset, size):
        data = self._data
        return data[offset:] if size is None else data[offset:offset+size]


    def params(self, size):
        return [[str(self._width is None).lower()]]
