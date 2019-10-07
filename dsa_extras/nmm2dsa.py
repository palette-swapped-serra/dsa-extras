from .nmm_common import name_stem
from .nmm_group import emit_structgroup, read_nmm
from .nmm_type import emit_types
from dsa.parsing.line_parsing import output_line
from dsa.ui.entrypoint import entry_point, param
import glob, os


def _write_file(filename, lines):
    with open(filename, 'w') as f:
        for line in lines:
            output_line(f, *line)


@param('in_folder', 'source NMMs folder')
@param('out_folder', 'destination folder for structgroups')
@param('out_type', 'filename for types')
@entry_point('NMM to DSA enumeration file converter')
def nmm2dsa(in_folder, out_folder, out_types):
    type_data = {}
    # Process each file first to accumulate type data,
    # then write out each output.
    all_group_data = [
        (name_stem(nmm), read_nmm(type_data, nmm))
        # TODO: handle folders recursively and mirror the folder structure
        # in the `out_folder`.
        for nmm in glob.glob(os.path.join(in_folder, '*.nmm'))
    ]
    for stem, group_data in all_group_data:
        out_file = os.path.join(out_folder, f'{stem}.txt')
        _write_file(out_file, emit_structgroup(type_data, group_data))
    _write_file(out_types, emit_types(type_data))
