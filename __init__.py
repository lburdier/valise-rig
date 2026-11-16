# SPDX-License-Identifier: GPL-3.0-or-later
"""Valise Rig — pilote le rig de la valise casque (RIG_Valise) depuis la barre latérale de la vue 3D.

* Contrôle direct : couvercle, fermoirs, écran du laptop, poignées, hauteur.
* Presets d'animation (ouverture, fermeture, cycle, ouverture rapide, coup d'œil, verrouillage, laptop,
  transport, poignées) générés en actions, avec l'inertie des câbles cuite en clés.
* Bibliothèque des animations, recalcul de l'inertie, cuisson pour l'export.
* Export FBX propre pour Substance Painter (un Texture Set par matériau M_*).
* Mises à jour automatiques depuis les releases GitHub.
"""
if "bpy" in locals():
    import importlib
    for _m in (rig, presets, painter, updater, props, ops, ui, prefs):  # noqa: F821
        importlib.reload(_m)
else:
    from . import rig, presets, painter, updater, props, ops, ui, prefs

import bpy  # noqa: E402

_modules = (prefs, props, ops, ui)


def register():
    for m in _modules:
        m.register()
    updater.register()


def unregister():
    updater.unregister()
    for m in reversed(_modules):
        m.unregister()
