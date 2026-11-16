# SPDX-License-Identifier: GPL-3.0-or-later
"""Opérateurs de l'add-on Valise Rig."""
import bpy
from . import rig as R, presets as P, updater, painter
from bpy_extras.io_utils import ExportHelper


def _rig_or_report(op, context):
    rig = R.find_rig(context)
    if rig is None:
        op.report({'ERROR'}, "Aucun rig de valise trouvé (armature avec CTRL_Couvercle)")
    return rig


class VALISE_OT_generate(bpy.types.Operator):
    bl_idname = "valise.generate"
    bl_label = "Générer l'animation"
    bl_description = "Crée une nouvelle action à partir du preset choisi (avec l'inertie des câbles si activée)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig = _rig_or_report(self, context)
        if rig is None:
            return {'CANCELLED'}
        st = context.scene.valise
        if context.object and context.object.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
        act, end = P.generate(context, rig, st.preset, start=st.start, speed=st.speed, inertia=st.inertia,
                              amplitude=st.amplitude, mode=st.mode, set_range=st.set_range)
        self.report({'INFO'}, "%s créée (images %d à %d)" % (act.name, st.start, int(end)))
        return {'FINISHED'}


class VALISE_OT_activate(bpy.types.Operator):
    bl_idname = "valise.activate"
    bl_label = "Activer"
    bl_description = "Rend cette animation active sur la valise et cale la plage d'images dessus"
    bl_options = {'REGISTER', 'UNDO'}
    action: bpy.props.StringProperty()

    def execute(self, context):
        rig = _rig_or_report(self, context)
        act = bpy.data.actions.get(self.action)
        if rig is None or act is None:
            return {'CANCELLED'}
        if rig.animation_data is None:
            rig.animation_data_create()
        rig.animation_data.action = act
        f0, f1 = act.frame_range
        context.scene.frame_start, context.scene.frame_end = int(f0), int(f1)
        context.scene.frame_set(int(f0))
        return {'FINISHED'}


class VALISE_OT_delete(bpy.types.Operator):
    bl_idname = "valise.delete"
    bl_label = "Supprimer"
    bl_description = "Supprime cette animation du fichier"
    bl_options = {'REGISTER', 'UNDO'}
    action: bpy.props.StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        act = bpy.data.actions.get(self.action)
        if act is None:
            return {'CANCELLED'}
        bpy.data.actions.remove(act)
        return {'FINISHED'}


class VALISE_OT_reinertia(bpy.types.Operator):
    bl_idname = "valise.reinertia"
    bl_label = "Recalculer l'inertie"
    bl_description = ("Recalcule l'inertie des câbles sur l'animation active "
                      "(à faire après avoir retouché le couvercle ou CTRL_Master à la main)")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig = _rig_or_report(self, context)
        if rig is None or rig.animation_data is None or rig.animation_data.action is None:
            self.report({'ERROR'}, "Pas d'animation active sur la valise")
            return {'CANCELLED'}
        act = rig.animation_data.action
        f0, f1 = act.frame_range
        n = P.bake_inertia(rig, act, int(f0), int(f1) + 40, context.scene.valise.amplitude)
        self.report({'INFO'}, "Inertie recalculée sur %d os" % n)
        return {'FINISHED'}


class VALISE_OT_key(bpy.types.Operator):
    bl_idname = "valise.key"
    bl_label = "Insérer une clé"
    bl_description = "Enregistre l'état des curseurs à l'image courante dans l'animation active"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig = _rig_or_report(self, context)
        if rig is None:
            return {'CANCELLED'}
        R.prepare(rig)
        if rig.animation_data is None:
            rig.animation_data_create()
        if rig.animation_data.action is None:
            a = bpy.data.actions.new("Valise_Manuel"); a.use_fake_user = True
            rig.animation_data.action = a
        f = context.scene.frame_current
        st = context.scene.valise
        for ch in ("lid", "latch", "screen", "handle_c", "handle_g", "handle_d", "up"):
            R.set_channel(rig, ch, getattr(st, ch))
            bones, prop, idx, _c = R.CHANNELS[ch]
            for b in bones:
                if b in rig.pose.bones:
                    rig.pose.bones[b].keyframe_insert(prop, index=idx, frame=f, group=b)
        return {'FINISHED'}


class VALISE_OT_read_pose(bpy.types.Operator):
    bl_idname = "valise.read_pose"
    bl_label = "Lire la pose"
    bl_description = "Recopie la pose actuelle de la valise dans les curseurs"
    bl_options = {'REGISTER'}

    def execute(self, context):
        rig = _rig_or_report(self, context)
        if rig is None:
            return {'CANCELLED'}
        st = context.scene.valise
        st.lock_update = True
        try:
            for ch in ("lid", "latch", "screen", "handle_c", "handle_g", "handle_d", "up"):
                setattr(st, ch, R.get_channel(rig, ch))
        finally:
            st.lock_update = False
        return {'FINISHED'}


