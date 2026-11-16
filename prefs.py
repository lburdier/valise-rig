# SPDX-License-Identifier: GPL-3.0-or-later
"""Préférences : mises à jour automatiques depuis les releases GitHub."""
import bpy
from . import updater


class VALISE_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    check_updates: bpy.props.BoolProperty(
        name="Rechercher les mises à jour", default=True,
        description="Regarde s'il y a une nouvelle release sur GitHub au démarrage (une fois par jour max)")
    auto_update: bpy.props.BoolProperty(
        name="Installer automatiquement", default=True,
        description="Installe seule la nouvelle release. Désactivé = un bouton apparaît dans le panneau")
    update_repo: bpy.props.StringProperty(
        name="Dépôt GitHub", default=updater.DEFAULT_REPO,
        description="propriétaire/nom du dépôt GitHub dont les releases sont installées")

    def draw(self, context):
        L = self.layout
        box = L.box()
        row = box.row(align=True)
        row.label(text="Valise Rig %s" % updater.current_version_str())
        row.operator("valise.update_check", icon='FILE_REFRESH')
        from .ui import draw_update_box
        draw_update_box(box)
        box.prop(self, "check_updates")
        sub = box.column()
        sub.active = self.check_updates
        sub.prop(self, "auto_update")
        sub.prop(self, "update_repo")


def register():
    bpy.utils.register_class(VALISE_Preferences)


def unregister():
    bpy.utils.unregister_class(VALISE_Preferences)
