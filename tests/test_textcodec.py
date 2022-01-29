from dsa_extras.library.codecs import textcodec
from io import BytesIO
import pytest


@pytest.mark.parametrize('line', ['', '#', '#comment', '# comment'])
def test_skip(line):
    mapping = {}
    textcodec.parse_config_line(mapping, line)
    assert len(mapping) == 0


@pytest.mark.parametrize(
    'line', [
        '[]',
        '[foo]',
        '[foo bar baz]***',
        '[] BYTE|x|y|z',
        '010203 [example]* PORTRAIT BYTE'
    ]
)
def test_pass(line):
    mapping = {}
    textcodec.parse_config_line(mapping, line)
    assert len(mapping) == 1


@pytest.mark.parametrize(
    'line', [
        '00', # no code
        '[', # missing close bracket for code
        'one [two]', # raw value isn't hex
        '[foo bar baz]*|*', # only asterisks used for newline marker
        '[] PORTRAIT*x*y', # only pipes used for param names
        '010203 [one] [two]', # duplicate code
        '[] x|y|z', # bad param kind
        '[foo|bar|baz]' # only equal signs used for code name alternatives
    ]
)
def test_fail(line):
    mapping = {}
    with pytest.raises(Exception):
        textcodec.parse_config_line(mapping, line)


def test_complex():
    mapping = {}
    textcodec.parse_config_line(mapping, '00 [a=b=c d=e=f g=h=i]*** BYTE|x|y|z')
    assert len(mapping) == 27
    results = set(mapping.values())
    assert len(results) == 1
    result = results.pop()
    assert result.parse(BytesIO(b'\x00')) == '[a d g x]\n\n\n'
    assert result.format(('x',)) == b'\x00\x00'


def test_portrait():
    mapping = {}
    textcodec.parse_config_line(mapping, '[test] PORTRAIT')
    assert len(mapping) == 1 
    results = set(mapping.values())
    assert len(results) == 1
    result = results.pop()
    assert result.parse(BytesIO(b'\x01\x01')) == '[test 0]'
    assert result.format(('1',)) == b'\x02\x01'
    assert result.format(('-1',)) == b'\xff\xff'
    with pytest.raises(Exception):
        result.format(('0', '1')) # too many params
    with pytest.raises(Exception):
        result.format() # not enough params
    with pytest.raises(Exception):
        result.parse(BytesIO(b'\xff\xff')) # explicitly disallowed
        # so that the config file is forced to describe the special case.
