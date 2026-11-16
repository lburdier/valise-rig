# SPDX-License-Identifier: GPL-3.0-or-later
"""Presets d'animation de la valise + inertie des câbles (ressort amorti) cuite en clés."""
import math
import random
import bpy
from mathutils import Vector, Quaternion, Matrix
from . import rig as R

OPEN = dict(lid=126.0, latch=62.0, screen=105.0)
REST = dict(lid=0.0, latch=0.0, screen=0.0, handle_c=0.0, handle_g=0.0, handle_d=0.0,
            up=0.0, tilt=0.0, yaw=0.0, roll=0.0)

# Chaque preset : durée (images à 24 i/s), état de base, clés par canal [(image, valeur[, 'LIN'|'CONST'])],
# décalage entre les 4 fermoirs (stagger). Les canaux absents restent à l'état de base.
PRESETS = {
    "OUVERTURE": dict(
        label="Ouverture complète", icon='TRIA_UP',
        desc="Déverrouillage des fermoirs un par un, ouverture du couvercle avec léger rebond, puis écran du laptop",
        duration=136, stagger=4,
        keys=dict(latch=[(0, 0), (10, 68), (14, 62)],
                  lid=[(0, 0), (26, 0), (60, 95), (78, 131), (84, 124), (90, 127), (96, 126)],
                  screen=[(0, 0), (96, 0), (118, 106), (124, 103), (130, 105)])),
    "FERMETURE": dict(
        label="Fermeture", icon='TRIA_DOWN',
        desc="Écran rabattu, couvercle qui retombe avec un petit rebond, fermoirs verrouillés un par un",
        duration=116, stagger=4, base=OPEN,
        keys=dict(screen=[(0, 105), (26, 0)],
                  lid=[(0, 126), (32, 126), (60, 70), (72, 0), (76, 2.5), (80, 0)],
                  latch=[(0, 62), (86, 62), (96, -4), (100, 0)])),
    "RAPIDE": dict(
        label="Ouverture rapide", icon='FF',
        desc="Fermoirs claqués d'un coup, couvercle projeté qui dépasse puis se stabilise",
        duration=50, stagger=1,
        keys=dict(latch=[(0, 0), (5, 72), (8, 62)],
                  lid=[(0, 0), (8, 0), (22, 138), (28, 121), (33, 128), (38, 125), (43, 126)])),
    "COUP_OEIL": dict(
        label="Coup d'œil", icon='HIDE_OFF',
        desc="On entrouvre le couvercle (~25°), on regarde, on referme et on reverrouille",
        duration=100, stagger=3,
        keys=dict(latch=[(0, 0), (10, 62), (78, 62), (88, -3), (91, 0)],
                  lid=[(0, 0), (20, 0), (36, 28), (40, 25), (60, 26), (72, 0), (75, 1.2), (78, 0)])),
    "DEVERROUILLER": dict(
        label="Déverrouiller", icon='UNLOCKED',
        desc="Les 4 fermoirs s'ouvrent l'un après l'autre",
        duration=40, stagger=6, keys=dict(latch=[(0, 0), (10, 70), (14, 62)])),
    "VERROUILLER": dict(
        label="Verrouiller", icon='LOCKED',
        desc="Les 4 fermoirs se referment l'un après l'autre",
        duration=40, stagger=6, base=dict(latch=62.0), keys=dict(latch=[(0, 62), (8, -4), (11, 0)])),
    "LAPTOP": dict(
        label="Laptop : ouvrir / fermer", icon='DESKTOP',
        desc="Valise ouverte : l'écran du laptop s'ouvre, reste ouvert puis se referme",
        duration=100, stagger=0, base=OPEN,
        keys=dict(screen=[(0, 0), (30, 106), (34, 101), (38, 105), (70, 105), (96, 0)])),
    "SOULEVER": dict(
        label="Soulever (transport)", icon='EMPTY_SINGLE_ARROW',
        desc="La poignée se lève, la valise est soulevée et se balance, puis reposée",
        duration=140, stagger=0,
        keys=dict(handle_c=[(0, 0), (12, 95), (16, 88), (124, 88), (134, 0)],
                  up=[(0, 0), (16, 0), (36, 0.45), (110, 0.45), (126, 0)],
                  tilt=[(0, 0), (36, 0), (42, -4), (50, 3), (58, -2), (66, 1.2), (74, -0.6), (82, 0), (110, 0),
                        (118, 1.5), (126, 0)],
                  roll=[(0, 0), (36, 0), (46, 2), (56, -1.5), (66, 0.8), (76, 0)])),
    "POIGNEES": dict(
        label="Poignées latérales", icon='ARROW_LEFTRIGHT',
        desc="Les deux poignées latérales se lèvent puis retombent avec un petit balancement",
        duration=80, stagger=0,
        keys=dict(handle_g=[(0, 0), (14, 92), (20, 86), (46, 86), (58, -4), (63, 3), (68, 0)],
                  handle_d=[(4, 0), (18, 92), (24, 86), (50, 86), (62, -4), (67, 3), (72, 0)])),
    "CYCLE": dict(
        label="Cycle complet", icon='FILE_REFRESH',
        desc="Ouverture complète puis fermeture (enchaînement des deux presets)",
        sequence=[("OUVERTURE", 0), ("FERMETURE", 150)]),
    "REPOS": dict(
        label="Repos", icon='LOOP_BACK', desc="Une clé de repos (tout fermé) à l'image de départ",
        duration=1, stagger=0, keys={}),
}
SLUG = {"OUVERTURE": "Ouverture_complete", "FERMETURE": "Fermeture", "CYCLE": "Cycle_complet",
        "RAPIDE": "Ouverture_rapide", "COUP_OEIL": "Coup_d_oeil", "DEVERROUILLER": "Deverrouiller",
        "VERROUILLER": "Verrouiller", "LAPTOP": "Laptop_ecran", "SOULEVER": "Soulever",
        "POIGNEES": "Poignees_laterales", "REPOS": "Repos"}
