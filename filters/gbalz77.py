from dsa.errors import UserError
from io import BytesIO


class BAD_LZ77_HEADER(UserError):
    """LZ77 source data didn't start with a 0x10 byte"""


class BAD_LZ77_DATA(UserError):
    """Corruption detected at end of LZ77 data"""


_CODE_SIZE = 2 # 2-byte codes
_MIN_ENCODED = 3 # minimum number of bytes represented by encoded chunk.
_LENGTH_SIZE = 4 # number of bits devoted to the size of an encoded chunk.
# Values used in binary search for the encoded chunk size.
_ENCODED_STEPS = [1 << i for i in reversed(range(_LENGTH_SIZE))]
_LOOKBEHIND_SIZE = 8 * _CODE_SIZE - _LENGTH_SIZE
# number of bits devoted to the lookbehind position.
_LOOKBEHIND_MASK = (1 << _LOOKBEHIND_SIZE) - 1
_MAX_LOOKBEHIND = _LOOKBEHIND_MASK + 1


def _encode(size, lookbehind):
    # The stored lookbehind value is 1 less than the actual distance.
    # Subtract 1 on encoding and add 1 back on decoding.
    x = ((size - _MIN_ENCODED) << _LOOKBEHIND_SIZE) | (lookbehind - 1)
    return x.to_bytes(_CODE_SIZE, 'big')


def _decode(code):
    x = int.from_bytes(code, 'big')
    return (x >> _LOOKBEHIND_SIZE) + _MIN_ENCODED, (x & _LOOKBEHIND_MASK) + 1


def _find(data, start, at, size):
    sought = data[at:at+size]
    # The GBA encoder won't encode a match with a lookbehind distance of 1;
    # thus a compressed bitmap of all zeroes has two literal bytes before the
    # encoding pairs, and F0 01 sequences instead of F0 00.
    # The `rfind` end point is limited to ensure compatible compressed output.
    # Additionally, matches of the desired length need to be forced to fail
    # if there is not enough data to match.
    return data.rfind(sought, start, at+size-2) if len(sought) == size else -1


def _search(data, position):
    start = max(0, position - _MAX_LOOKBEHIND)
    # Try to match data[position:position+N] in data[:start+N], and
    # binary search 3..18 to find the maximal value of N. We prefer a match
    # that minimizes the lookbehind distance, so we use .rfind().
    size = 3
    found_at = _find(data, start, position, size)
    if found_at == -1:
        # If there isn't a match of at least 3, return a single unencoded byte.
        return 1, data[position:position+1]
    for step in _ENCODED_STEPS:
        candidate = _find(data, start, position, size + step)
        if candidate != -1:
            size += step
            found_at = candidate
    return size, _encode(size, position - found_at)


def _encoded_chunks_gen(data):
    position = 0
    while position < len(data):
        size, encoding = _search(data, position)
        yield encoding
        position += size


def _decompress(data):
    stream = BytesIO(data)
    read = stream.read
    get = lambda: read(1)[0]
    BAD_LZ77_HEADER.require(get() == 0x10)
    size = int.from_bytes(read(3), 'little')
    result = bytearray(0)
    # When we reset the flags, we set the 0x100 bit as a sentinel.
    # When that bit has been left-shifted into the 0x10000 place, refill.
    flag_buffer = 0x10000
    while len(result) < size:
        if flag_buffer & 0x10000:
            flag_buffer = 0x100 | get()
        # we can immediately check the flag.
        flag_buffer <<= 1
        if flag_buffer & 0x100: # current flag is set; read an encoded pair.
            code = read(2)
            chunk_size, lookbehind = _decode(code)
            match_location = len(result) - lookbehind
            # Can't just extend with a slice, because the source may overlap
            # the destination deliberately.
            for i in range(chunk_size):
                result.append(result[match_location + i])
        else:
            result.append(get())
    BAD_LZ77_DATA.require(len(result) == size)
    consumed = stream.tell()
    return (consumed + (-consumed % 4)), bytes(result)


# Filter interface.
pack_args = ()
unpack_args = ()


def pack(data):
    # header
    result = bytearray(((len(data) << 8) | 0x10).to_bytes(4, 'little'))
    flag_bit = 1
    for chunk in _encoded_chunks_gen(data):
        if flag_bit == 1: # about to start the next chunk
            flag_bit = 128
            flag_position = len(result)
            result.append(0) # byte to store the flags in
        else:
            flag_bit >>= 1
        result.extend(chunk)
        if len(chunk) == 2:
            result[flag_position] |= flag_bit
    result.extend(bytes(-len(result) % 4)) # padding
    return bytes(result)


class View:
    """View into the uncompressed version of LZ77-compressed data."""
    def __init__(self, data):
        self._packed_size, self._data = _decompress(data)


    @property
    def data(self):
        return self._data


    def pack_params(self, unpacked):
        return self._packed_size, []
