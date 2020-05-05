import json, struct, sys


def build_table_rec(chunk, position, result, value):
    assert not len(chunk) % 2
    assert 0 <= position < len(chunk)
    left, right = chunk[position:position+2]
    if right >= 0x8000:
        size = (left.bit_length() + 7) // 8
        result[value] = list(left.to_bytes(size, 'little'))
    else:
        build_table_rec(chunk, left*2, result, value << 1)
        build_table_rec(chunk, right*2, result, (value << 1) | 1)


def main(input_name, output_name, start, end):
    with open(input_name, 'rb') as f:
        raw = f.read()[start:end]
        pairs = struct.unpack(f'<{len(raw)//2}H', raw)
    result = {}
    build_table_rec(pairs, len(pairs) - 2, result, 1)
    with open(output_name, 'w') as f:
        json.dump(result, f, sort_keys=True, indent=4)


if __name__ == '__main__':
    input_name, output_name, start, end = sys.argv[1:]
    main(input_name, output_name, int(start, 0), int(end, 0))
