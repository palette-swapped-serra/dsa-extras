from .nmm_common import name_stem
from .nmm_group import emit_structgroup, read_nmm
from .nmm_type import emit_types
from dsa.parsing.file_parsing import output_file
from dsa.parsing.line_parsing import INDENT
from dsa.ui.entrypoint import entry_point, param
import glob, os


def _emit_master(entries):
    yield [['align', '1'], ['count', '1']]
    # The whole group is fake, having zero size.
    # We set count=1 so disassembly only gets the pointers once.
    yield []
    yield [['MASTER']]
    for name, offset in entries:
        yield [
            INDENT, ['Address'], [name],
            ['referent', name], ['bias', hex(offset)]
        ]


@param('in_folder', 'source NMMs folder')
@param('out_folder', 'destination folder for structgroups')
@param('out_type', 'filename for types')
@entry_point('NMM to DSA enumeration file converter')
def nmm2dsa(in_folder, out_folder, out_types):
    type_data = {}
    master_entries = []
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
        output_file(
            out_file, emit_structgroup(type_data, group_data), compact=True
        )
        struct_data, chunk_offset, count, struct_size = group_data
        master_entries.append((stem, chunk_offset))
    master_file = os.path.join(out_folder, 'AllNMM.txt')
    output_file(master_file, _emit_master(master_entries), compact=True)
    output_file(out_types, emit_types(type_data), compact=True)