ORDER = ["OUVERTURE", "FERMETURE", "CYCLE", "RAPIDE", "COUP_OEIL", "DEVERROUILLER", "VERROUILLER", "LAPTOP",
         "SOULEVER", "POIGNEES", "REPOS"]


def enum_items(self=None, context=None):
    return [(k, PRESETS[k]["label"], PRESETS[k]["desc"], PRESETS[k]["icon"], i) for i, k in enumerate(ORDER)]


def flatten(name):
    """-> (durée, {canal: [(image, valeur, interp)]}, stagger par canal)."""
    p = PRESETS[name]
    if "sequence" in p:
        out, dur, stag = {}, 0, {}
        for sub, off in p["sequence"]:
            d, keys, st = flatten(sub)
            for ch, ks in keys.items():
                lst = out.setdefault(ch, [])
                lst += [(f + off, v, it) for f, v, it in ks]
                stag[ch] = max(stag.get(ch, 0), st.get(ch, 0))
            dur = max(dur, off + d)
        for ch in out:
            out[ch].sort(key=lambda k: k[0])
        return dur, out, stag
    base = dict(REST); base.update(p.get("base", {}))
    keys = {}
    for ch in R.CHANNELS:
        ks = p["keys"].get(ch)
        if ks:
            keys[ch] = [(k[0], k[1], k[2] if len(k) > 2 else 'AUTO') for k in ks]
            if keys[ch][-1][0] < p["duration"]:
                keys[ch].append((p["duration"], keys[ch][-1][1], 'AUTO'))
        else:
            keys[ch] = [(0, base[ch], 'AUTO'), (p["duration"], base[ch], 'AUTO')]
    return p["duration"], keys, {"latch": p.get("stagger", 0)}


def _unique_action_name(base):
    name, i = base, 2
    while name in bpy.data.actions:
        name = "%s.%03d" % (base, i); i += 1
    return name