class VALISE_OT_rest(bpy.types.Operator):
    bl_idname = "valise.rest"
    bl_label = "Pose de repos"
    bl_description = "Remet tous les contrôleurs à zéro (valise fermée) sans toucher aux animations"
    bl_options = {'REGISTER', 'UNDO'}
    detach: bpy.props.BoolProperty(name="Détacher l'animation active", default=False)

    def execute(self, context):
        rig = _rig_or_report(self, context)
        if rig is None:
            return {'CANCELLED'}
        if self.detach and rig.animation_data:
            rig.animation_data.action = None
        R.reset_pose(rig)
        bpy.ops.valise.read_pose()
        return {'FINISHED'}


class VALISE_OT_bake_export(bpy.types.Operator):
    bl_idname = "valise.bake_export"
    bl_label = "Cuire pour l'export"
    bl_description = ("Crée une copie de l'animation active avec toutes les contraintes cuites (Visual Keying) "
                      "pour l'export FBX / moteur de jeu. L'original n'est pas modifié")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig = _rig_or_report(self, context)
        if rig is None or rig.animation_data is None or rig.animation_data.action is None:
            self.report({'ERROR'}, "Pas d'animation active sur la valise")
            return {'CANCELLED'}
        src = rig.animation_data.action
        f0, f1 = (int(x) for x in src.frame_range)
        prev_active = context.view_layer.objects.active
        prev_mode = context.object.mode if context.object else 'OBJECT'
        if prev_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for o in context.view_layer.objects:
            o.select_set(False)
        rig.hide_set(False); rig.select_set(True)
        context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.nla.bake(frame_start=f0, frame_end=f1, only_selected=False, visual_keying=True,
                         clear_constraints=False, use_current_action=False, bake_types={'POSE'})
        baked = rig.animation_data.action
        if baked is not None and baked != src:
            baked.name = src.name + "_EXPORT"
            baked.use_fake_user = True
        bpy.ops.object.mode_set(mode='OBJECT')
        if prev_active:
            context.view_layer.objects.active = prev_active
        self.report({'INFO'}, "Action cuite : %s" % (baked.name if baked else "?"))
        return {'FINISHED'}


class VALISE_OT_export_painter(bpy.types.Operator, ExportHelper):
    bl_idname = "valise.export_painter"
    bl_label = "Exporter pour Substance Painter"
    bl_description = ("FBX propre pour Painter : un objet par matériau M_* (un Texture Set chacun), pose fermée, "
                      "triangulé, UV 0-1, normales conservées")
    filename_ext = ".fbx"
    filter_glob: bpy.props.StringProperty(default="*.fbx", options={'HIDDEN'})

    def invoke(self, context, event):
        if not self.filepath:
            import os
            base = os.path.splitext(bpy.data.filepath)[0] if bpy.data.filepath else "valise"
            self.filepath = base + "_painter.fbx"
        return ExportHelper.invoke(self, context, event)

    def execute(self, context):
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        rep = painter.export(context, self.filepath, R.find_rig(context))
        n = sum(v["triangles"] for v in rep.values())
        self.report({'INFO'}, "%d Texture Sets, %d triangles -> %s" % (len(rep), n, self.filepath))
        return {'FINISHED'}


class VALISE_OT_update_check(bpy.types.Operator):
    bl_idname = "valise.update_check"
    bl_label = "Rechercher une mise à jour"
    bl_description = "Interroge les releases GitHub de l'add-on"

    def execute(self, context):
        msg = updater.check(manual=True)
        if msg:
            self.report({'WARNING'}, msg)
        return {'FINISHED'}


class VALISE_OT_update_install(bpy.types.Operator):
    bl_idname = "valise.update_install"
    bl_label = "Installer la mise à jour"
    bl_description = "Télécharge et installe la dernière release GitHub"

    def execute(self, context):
        msg = updater.install()
        if msg:
            self.report({'WARNING'}, msg)
        return {'FINISHED'}


classes = (VALISE_OT_generate, VALISE_OT_activate, VALISE_OT_delete, VALISE_OT_reinertia, VALISE_OT_key,
           VALISE_OT_read_pose, VALISE_OT_rest, VALISE_OT_bake_export, VALISE_OT_export_painter, VALISE_OT_update_check,
           VALISE_OT_update_install)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
