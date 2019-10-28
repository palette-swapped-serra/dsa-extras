from .ea_file import parse_file
from dsa.output import output_file
import glob, os


def _compare_patterns(x):
    (name, pattern), field = x
    return ['.0123456789ABCDEF'.index(c) for c in pattern]


class StructGroup:
    def __init__(self, folder, group_name):
        self.structs = {}
        self._terminator = None
        self._id = f'{folder}:{group_name}'


    def _set_terminator(self, pattern):
        if '.' in pattern:
            raise ValueError('non-fixed field in terminator')
        if self._terminator is not None and self._terminator != pattern:
            raise ValueError(
                f'{self._id}: terminator {pattern} != {self._terminator}'
            )
        self._terminator = pattern


    def add_struct(self, name, is_terminator, is_last, fields):
        pattern = ''.join(field.fixed_dump for field in fields)
        if is_terminator:
            self._set_terminator(pattern)
            return
        key = (name, pattern)
        if key in self.structs:
            print(f'Warning: {self._id} already has {key}')
        else:
            self.structs[key] = is_last, fields


    def _tokens_gen(self):
        # While pointers can enforce alignment at the beginning of the chunk,
        # structgroups still have an `align` parameter so that structs will be
        # auto-padded on load, ensuring each struct is also aligned.
        first_line = ('', ('align', '4'),)
        if self._terminator is not None:
            first_line += (('terminator', self._terminator),)
        yield first_line
        yield ('',)
        for (name, pattern), (is_last, fields) in sorted(
            self.structs.items(), key=_compare_patterns
        ):
            yield ('', (name,), ('last',)) if is_last else ('', (name,))
            for field in fields:
                yield field.tokens()
            yield ('',)


    def tokens(self):
        return tuple(self._tokens_gen())


def parse_files(filenames):
    groups = {'FE': {}, 'FE6': {}, 'FE7': {}, 'FE8': {}}
    for filename in filenames:
        print('Parsing:', filename)
        for tags, *struct_data in parse_file(filename):
            for tag in tags:
                folder, group_name = tag
                group = groups[folder].setdefault(
                    group_name, StructGroup(folder, group_name)
                )
                group.add_struct(*struct_data)
    return groups


def process_files(filenames):
    for folder, file_data in parse_files(filenames).items():
        for outfile, struct_data in file_data.items():
            path = os.path.join(folder, f'{outfile}.txt')
            output_file(path, struct_data.tokens(), compact=True)


def process_folder(folder):
    return process_files(
        glob.glob(os.path.join(folder, '*.txt')) +
        glob.glob(os.path.join(folder, '**', '*.txt'))
    )
