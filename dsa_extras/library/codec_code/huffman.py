from dsa.parsing.file_parsing import load_files
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
    def __init__(self):
        self._decode = {}
        self._encode = {}


    def register(self, encoded, decoded):
        self._decode[encoded] = decoded
        self._encode[decoded] = encoded


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


class HuffmanTableLoader:
    def __init__(self):
        self._table = HuffmanTable()


    def line(self, indent, tokens):
        if indent:
            raise ValueError('Unindented lines only pls')
        self._table.register(*_parser(tokens)[0])


    def result(self):
        return self._table 


def load(filename):
    return load_files([filename], HuffmanTableLoader)
