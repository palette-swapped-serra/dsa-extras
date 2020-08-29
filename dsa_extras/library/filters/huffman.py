# FIXME use dynamic loading interface for codecs.
from dsa_extras.library.codecs import huffmanlogic
import io
from pathlib import Path

_HERE = Path(__file__).absolute().parent

_table = huffmanlogic.load(_HERE / '..' / 'codecs' / 'table.txt')


# Filter interface.
pack_args = () # Layout is hard-coded.
unpack_args = ()


def pack(data):
    return _table.encode(data)


class View:
    def __init__(self, data):
        stream = io.BytesIO(data)
        start = stream.tell()
        self._data = _table.decode(stream)
        self._packed_size = stream.tell() - start


    @property
    def data(self):
        return self._data


    def pack_params(self, unpacked):
        return self._packed_size, []
