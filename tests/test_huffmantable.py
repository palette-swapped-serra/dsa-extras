from dsa_extras.library.codecs import huffmanlogic
import pytest
import io, os


@pytest.mark.parametrize(
    ('position', 'result'), [
        (0xaeae8c, b'\x00'),
        (0xaeae8d, b'Yes\x1f\x00'),
        (0xaeae91, b'No\x00')
    ]
)
def test_huffmantable(position, result):
    table = huffmanlogic.load('dsa_extras/library/codecs/table.txt')
    with open(os.environ['FE7'], 'rb') as f:
        data = f.read()
    stream = io.BytesIO(data)
    stream.seek(position)
    assert table.decode(stream) == result
