# SPDX-License-Identifier: GPL-2.0-or-later
import json
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path, PureWindowsPath
from configparser import ConfigParser
from qgis.core import Qgis, QgsApplication, QgsSettings
from qgis.PyQt.QtWidgets import (QAction, QDialog, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox, QCheckBox, QTextEdit)
from qgis.PyQt.QtCore import Qt

VALID = re.compile(r'^[A-Za-z_][A-Za-z_0-9]*$')

def plugins_dir():
    return Path(QgsApplication.qgisSettingsDirPath()) / 'python' / 'plugins'

def installed():
    root = plugins_dir()
    result = []
    if root.exists():
        for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
            if p.is_dir() and not p.is_symlink() and VALID.fullmatch(p.name) and (p/'metadata.txt').is_file() and (p/'__init__.py').is_file():
                cp = ConfigParser(interpolation=None)
                try:
                    cp.read(str(p/'metadata.txt'), encoding='utf-8-sig')
                    name = cp.get('general', 'name', fallback=p.name)
                    version = cp.get('general', 'version', fallback='?')
                except Exception:
                    name, version = p.name, '?'
                result.append((p.name, name, version))
    return result

class PluginTransfer:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
    def initGui(self):
        self.action = QAction('Plugin Transfer - Migrer les extensions', self.iface.mainWindow())
        self.action.triggered.connect(self.open)
        self.iface.addPluginToMenu('Plugin Transfer', self.action)
    def unload(self):
        if self.action:
            self.iface.removePluginMenu('Plugin Transfer', self.action)
    def open(self):
        dlg = QDialog(self.iface.mainWindow())
        dlg.setWindowTitle('Plugin Transfer 1.0.0')
        dlg.resize(650, 570)
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel('Extensions Python du profil actif (cochées = incluses dans la sauvegarde)'))
        lst = QListWidget()
        lay.addWidget(lst)
        settings = QgsSettings()
        for key, name, ver in installed():
            enabled = settings.value('/PythonPlugins/' + key, False, type=bool)
            item = QListWidgetItem('{}  |  {}  |  v{}  |  {}'.format(key, name, ver, 'activée' if enabled else 'désactivée'))
            item.setData(Qt.UserRole, key)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked if key == 'plugin_transfer' else Qt.Checked)
            lst.addItem(item)
        lay.addWidget(QLabel('La sélection concerne l’export, pas l’état activé/désactivé.'))
        restore_states = QCheckBox('Restaurer les états activé/désactivé lors de l’import')
        restore_states.setChecked(True)
        lay.addWidget(restore_states)
        overwrite = QCheckBox('Remplacer les extensions existantes (sauvegarde automatique avant remplacement)')
        lay.addWidget(overwrite)
        log = QTextEdit()
        log.setReadOnly(True)
        lay.addWidget(log)
        export_btn = QPushButton('Exporter les extensions sélectionnées vers ZIP')
        import_btn = QPushButton('Importer une sauvegarde ZIP')
        lay.addWidget(export_btn)
        lay.addWidget(import_btn)
        export_btn.clicked.connect(lambda: self.export(lst, log))
        import_btn.clicked.connect(lambda: self.restore(log, overwrite.isChecked(), restore_states.isChecked()))
        dlg.exec_()
    def export(self, lst, log):
        keys = [lst.item(i).data(Qt.UserRole) for i in range(lst.count()) if lst.item(i).checkState() == Qt.Checked]
        if not keys:
            QMessageBox.warning(None, 'Plugin Transfer', 'Aucune extension sélectionnée.')
            return
        path, _ = QFileDialog.getSaveFileName(None, 'Exporter les extensions', 'qgis_plugins_backup.zip', 'Archives ZIP (*.zip)')
        if not path:
            return
        if not path.lower().endswith('.zip'):
            path += '.zip'
        root = plugins_dir()
        settings = QgsSettings()
        manifest = {'format': 'plugin-transfer-v2', 'qgis_version': Qgis.QGIS_VERSION, 'plugins': []}
        try:
            output = Path(path).resolve()
            if any((root / key).resolve() in output.parents for key in keys):
                raise ValueError('Enregistrez la sauvegarde en dehors des extensions sélectionnées.')
            with tempfile.TemporaryDirectory(dir=output.parent) as temp:
                temporary_path = Path(temp) / 'backup.zip'
                with zipfile.ZipFile(temporary_path, 'w', zipfile.ZIP_DEFLATED) as z:
                    for key in keys:
                        folder = root/key
                        if not folder.is_dir():
                            continue
                        manifest['plugins'].append({'id': key, 'enabled': settings.value('/PythonPlugins/'+key, False, type=bool)})
                        for base, dirs, files in os.walk(str(folder)):
                            dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', '.svn')]
                            for file in files:
                                source = Path(base)/file
                                if source.is_symlink() or file.endswith(('.pyc', '.pyo')):
                                    continue
                                rel = source.relative_to(root).as_posix()
                                z.write(str(source), 'plugins/'+rel)
                    z.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
                os.replace(temporary_path, output)
            log.append('Export terminé : {} extension(s) -> {}'.format(len(manifest['plugins']), path))
            QMessageBox.information(None, 'Plugin Transfer', 'Sauvegarde créée avec succès.')
        except Exception as exc:
            log.append('ERREUR export : {}'.format(exc))
            QMessageBox.critical(None, 'Plugin Transfer', str(exc))
    def restore(self, log, overwrite, restore_states):
        path, _ = QFileDialog.getOpenFileName(None, 'Importer la sauvegarde', '', 'Archives ZIP (*.zip)')
        if not path:
            return
        root = plugins_dir()
        try:
            with zipfile.ZipFile(path) as z:
                entries = z.infolist()
                if len(entries) > 100000 or sum(i.file_size for i in entries) > 4 * 1024**3:
                    raise ValueError('Archive trop volumineuse (100 000 entrées ou 4 Gio décompressés).')
                if z.getinfo('manifest.json').file_size > 8 * 1024**2:
                    raise ValueError('Manifeste trop volumineux.')
                manifest = json.loads(z.read('manifest.json').decode('utf-8'))
                if manifest.get('format') != 'plugin-transfer-v2':
                    raise ValueError('Archive non compatible : format de sauvegarde Plugin Transfer requis.')
                records = manifest.get('plugins', [])
                ids = [r['id'] for r in records]
                if len({k.casefold() for k in ids}) != len(ids) or any(not VALID.fullmatch(k) for k in ids):
                    raise ValueError('Identifiants invalides ou en doublon.')
                names = z.namelist()
                if len({n.casefold() for n in names}) != len(names):
                    raise ValueError('Chemins en doublon dans la sauvegarde.')
                for info in z.infolist():
                    name = info.filename
                    parts = (name[:-1] if name.endswith('/') else name).split('/')
                    if any(part in ('', '.', '..') or part.endswith((' ', '.'))
                           or PureWindowsPath(part).is_reserved()
                           or any(ord(c) < 32 or c in '<>:"|?*' for c in part)
                           for part in parts):
                        raise ValueError('Chemin de fichier invalide : ' + name)
                    if name.startswith('/') or '\\' in name or '..' in parts or (name != 'manifest.json' and (len(parts) < 3 or parts[0] != 'plugins' or parts[1] not in ids)):
                        raise ValueError('Chemin dangereux dans l’archive : '+name)
                    if (info.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError('Lien symbolique interdit : '+name)
                for key in ids:
                    for required in ('metadata.txt', '__init__.py'):
                        if 'plugins/{}/{}'.format(key, required) not in names:
                            raise ValueError('Fichier manquant : {}/{}'.format(key, required))
                todo = [k for k in ids if overwrite or not (root/k).exists()]
                if not todo:
                    QMessageBox.information(None, 'Plugin Transfer', 'Toutes les extensions existent déjà. Cochez le remplacement pour les écraser.')
                    return
                if QMessageBox.question(None, 'Confirmer', 'Importer uniquement une sauvegarde de confiance. Restaurer {} extension(s) ?\nUn redémarrage de QGIS sera nécessaire.'.format(len(todo)), QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                    return
                root.mkdir(parents=True, exist_ok=True)
                backup_root = root.parent / ('plugin_transfer_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
                restored = []
                with tempfile.TemporaryDirectory(dir=root.parent) as temp:
                    stage = Path(temp)
                    for key in todo:
                        target = stage/key
                        target.mkdir()
                        for info in z.infolist():
                            prefix = 'plugins/'+key+'/'
                            if not info.filename.startswith(prefix) or info.is_dir():
                                continue
                            rel = info.filename[len(prefix):]
                            dest = target/rel
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            with z.open(info) as src, open(dest, 'wb') as dst:
                                shutil.copyfileobj(src, dst)
                    try:
                        for key in todo:
                            destination = root / key
                            if destination.exists():
                                backup_root.mkdir(exist_ok=True)
                                destination.rename(backup_root / key)
                            try:
                                (stage / key).rename(destination)
                            except OSError:
                                if (backup_root / key).exists():
                                    (backup_root / key).rename(destination)
                                raise
                            restored.append(key)
                    except OSError:
                        for key in reversed(restored):
                            (root / key).rename(stage / key)
                            if (backup_root / key).exists():
                                (backup_root / key).rename(root / key)
                        raise
                if restore_states:
                    settings = QgsSettings()
                    for record in records:
                        if record['id'] in restored:
                            settings.setValue('/PythonPlugins/'+record['id'], bool(record.get('enabled', False)))
                    settings.sync()
                log.append('Restaurées : '+', '.join(restored))
                if backup_root.exists():
                    log.append('Sauvegardes des versions remplacées : '+str(backup_root))
                QMessageBox.information(None, 'Plugin Transfer', '{} extension(s) restaurée(s).\nRedémarrez QGIS.\nLes dépendances externes ne sont pas incluses.'.format(len(restored)))
        except Exception as exc:
            log.append('ERREUR import : '+str(exc))
            QMessageBox.critical(None, 'Plugin Transfer', str(exc))
