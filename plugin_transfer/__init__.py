# SPDX-License-Identifier: GPL-2.0-or-later
def classFactory(iface):
    from .plugin import PluginTransfer
    return PluginTransfer(iface)
