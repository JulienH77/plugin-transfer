"""Build the QGIS plugin archive from the repository root."""
from configparser import ConfigParser
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parent
plugin = root / 'plugin_transfer'
metadata = ConfigParser(interpolation=None)
metadata.read(plugin / 'metadata.txt', encoding='utf-8')
version = metadata['general']['version']
with ZipFile(root / f'Plugin_Transfer_{version}.zip', 'w', ZIP_DEFLATED) as archive:
    for source in sorted(plugin.rglob('*')):
        if source.is_file() and '__pycache__' not in source.parts and source.suffix not in {'.pyc', '.pyo'}:
            archive.write(source, source.relative_to(root))
