from dsa.errors import UserError


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


# Filter interface.
# The unpacked version might have junk tiles at the end, if the total
# number of tiles is not divisible by the width. So we need to specify
# that as well.
pack_args = (
    'width of image in tiles', 'integer',
    'total number of tiles', 'integer'
)
# we unpack the whole data chunk, so we don't need a total tile count.
unpack_args = ('width of image in tiles', 'integer')


def pack(data, codec_lookup, tile_width, tile_count):
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


class View:
    def __init__(self, codec_lookup, data, width):
        self._raw_size, self._width = len(data), width
        self._count, self._data = _untile(data, width)


    @property
    def data(self):
        return self._data


    def pack_params(self, unpacked):
        return self._raw_size, [[str(self._width)], [str(self._count)]]
