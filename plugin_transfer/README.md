# Plugin Transfer

Sauvegardez les extensions Python de votre profil QGIS dans un ZIP et retrouvez-les sur un autre poste, même hors ligne.

## Utilisation

1. Installez et activez **Plugin Transfer** sur les deux postes. Pour une installation manuelle, ouvrez le gestionnaire d’extensions de QGIS, puis **Installer depuis un ZIP**, et sélectionnez `Plugin_Transfer_1.0.0.zip`.
2. Sur le poste de départ, ouvrez **Extensions → Plugin Transfer → Plugin Transfer - Migrer les extensions**. Cochez les extensions à emporter, puis cliquez sur **Exporter les extensions sélectionnées vers ZIP**. La liste indique la version et l’état de chaque extension. Une extension désactivée peut être exportée.
3. Sur le poste d’arrivée, ouvrez l’extension dans le profil voulu et cliquez sur **Importer une sauvegarde ZIP**. Par défaut, les extensions déjà présentes sont ignorées. Pour les mettre à jour à partir de la sauvegarde, cochez **Remplacer les extensions existantes** avant l’import.
4. Laissez **Restaurer les états activé/désactivé** coché si vous souhaitez reprendre les états du poste de départ. Confirmez l’import et redémarrez QGIS.

Les extensions remplacées sont conservées dans le dossier `python/plugin_transfer_backup_<horodatage>` du profil cible. Le journal affiche son chemin. Pour récupérer une ancienne version, fermez QGIS et recopiez le dossier de l’extension sauvegardée dans `python/plugins` du profil.

### Périmètre

L’archive contient les fichiers des extensions utilisateur sélectionnées et un manifeste. Les extensions fournies avec QGIS, les préférences du profil, les projets, les connexions et les dépendances installées séparément ne sont pas transférés. Importez uniquement des sauvegardes de confiance. Vérifiez la compatibilité des extensions transférées avec la version de QGIS et le système du poste cible.

## English

Back up selected Python plugins from the active QGIS user profile and restore them on another computer. The interface is in French.

1. Install and enable Plugin Transfer on both computers. Open **Plugins → Plugin Transfer**.
2. Select the plugins to include and click **Exporter les extensions sélectionnées vers ZIP** to create a backup.
3. In the destination profile, click **Importer une sauvegarde ZIP**. Existing plugins are skipped unless replacement is enabled. Replaced versions are backed up in the profile's Python directory. Restoring enabled states is optional.
4. Restart QGIS. Install any external dependencies separately. Only import archives you trust.

## Compatibilité et licence

QGIS 3.40.6 à 3.44.x. Essais fonctionnels sous Linux avec QGIS 3.40.6. La version d’origine fonctionne également sous QGIS 3.44 d’après son utilisateur. Interface en français. Licence GPL-2.0-or-later.
