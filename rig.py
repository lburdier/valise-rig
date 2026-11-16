# SPDX-License-Identifier: GPL-3.0-or-later
"""Accès au rig de la valise (RIG_Valise) : contrôleurs, canaux animables, pose."""
import math
import bpy

LID = "CTRL_Couvercle"
LATCHES = ("CTRL_Fermoir_01", "CTRL_Fermoir_02", "CTRL_Fermoir_03", "CTRL_Fermoir_04")
SCREEN = "CTRL_Laptop_Ecran"
HANDLE_C, HANDLE_G, HANDLE_D = "CTRL_Poignee_Centre", "CTRL_Poignee_Gauche", "CTRL_Poignee_Droite"
MASTER = "CTRL_Master"

R = math.radians
# canal -> (os, propriété, index, conversion valeur UI -> valeur Blender)
CHANNELS = {
    "lid":      ((LID,), "rotation_euler", 0, R),                  # degrés d'ouverture
    "latch":    (LATCHES, "rotation_euler", 0, R),                 # degrés (ouverture des fermoirs)
    "screen":   ((SCREEN,), "rotation_euler", 0, R),               # degrés d'ouverture de l'écran
    "handle_c": ((HANDLE_C,), "rotation_euler", 0, lambda v: -R(v)),  # degrés de levée
    "handle_g": ((HANDLE_G,), "rotation_euler", 0, lambda v: -R(v)),
    "handle_d": ((HANDLE_D,), "rotation_euler", 0, lambda v: -R(v)),
    "up":       ((MASTER,), "location", 1, float),                 # mètres (Y de l'os = haut)
    "tilt":     ((MASTER,), "rotation_euler", 0, R),               # bascule avant/arrière
    "yaw":      ((MASTER,), "rotation_euler", 1, R),               # rotation au sol
    "roll":     ((MASTER,), "rotation_euler", 2, R),               # bascule gauche/droite
}
EULER_BONES = (LID, SCREEN, HANDLE_C, HANDLE_G, HANDLE_D, MASTER) + LATCHES


def is_rig(ob):
    return ob is not None and ob.type == 'ARMATURE' and LID in ob.data.bones


def find_rig(context=None):
    context = context or bpy.context
    st = getattr(context.scene, "valise", None)
    if st and is_rig(st.rig):
        return st.rig
    ob = getattr(context, "object", None)
    if is_rig(ob):
        return ob
    if is_rig(bpy.data.objects.get("RIG_Valise")):
        return bpy.data.objects["RIG_Valise"]
    for ob in bpy.data.objects:
        if is_rig(ob):
            return ob
    return None


def prepare(rig):
    for n in EULER_BONES:
        pb = rig.pose.bones.get(n)
        if pb and pb.rotation_mode != 'XYZ':
            pb.rotation_mode = 'XYZ'


def set_channel(rig, ch, value):
    bones, prop, idx, conv = CHANNELS[ch]
    for b in bones:
        pb = rig.pose.bones.get(b)
        if pb is not None:
            getattr(pb, prop)[idx] = conv(value)


def get_channel(rig, ch):
    bones, prop, idx, conv = CHANNELS[ch]
    pb = rig.pose.bones.get(bones[0])
    if pb is None:
        return 0.0
    v = getattr(pb, prop)[idx]
    if conv is float:
        return v
    if ch.startswith("handle"):
        return -math.degrees(v)
    return math.degrees(v)


def reset_pose(rig):
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)


def channelbag(action, create_for=None):
    """Conteneur des F-Curves d'une action (actions à calques de Blender 4.4+)."""
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    return cb
    except AttributeError:
        return None
    return None


def fcurves(action):
    cb = channelbag(action)
    if cb is not None:
        return list(cb.fcurves)
    return list(getattr(action, "fcurves", []))


def find_fcurve(action, path, index):
    for fc in fcurves(action):
        if fc.data_path == path and fc.array_index == index:
            return fc
    return None


def valise_actions():
    return [a for a in bpy.data.actions if a.name.startswith("Valise_")]
