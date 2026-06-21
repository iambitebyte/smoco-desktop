# PyInstaller hook for webrtcvad
# This hook bypasses the problematic copy_metadata call

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all submodules
hiddenimports = collect_submodules('webrtcvad')

# Collect data files if any
datas = collect_data_files('webrtcvad')
