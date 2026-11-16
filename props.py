# SPDX-License-Identifier: GPL-3.0-or-later
"""Réglages de la scène : rig, curseurs de contrôle direct, options des presets."""
import bpy
from . import rig as R, presets as P


def _live(ch):
    def update(self, context):
        if self.lock_update:
            return
        rig = R.find_rig(context)
        if rig is not None:
            R.prepare(rig)
            R.set_channel(rig, ch, getattr(self, ch))
    return update


def _rig_poll(self, ob):
    return R.is_rig(ob)


class ValiseSettings(bpy.types.PropertyGroup):
    rig: bpy.props.PointerProperty(name="Rig", type=bpy.types.Object, poll=_rig_poll,
                                   description="Armature de la valise (vide = détection automatique)")
    lock_update: bpy.props.BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})

    lid: bpy.props.FloatProperty(name="Couvercle", min=0, max=130, default=0, subtype='FACTOR', precision=1,
                                 update=_live("lid"), description="Ouverture du couvercle (degrés)")
    latch: bpy.props.FloatProperty(name="Fermoirs", min=-5, max=77, default=0, subtype='FACTOR', precision=1,
                                   update=_live("latch"), description="Ouverture des 4 fermoirs (degrés)")
    screen: bpy.props.FloatProperty(name="Écran laptop", min=-5, max=112, default=0, subtype='FACTOR', precision=1,
                                    update=_live("screen"), description="Ouverture de l'écran (degrés)")
    handle_c: bpy.props.FloatProperty(name="Poignée avant", min=-5, max=110, default=0, subtype='FACTOR',
                                      precision=1, update=_live("handle_c"), description="Levée (degrés)")
    handle_g: bpy.props.FloatProperty(name="Poignée gauche", min=-5, max=110, default=0, subtype='FACTOR',
                                      precision=1, update=_live("handle_g"), description="Levée (degrés)")
    handle_d: bpy.props.FloatProperty(name="Poignée droite", min=-5, max=110, default=0, subtype='FACTOR',
                                      precision=1, update=_live("handle_d"), description="Levée (degrés)")
    up: bpy.props.FloatProperty(name="Hauteur", min=-1, max=3, default=0, unit='LENGTH', update=_live("up"),
                                description="Soulève toute la valise (CTRL_Master)")

    preset: bpy.props.EnumProperty(name="Preset", items=P.enum_items())
    start: bpy.props.IntProperty(name="Début", default=1, description="Image de départ de l'animation")
    speed: bpy.props.FloatProperty(name="Vitesse", default=1.0, min=0.25, max=4.0, step=10,
                                   description="×2 = deux fois plus rapide")
    inertia: bpy.props.BoolProperty(name="Inertie des câbles", default=True,
                                    description="Cuit le balancement amorti des câbles dans l'animation")
    amplitude: bpy.props.FloatProperty(name="Amplitude", default=1.0, min=0.0, max=3.0, step=10,
                                       description="Force de l'inertie des câbles")
    mode: bpy.props.EnumProperty(name="Mode", default='ACTIVE', items=[
        ('ACTIVE', "Action active", "La nouvelle animation remplace l'action active de la valise"),
        ('NLA', "Piste NLA", "Ajoute l'animation dans une nouvelle piste NLA (pour enchaîner/mélanger)")])
    set_range: bpy.props.BoolProperty(name="Caler la plage d'images", default=True)
    show_direct: bpy.props.BoolProperty(default=True)
    show_lib: bpy.props.BoolProperty(default=True)


def register():
    bpy.utils.register_class(ValiseSettings)
    bpy.types.Scene.valise = bpy.props.PointerProperty(type=ValiseSettings)


def unregister():
    del bpy.types.Scene.valise
    bpy.utils.unregister_class(ValiseSettings)
