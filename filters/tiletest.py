# Extract a subset of tiles from a portrait spritesheet.
# Disassembly only.

def pack(data, params):
    pass


_TILES = [
    0,1,2,3,4,5,6,7,
    32,33,34,35,36,37,38,39,
    64,65,66,67,68,69,70,71,
    96,97,98,99,100,101,102,103,
    8,9,10,11,12,13,14,15,
    40,41,42,43,44,45,46,47,
    72,73,74,75,76,77,78,79,
    104,105,106,107,108,109,110,111
]


class View:
    def __init__(self, base_get, params):
        self._data = b''.join(
            base_get(32*t, 32)
            for t in _TILES
        )


    def get(self, offset, size):
        data = self._data
        return data[offset:] if size is None else data[offset:offset+size]


    def params(self, size):
        return ()
