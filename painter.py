# SPDX-License-Identifier: GPL-3.0-or-later
"""Export FBX propre pour Substance Painter : un objet par matériau M_* (= un Texture Set), pose de repos,
modificateurs appliqués, triangulé, faces nulles supprimées, une seule couche UV dans 0-1, normales réelles
conservées (custom / arêtes vives), sans armature ni tangentes."""
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
def fix_cable(me):
    bmc = bmesh.new(); bmc.from_mesh(me); bmc.normal_update()
    lay = bmc.loops.layers.float_vector.get("_nrm")
    verts = [v.co.copy() for v in bmc.verts]
    kd = KDTree(len(verts))
    for i, co in enumerate(verts):
        kd.insert(co, i)
    kd.balance()
    # rayon du tube : distance médiane entre sommets opposés ~ estimée par la plus grande arête de "tour"
    el = sorted(e.calc_length() for e in bmc.edges)
    circ_edge = el[int(len(el) * 0.5)] if el else 0.01
    flip = []
    for f in bmc.faces:
        c = f.calc_center_median()
        # rayon de recherche croissant jusqu'à avoir une section complète
        r = circ_edge * 4
        for _ in range(6):
            pts = kd.find_range(c, r)
            if len(pts) >= 24:
                break
            r *= 1.6
        cen = sum((p for p, _i, _d in pts), Vector()) / max(len(pts), 1)
        if f.normal.dot(c - cen) < 0:
            flip.append(f)
    if flip:
        bmesh.ops.reverse_faces(bmc, faces=flip)
    bmc.normal_update()
    if lay is not None:
        for f in bmc.faces:
            for lp in f.loops:
                lp[lay] = lp.vert.normal
    bmc.to_mesh(me); bmc.free()
    return len(flip)



