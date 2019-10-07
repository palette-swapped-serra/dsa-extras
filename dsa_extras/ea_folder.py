from .ea_file import parse_file
from dsa.parsing.line_parsing import output_line
import glob, os


class StructGroup:
    def __init__(self):
        self.structs = {}
        self._terminator = None


    def _set_terminator(self, pattern):
        if '.' in pattern:
            raise ValueError('non-fixed field in terminator')
        if self._terminator is not None and self._terminator != pattern:
            raise ValueError(
                'terminator value conflict: {pattern} vs {self._terminator}'
            )
        self._terminator = pattern


    def add_struct(self, name, is_terminator, fields):
        pattern = ''.join(field.fixed_dump for field in fields)
        if is_terminator:
            self._set_terminator(pattern)
            return
        key = (name, pattern)
        if key in self.structs:
            print('Warning: ignoring duplicate formatting for struct')
        else:
            self.structs[key] = fields


    def _tokens_gen(self):
        first_line = (('align', '4'), ('endian', 'little'))
        if self._terminator is not None:
            first_line += (('terminator', self._terminator),)
        yield first_line
        for (name, pattern), fields in sorted(self.structs.items()):
            yield (name,),
            for field in fields:
                yield field.tokens()


    def tokens(self):
        return tuple(self._tokens_gen())


def parse_files(filenames):
    groups = {'FE': {}, 'FE6': {}, 'FE7': {}, 'FE8': {}}
    for filename in filenames:
        print('Parsing:', filename)
        for struct_name, tags, is_terminator, fields in parse_file(filename):
            for tag in tags:
                folder, group_name = tag
                group = groups[folder].setdefault(group_name, StructGroup())
                group.add_struct(struct_name, is_terminator, fields)
    return groups


def _write_file(filename, lines):
    with open(filename, 'w') as f:
        for line in lines:
            output_line(f, *line)


def process_files(filenames):
    for folder, file_data in parse_files(filenames).items():
        for outfile, struct_data in file_data.items():
            path = os.path.join(folder, f'{outfile}_group.txt')
            _write_file(path, struct_data.tokens())


def process_folder(folder):
    return process_files(
        glob.glob(os.path.join(folder, '*.txt')) +
        glob.glob(os.path.join(folder, '**', '*.txt'))
    )
