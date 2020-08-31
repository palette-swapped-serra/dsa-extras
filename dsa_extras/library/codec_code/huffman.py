from dsa.parsing.line_parsing import line_parser
from dsa.parsing.token_parsing import make_parser


_parser = line_parser(
    'Huffman table entry',
    make_parser(
        'Huffman table entry data',
        ('integer', 'encoded bit sequence'),
        ('hexdump', 'decoded bytes')
    )
)


class HuffmanTable:
    def __init__(self, decode, encode):
        self._decode = decode
        self._encode = encode


    def _decode_gen(self, stream):
        read_byte = stream.read(1)[0]
        bit_offset = 0
        value = 1
        while True:
            if value in self._decode:
                encoded = self._decode[value]
                yield encoded
                if encoded[-1] == 0:
                    return
                value = 1 # clear composed value
            # append a bit to the composed value
            value = (value << 1) | ((read_byte >> bit_offset) & 1)
            bit_offset += 1
            if bit_offset == 8:
                bit_offset = 0
                read_byte = stream.read(1)[0]


    def decode(self, stream):
        return b''.join(self._decode_gen(stream))


class Loader:
    def __init__(self):
        self._decode = {}
        self._encode = {}


    def line(self, tokens):
        compressed, uncompressed = _parser(tokens)[0]
        self._decode[compressed] = uncompressed
        self._encode[uncompressed] = compressed


    def result(self):
        return HuffmanTable(self._decode, self._encode)