def export(context, filepath, rig=None):
    scene = context.scene
    arm = rig
    prev = arm.data.pose_position if arm else None
    if arm:
        arm.data.pose_position = 'REST'
    dg = context.evaluated_depsgraph_get()
    dg.update()
    created = []
    prev_sel = [o for o in context.view_layer.objects if o.select_get()]
    prev_act = context.view_layer.objects.active
    try:
        groups = {}
        for o in bpy.data.objects:
            if o.type != 'MESH' or not o.visible_get() or not o.material_slots or not o.material_slots[0].material:
                continue
            m = o.material_slots[0].material
            if not m.name.startswith("M_"):
                continue
            groups.setdefault(m.name, []).append(o)

        report = {}
        out_objs = created
        for mname, objs in sorted(groups.items()):
            bm = bmesh.new()
            for o in objs:
                oe = o.evaluated_get(dg)
                me = bpy.data.meshes.new_from_object(oe, preserve_all_data_layers=True, depsgraph=dg)
                # une seule couche UV : la couche de rendu (UV_Texture / UVMap d'origine)
                keep = next((l.name for l in me.uv_layers if l.active_render), me.uv_layers[0].name if me.uv_layers else None)
                for l in list(me.uv_layers):
                    if l.name != keep:
                        me.uv_layers.remove(l)
                if me.uv_layers:
                    me.uv_layers[0].name = "UVMap"
                # normales réelles (custom / sharp / auto smooth) conservées dans un attribut de coin
                Mw = oe.matrix_world
                N3 = Mw.to_3x3().inverted().transposed()
                cn = np.empty(len(me.loops) * 3, dtype=np.float32)
                me.corner_normals.foreach_get("vector", cn) if len(me.loops) else None
                cn = cn.reshape(-1, 3) @ np.array(N3, dtype=np.float32).T
                ln = np.linalg.norm(cn, axis=1, keepdims=True); ln[ln == 0] = 1
                att = me.attributes.new("_nrm", 'FLOAT_VECTOR', 'CORNER')
                att.data.foreach_set("vector", (cn / ln).ravel())
                me.transform(Mw)
                if Mw.determinant() < 0:
                    me.flip_normals()
                if o.name.startswith("Cable_"):
                    fix_cable(me)
                me.materials.clear()
                tmp = bmesh.new(); tmp.from_mesh(me)
                tmp_me = bpy.data.meshes.new("tmp"); tmp.to_mesh(tmp_me); tmp.free()
                bm.from_mesh(tmp_me)
                bpy.data.meshes.remove(tmp_me); bpy.data.meshes.remove(me)
            nf0 = len(bm.faces)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
            bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-7)
            bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='EAR_CLIP')
            # triangles d'aire nulle restants
            bm.normal_update()
            zero = [f for f in bm.faces if f.calc_area() < 1e-10 or f.normal.length < 0.5]
            if zero:
                bmesh.ops.delete(bm, geom=zero, context='FACES')
            loose = [v for v in bm.verts if not v.link_faces]
            if loose:
                bmesh.ops.delete(bm, geom=loose, context='VERTS')
            loose_e = [e for e in bm.edges if not e.link_faces]
            if loose_e:
                bmesh.ops.delete(bm, geom=loose_e, context='EDGES')
            # UV dans [0,1] strict (pas de débordement d'UDIM)
            uvl = bm.loops.layers.uv.active
            oob = 0
            if uvl:
                eps = 1e-5
                for f in bm.faces:
                    for lp in f.loops:
                        u, v = lp[uvl].uv
                        cu, cv = min(max(u, eps), 1 - eps), min(max(v, eps), 1 - eps)
                        if abs(cu - u) > 1e-3 or abs(cv - v) > 1e-3:
                            oob += 1
                        lp[uvl].uv = (cu, cv)
            name = "SM_" + mname[2:]
            me = bpy.data.meshes.new(name)
            bm.to_mesh(me); bm.free()
            me.materials.append(bpy.data.materials[mname])
            a = me.attributes.get("_nrm")
            if a is not None:
                cn = np.empty(len(me.loops) * 3, dtype=np.float32); a.data.foreach_get("vector", cn)
                cn = cn.reshape(-1, 3); ln = np.linalg.norm(cn, axis=1)
                bad = ln < 0.5
                if bad.any():                                  # coin sans normale fiable -> normale de la face
                    fidx = np.empty(len(me.loops), dtype=np.int32)
                    for p in me.polygons:
                        fidx[p.loop_start:p.loop_start + p.loop_total] = p.index
                    fn = np.empty(len(me.polygons) * 3, dtype=np.float32); me.polygons.foreach_get("normal", fn)
                    cn[bad] = fn.reshape(-1, 3)[fidx[bad]]
                cn /= np.maximum(np.linalg.norm(cn, axis=1, keepdims=True), 1e-8)
                me.attributes.remove(a)
                me.normals_split_custom_set(cn.tolist())
            ob = bpy.data.objects.new(name, me)
            scene.collection.objects.link(ob)
            out_objs.append(ob)
            report[name] = dict(objets=len(objs), faces_avant=nf0, triangles=len(me.polygons), uv_hors_0_1=oob,
                                couches_uv=[l.name for l in me.uv_layers])

        for o in context.view_layer.objects:
            o.select_set(False)
        for o in created:
            o.select_set(True)
        context.view_layer.objects.active = created[0]
        bpy.ops.export_scene.fbx(filepath=filepath, use_selection=True, object_types={'MESH'},
                                 use_mesh_modifiers=False, mesh_smooth_type='OFF', use_tspace=False,
                                 apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z',
                                 axis_up='Y', bake_anim=False, add_leaf_bones=False, path_mode='STRIP',
                                 embed_textures=False, use_custom_props=False, colors_type='NONE')
        return report
    finally:
        for o in created:
            me = o.data
            bpy.data.objects.remove(o)
            if me.users == 0:
                bpy.data.meshes.remove(me)
        for o in prev_sel:
            try:
                o.select_set(True)
            except Exception:
                pass
        context.view_layer.objects.active = prev_act
        if arm:
            arm.data.pose_position = prev
