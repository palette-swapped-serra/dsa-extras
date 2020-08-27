import os, re


_forbidden = re.compile('[\[\],:@{}<>]')


def words(name):
    return _forbidden.sub(' ', name).split()


def normalize(name):
    """Take out characters with any special meaning"""
    return ' '.join(words(name))


def number(name, i):
    return f'{name} {i}' if ' ' in name else f'{name}{i}'


def file_contents(filename):
    with open(filename) as f:
        for line in f:
            line = line.partition('#')[0].strip()
            if line:
                yield line


def in_folder(ref, path):
    return os.path.abspath(os.path.join(os.path.split(ref)[0], path))


def name_stem(filename):
    return os.path.splitext(os.path.split(filename)[1])[0]