def generate(context, rig, preset, start=1, speed=1.0, inertia=True, amplitude=1.0, mode='ACTIVE',
             set_range=True):
    """Crée l'action du preset. Retourne (action, image de fin)."""
    R.prepare(rig)
    dur, keys, stag = flatten(preset)
    sp = max(0.1, speed)
    fr = lambda f: start + f / sp
    act = bpy.data.actions.new(_unique_action_name("Valise_" + SLUG.get(preset, preset.title())))
    act.use_fake_user = True
    if rig.animation_data is None:
        rig.animation_data_create()
    ad = rig.animation_data
    prev_action = ad.action
    ad.action = act
    for ch, ks in keys.items():
        bones, prop, idx, conv = R.CHANNELS[ch]
        for bi, b in enumerate(bones):
            pb = rig.pose.bones.get(b)
            if pb is None:
                continue
            off = stag.get(ch, 0) * bi
            for f, v, it in ks:
                getattr(pb, prop)[idx] = conv(v)
                frame = fr(f + (off if 0 < f else 0))
                pb.keyframe_insert(prop, index=idx, frame=frame, group=b)
            fc = R.find_fcurve(act, 'pose.bones["%s"].%s' % (b, prop), idx)
            if fc:
                for kp, (_f, _v, it) in zip(fc.keyframe_points, ks):
                    if it == 'LIN':
                        kp.interpolation = 'LINEAR'
                    elif it == 'CONST':
                        kp.interpolation = 'CONSTANT'
                    else:
                        kp.interpolation = 'BEZIER'
                        kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
                fc.update()
    end = fr(dur + max([s * 3 for s in stag.values()] + [0]))
    if inertia:
        bake_inertia(rig, act, int(math.floor(start)), int(math.ceil(end)) + 40, amplitude)
        end += 40
    if mode == 'NLA':
        ad.action = prev_action
        track = ad.nla_tracks.new()
        track.name = act.name
        strip = track.strips.new(act.name, int(start), act)
        try:
            if getattr(strip, "action_slot", None) is None and len(act.slots):
                strip.action_slot = act.slots[0]
        except Exception:
            pass
    scene = context.scene
    if set_range:
        scene.frame_start = int(start)
        scene.frame_end = int(math.ceil(end))
    scene.frame_set(int(start))
    return act, end


# ------------------------------------------------------------------------------------- inertie
SUB = 8
GAIN = 0.024          # hauteur du "ventre" des câbles du couvercle (m) par unité de forçage
FREQ = (1.4, 2.2)     # Hz
DAMP = 0.22


def _simulate(force, f0, zeta, dt):
    w = 2 * math.pi * f0
    x = v = 0.0
    out = []
    for F in force:
        v += (-w * w * x - 2 * zeta * w * v + F) * dt
        x += v * dt
        out.append(x)
    return out


def _d2(vals, dt):
    n = len(vals)
    out = [0.0] * n
    for i in range(1, n - 1):
        out[i] = (vals[i + 1] - 2 * vals[i] + vals[i - 1]) / (dt * dt)
    return out


def _new_fcurve(act, rig, path, index, group, frames, values):
    cb = R.channelbag(act)
    old = R.find_fcurve(act, path, index)
    if old is not None:
        (cb.fcurves if cb else act.fcurves).remove(old)
    fc = cb.fcurves.new(path, index=index) if cb else act.fcurves.new(path, index=index)
    if cb is not None:
        g = cb.groups.get(group) or cb.groups.new(group)
        fc.group = g
    fc.keyframe_points.add(len(frames))
    co = []
    for f, v in zip(frames, values):
        co += [f, v]
    fc.keyframe_points.foreach_set("co", co)
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'
    fc.update()


