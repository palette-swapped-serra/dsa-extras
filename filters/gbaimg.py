from dsa.parsing.line_parsing import line_parser
from dsa.parsing.token_parsing import single_parser


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
    return result # leave as separate rows for PNG compression.


def _gba2png(data, width):
    return b''.join(_untile(data, width)) # FIXME


def _retile(img_raw):
    pass # TODO


def _png2gba(data):
    pass # TODO


# Filter interface.
def pack(data, params):
    # The width of the image is implicit in the image header.
    line_parser('`gbaimg` filter parameters')(params)
    return _png2gba(data) # TODO


class View:
    def __init__(self, base_get, params):
        width, = line_parser(
            '`gbaimg` filter parameters',
            single_parser('width of image in tiles', 'integer')
        )(params)
        raw = base_get(0, None)
        self._data = _gba2png(raw, width)


    def get(self, offset, size):
        data = self._data
        return data[offset:] if size is None else data[offset:offset+size]


    def params(self, size):
        return ()
