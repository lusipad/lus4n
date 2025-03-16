# PyInstaller hook for luaparser
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Make sure all submodules are included
hiddenimports = collect_submodules('luaparser')

# Include any data files
datas = collect_data_files('luaparser')
