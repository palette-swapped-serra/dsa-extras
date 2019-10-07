from dsa.parsing.line_parsing import line_parser
from dsa.parsing.token_parsing import single_parser
from dsa.errors import UserError


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
_MAX_LOOKBEHIND = _LOOKBEHIND_MASK # +1?


def _encode(size, lookbehind):
    value = ((size - _MIN_ENCODED) << _LOOKBEHIND_SIZE) | lookbehind
    return value.to_bytes(_CODE_SIZE, 'big')


def _decode(code):
    value = int.from_bytes(code, 'big')
    return (value >> _LOOKBEHIND_SIZE) + _MIN_ENCODED, value & _LOOKBEHIND_MASK


def _find(data, start, at, size):
    sought = data[at:at+size]
    return data.rfind(sought, start, at+size-1) if len(sought) == size else -1


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


# The data we compress will always be the entirety of some bytes-like object.
# However, we might *de*compress only a subsequence of data.
def _compress(data):
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


def _decompress(get):
    position = 0
    def next_bytes(amount):
        nonlocal position
        result = get(position, amount)
        position += amount 
        return result
    def next_byte():
        return next_bytes(1)[0]
    BAD_LZ77_HEADER.require(next_byte() == 0x10)
    size = int.from_bytes(next_bytes(3), 'little')
    result = bytearray(0)
    # When we reset the flags, we set the 0x100 bit as a sentinel.
    # When that bit has been left-shifted into the 0x10000 place, refill.
    flag_buffer = 0x10000
    while len(result) < size:
        if flag_buffer & 0x10000:
            flag_buffer = 0x100 | next_byte()
        # we can immediately check the flag.
        flag_buffer <<= 1
        if flag_buffer & 0x100: # current flag is set; read an encoded pair.
            code = next_bytes(2)
            chunk_size, lookbehind = _decode(code)
            match_location = len(result) - lookbehind
            # Can't just extend with a slice, because the source may overlap
            # the destination deliberately.
            for i in range(chunk_size):
                result.append(result[match_location + i])
        else:
            result.append(next_byte())
    BAD_LZ77_DATA.require(len(result) == size)
    return bytes(result)


# Filter interface.
def pack(data, params):
    # Ensure no parameters are passed, as none are accepted.
    line_parser('`gbalz77` filter parameters')(params)
    return _compress(data)


class View:
    """View into the uncompressed version of LZ77-compressed data."""
    def __init__(self, base_get, params):
        # No parameters are accepted.
        line_parser('`gbalz77` filter parameters')(params)
        # Eagerly decompress the data, then index into it.
        self._data = _decompress(base_get)


    def get(self, offset, size):
        data = self._data
        return data[offset:] if size is None else data[offset:offset+size]


    def params(self, size):
        return ()