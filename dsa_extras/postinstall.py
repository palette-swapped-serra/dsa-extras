from pathlib import Path
from dsa.ui.usefiles import use_files
from epmanager import entrypoint


_HERE = Path(__file__).absolute().parent


@entrypoint(
    name='dsa-extras-postinstall',
    description='make extras library available to DSA'
)
def install_library():
    use_files(str(_HERE / 'library'))
