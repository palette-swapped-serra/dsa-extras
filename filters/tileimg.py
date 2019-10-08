from dsa.errors import UserError
from dsa.parsing.line_parsing import line_parser
from dsa.parsing.token_parsing import single_parser


class BAD_PALETTE(UserError):
    """invalid palette index in bitmap data"""


# Convert 4bpp gba to 8bpp bitmap (palette indices 16..255 unused).
def _untile(gba_raw, tile_width):
    tile_count, remainder = divmod(len(gba_raw), 32)
    assert not remainder
    row_count = (tile_count + tile_width - 1) // tile_width
    result = [
        bytearray(tile_width * 8)
        for _ in range(row_count * 8)
    ]
    for i, byte in enumerate(gba_raw):
        tile, tile_offset = divmod(i, 32)
        tile_row, tile_column = divmod(tile, tile_width)
        inner_row, inner_colpair = divmod(tile_offset, 4)
        row = tile_row * 8 + inner_row
        column = tile_column * 8 + inner_colpair * 2
        result[row][column] = byte & 0xF
        result[row][column + 1] = byte >> 4
    return tile_count, b''.join(result)


def _retile(data, tile_width, tile_count):
    result = bytearray()
    for i in range(tile_count):
        tile_row, tile_column = divmod(i, tile_width)
        for row in range(tile_row*8, (tile_row+1)*8):
            for column in range(tile_column*8, (tile_column+1)*8, 2):
                index = row * tile_width * 8 + column
                x, y = data[index:index+2]
                BAD_PALETTE.require(x < 16 and y < 16)
                result.append(x | (y << 4))
    return bytes(result)


# Filter interface.
def pack(data, params):
    # There may be junk tiles at the end of the last row, so we must have
    # an explicit `count` value passed as well.
    width, count = line_parser(
        '`tileimg` filter parameters',
        single_parser('width of image in tiles', 'integer'),
        single_parser('total number of tiles', 'integer')
    )(params)
    return _retile(data, width, count) # TODO


class View:
    def __init__(self, base_get, params):
        # When disassembling, we infer the tile count from the amount of
        # raw tile bitmap data.
        self._width, = line_parser(
            '`gbaimg` filter parameters',
            single_parser('width of image in tiles', 'integer')
        )(params)
        raw = base_get(0, None)
        self._count, self._data = _untile(raw, self._width)


    def get(self, offset, size):
        data = self._data
        return data[offset:] if size is None else data[offset:offset+size]


    def params(self, size):
        return ((str(self._width),), (str(self._count),))
