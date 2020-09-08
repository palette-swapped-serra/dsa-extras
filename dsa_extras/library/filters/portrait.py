# Portrait spritesheets generally have a horizontal striped pattern in
# the lower right (when viewed at the standard 32 tile width). We reproduce
# this in the tilemap, even though it's garbage in-game, to ensure that
# round-trip disassembly/assembly tests pass.
_TEXT_TILEMAP = [
    '00 00 00 01 02 03 04 05 06 07 00 00 00 00 00 00',
    '00 00 20 21 22 23 24 25 26 27 00 00 00 00 00 00',
    '00 00 40 41 42 43 44 45 46 47 00 00 00 00 00 00',
    '00 00 60 61 62 63 64 65 66 67 00 00 00 00 00 00',
    '00 00 08 09 0A 0B 0C 0D 0E 0F 00 00 00 00 00 00',
    '00 00 28 29 2A 2B 2C 2D 2E 2F 00 00 00 00 00 00',
    '14 15 48 49 4A 4B 4C 4D 4E 4F 16 17 18 19 1A 1B',
    '34 35 68 69 6A 6B 6C 6D 6E 6F 36 37 38 39 3A 3B',
    '54 55 10 11 12 13 50 51 52 53 56 57 58 59 5A 5B',
    '74 75 30 31 32 33 70 71 72 73 76 77 78 79 7A 7B',
    '00 00 00 00 00 00 00 00 00 00 00 00 1C 1D 1E 1F',
    '00 00 00 00 00 00 00 00 00 00 00 00 3C 3D 3E 3F',
    '00 00 00 00 00 00 00 00 00 00 00 00 5C 5D 5E 5F',
    '00 00 00 00 00 00 00 00 00 00 00 00 7C 7D 7E 7F'
]
_UNPACK_MAP = [int(x, 16) for line in _TEXT_TILEMAP for x in line.split()]
_PACK_MAP = [_UNPACK_MAP.index(x) for x in range(0x80)]


def _tiles(data, mapping):
    return b''.join(data[32*t:32*(t+1)] for t in mapping)


# Filter interface.
pack_args = () # Layout is hard-coded.
unpack_args = ()


def pack(codec_lookup, data):
    return _tiles(data, _PACK_MAP)


class View:
    def __init__(self, codec_lookup, data):
        self._raw_size, self._data = len(data), _tiles(data, _UNPACK_MAP)


    @property
    def data(self):
        return self._data


    def pack_params(self, unpacked):
        return self._raw_size, []