def bake_inertia(rig, act, f0, f1, amplitude=1.0):
    """Cuit l'inertie des câbles (os CVxx_yy du couvercle, CIxx_yy intérieurs) entre f0 et f1."""
    arm = rig.data
    if "Couvercle" not in arm.bones:
        return 0
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    dt = 1.0 / (fps * SUB)
    n = (f1 - f0) * SUB + 1
    T = [f0 + i / SUB for i in range(n)]
    fc_lid = R.find_fcurve(act, 'pose.bones["%s"].rotation_euler' % R.LID, 0)
    fc_up = R.find_fcurve(act, 'pose.bones["%s"].location' % R.MASTER, 1)
    theta = [fc_lid.evaluate(t) if fc_lid else 0.0 for t in T]
    up = [fc_up.evaluate(t) if fc_up else 0.0 for t in T]
    alpha = _d2(theta, dt)
    a_up = _d2(up, dt)
    lidb = arm.bones["Couvercle"]
    hinge = (lidb.matrix_local.to_3x3() @ Vector((1, 0, 0))).normalized()
    pivot = lidb.head_local.copy()
    rnd = random.Random(7)
    frames = list(range(f0, f1 + 1))
    count = 0

    chains = {}
    for b in arm.bones:
        if b.name.startswith("CV") and not b.name.endswith("_FIN"):
            chains.setdefault(b.name.rsplit("_", 1)[0], []).append(b.name)
    for cname in sorted(chains):
        bones = sorted(chains[cname])
        bl = [arm.bones[x] for x in bones]
        lens = [b.length for b in bl]
        Lc = sum(lens)
        mid = sum(((b.head_local + b.tail_local) / 2 for b in bl), Vector()) / len(bl)
        n_out = Vector((0, 0, 1)) if mid.z > 1.9 else Vector((0, 0, -1))
        k = -hinge.cross(mid - pivot).dot(n_out)
        force = []
        for th, al, au in zip(theta, alpha, a_up):
            nw = Matrix.Rotation(th, 3, hinge) @ n_out          # normale actuelle (couvercle tourné)
            force.append(k * al - au * nw.z)
        A = _simulate(force, rnd.uniform(*FREQ), DAMP * rnd.uniform(0.85, 1.15), dt)
        cap = min(0.08, 0.02 * Lc) * amplitude
        s_acc, slopes = 0.0, []
        for L in lens:
            sm = s_acc + L / 2; s_acc += L
            slopes.append(math.pi / Lc * math.cos(math.pi * sm / Lc))
        rel = [slopes[0]] + [slopes[j] - slopes[j - 1] for j in range(1, len(slopes))]
        for j, bn in enumerate(bones):
            b = arm.bones[bn]
            ax = (b.tail_local - b.head_local).cross(n_out)
            if ax.length < 1e-6:
                ax = hinge.copy()
            axl = (b.matrix_local.to_3x3().inverted() @ ax.normalized()).normalized()
            qs = []
            for f in frames:
                h = A[(f - f0) * SUB] * GAIN * amplitude
                h = max(-0.25 * cap, min(cap, h))
                qs.append(Quaternion(axl, h * rel[j]))
            rig.pose.bones[bn].rotation_mode = 'QUATERNION'
            for i in range(4):
                _new_fcurve(act, rig, 'pose.bones["%s"].rotation_quaternion' % bn, i, "Inertie_Cables_Couvercle",
                            frames, [q[i] for q in qs])
            count += 1

    for pb in rig.pose.bones:
        if not pb.name.startswith("CI"):
            continue
        con = next((c for c in pb.constraints if c.type == 'TRANSFORM'), None)
        dz = con.to_min_z if con else 0.0
        lim = con.from_max_x_rot if con else 1.0
        off = [dz * (1 - min(max(t / lim, 0.0), 1.0)) for t in theta]
        acc = [-a - b for a, b in zip(_d2(off, dt), a_up)]
        if max(abs(x) for x in acc) < 1e-6:
            continue
        z = _simulate(acc, rnd.uniform(2.0, 3.0), 0.18, dt)
        vals = [max(-0.05, min(0.05, z[(f - f0) * SUB] * amplitude)) for f in frames]
        _new_fcurve(act, rig, 'pose.bones["%s"].location' % pb.name, 2, "Inertie_Cables_Interieurs", frames, vals)
        count += 1
    return count
