import json, os, struct 


def build_table_rec(chunk, position, value):
    assert not len(chunk) % 2
    assert 0 <= position < len(chunk)
    left, right = chunk[position:position+2]
    if right >= 0x8000:
        size = (left.bit_length() + 7) // 8
        pattern = left.to_bytes(size, 'little').hex()
        if not pattern:
            pattern = '00' # null terminator
        yield (value, pattern)
    else:
        yield from build_table_rec(chunk, left*2, value << 1)
        yield from build_table_rec(chunk, right*2, (value << 1) | 1)


def main(input_name, output_name, start, end):
    with open(input_name, 'rb') as f:
        raw = f.read()[start:end]
        pairs = struct.unpack(f'<{len(raw)//2}H', raw)
    
    with open(output_name, 'w') as f:
        for value, pattern in sorted(build_table_rec(pairs, len(pairs) - 2, 1)):
            f.write(f'{value}:{pattern}\n')


if __name__ == '__main__':
    main(os.environ['FE7'], 'table.txt', 0xb7d71c, 0xb808a8)
