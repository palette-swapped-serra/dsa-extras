import io


# Filter interface.
pack_args = ('codec name', 'string')
unpack_args = ('codec name', 'string')


def pack(codec_lookup, data, codec_name):
    return codec_lookup[codec_name].encode(data)


class View:
    def __init__(self, codec_lookup, data, codec_name):
        self._name = codec_name
        stream = io.BytesIO(data)
        start = stream.tell()
        self._data = codec_lookup[codec_name].decode(stream)
        self._packed_size = stream.tell() - start


    @property
    def data(self):
        return self._data


    def pack_params(self, unpacked):
        return self._packed_size, [[str(self._name)]]
