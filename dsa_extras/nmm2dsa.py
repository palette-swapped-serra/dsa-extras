from .nmm_common import name_stem
from .nmm_group import emit_structgroup, read_nmm
from .nmm_type import emit_types
from dsa.parsing.file_parsing import output_file
from dsa.ui.entrypoint import entry_point, param
import glob, os


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
        output_file(
            out_file, emit_structgroup(type_data, group_data), compact=True
        )
    output_file(out_types, emit_types(type_data), compact=True)
