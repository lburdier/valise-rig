# SPDX-License-Identifier: GPL-3.0-or-later
"""Panneau « Valise » de la barre latérale (N) de la vue 3D."""
import bpy
from . import rig as R, presets as P, updater


def draw_update_box(layout):
    st = updater.state["status"]
    if st == "available":
        row = layout.row()
        row.alert = True
        row.operator("valise.update_install", text="Installer la version %s" % updater.state["latest"],
                     icon='IMPORT')
    elif st in ("checking", "downloading", "installing"):
        layout.label(text={"checking": "Recherche…", "downloading": "Téléchargement…",
                           "installing": "Installation…"}[st], icon='SORTTIME')
    elif st == "installed":
        layout.label(text="Mis à jour : redémarre Blender si besoin", icon='CHECKMARK')
    elif st == "uptodate":
        layout.label(text="À jour (%s)" % updater.current_version_str(), icon='CHECKMARK')
    elif st == "error" and updater.state.get("error"):
        layout.label(text=updater.state["error"], icon='ERROR')


class VALISE_PT_main(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Valise"
    bl_label = "Valise"

    def draw(self, context):
        L = self.layout
        st = context.scene.valise
        rig = R.find_rig(context)
        row = L.row(align=True)
        row.prop(st, "rig", text="")
        if rig is None:
            L.label(text="Aucun RIG_Valise dans la scène", icon='ERROR')
            return
        act = rig.animation_data.action if rig.animation_data else None
        L.label(text="Animation : %s" % (act.name if act else "—"), icon='ACTION')

        # --- contrôle direct
        box = L.box()
        h = box.row()
        h.prop(st, "show_direct", text="", emboss=False, icon='TRIA_DOWN' if st.show_direct else 'TRIA_RIGHT')
        h.label(text="Contrôle direct", icon='ARMATURE_DATA')
        if st.show_direct:
            col = box.column(align=True)
            for p in ("lid", "latch", "screen"):
                col.prop(st, p, slider=True)
            col.separator()
            for p in ("handle_c", "handle_g", "handle_d"):
                col.prop(st, p, slider=True)
            col.separator()
            col.prop(st, "up")
            row = box.row(align=True)
            row.operator("valise.key", icon='KEYFRAME_HLT')
            row.operator("valise.read_pose", text="", icon='IMPORT')
            row.operator("valise.rest", text="", icon='LOOP_BACK')

        # --- presets
        box = L.box()
        box.label(text="Presets d'animation", icon='PRESET')
        box.prop(st, "preset", text="")
        desc = P.PRESETS[st.preset]["desc"]
        for line in _wrap(desc, 42):
            box.label(text=line)
        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(st, "start")
        row.prop(st, "speed")
        row = col.row(align=True)
        row.prop(st, "inertia", toggle=True, icon='FORCE_HARMONIC')
        sub = row.row(align=True)
        sub.active = st.inertia
        sub.prop(st, "amplitude")
        box.row().prop(st, "mode", expand=True)
        box.prop(st, "set_range")
        box.operator("valise.generate", icon='PLAY', text="Générer : " + P.PRESETS[st.preset]["label"])

        # --- bibliothèque
        box = L.box()
        h = box.row()
        h.prop(st, "show_lib", text="", emboss=False, icon='TRIA_DOWN' if st.show_lib else 'TRIA_RIGHT')
        h.label(text="Animations de la valise", icon='NLA')
        if st.show_lib:
            acts = R.valise_actions()
            if not acts:
                box.label(text="Aucune pour l'instant")
            for a in acts:
                row = box.row(align=True)
                f0, f1 = a.frame_range
                op = row.operator("valise.activate", text="%s  (%d-%d)" % (a.name[7:], f0, f1),
                                  icon='RADIOBUT_ON' if a == act else 'RADIOBUT_OFF', depress=(a == act))
                op.action = a.name
                row.operator("valise.delete", text="", icon='X').action = a.name
            row = box.row(align=True)
            row.operator("valise.reinertia", icon='FORCE_HARMONIC')
            row.operator("valise.bake_export", icon='EXPORT')
        L.operator("valise.export_painter", icon='TEXTURE')

        draw_update_box(L)


def _wrap(text, n):
    out, line = [], ""
    for w in text.split():
        if len(line) + len(w) + 1 > n:
            out.append(line); line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out


def register():
    bpy.utils.register_class(VALISE_PT_main)


def unregister():
    bpy.utils.unregister_class(VALISE_PT_main)
