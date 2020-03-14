import bmesh
from mathutils import Vector
from bmesh.types import BMVert, BMFace

from .balcony_rails import (
    create_balcony_railing
)
from ...utils import (
    FaceMap,
    filter_geom,
    local_to_global,
    calc_edge_median,
    add_faces_to_map,
    calc_face_dimensions,
    inset_face_with_scale_offset,
)


def create_balcony(bm, faces, prop):
    """Generate balcony geometry
    """
    for f in faces:
        f = create_balcony_split(bm, f, prop.size_offset)

        add_faces_to_map(bm, [f], FaceMap.BALCONY)
        ret = bmesh.ops.extrude_face_region(bm, geom=[f])

        map_balcony_faces(bm, ret)
        bmesh.ops.translate(
            bm, verts=filter_geom(ret["geom"], BMVert), vec=-f.normal * prop.width
        )

        if prop.has_railing:
            add_railing_to_balcony_edges(bm, ret["geom"], f.normal, prop)
        bmesh.ops.delete(bm, geom=[f], context="FACES_ONLY")


def add_railing_to_balcony_edges(bm, balcony_geom, balcony_normal, prop):
    """Add railing to the balcony
    """
    face = filter_geom(balcony_geom, BMFace).pop()
    top_verts = sorted(face.verts, key=lambda v: v.co.z)[2:]
    edges = list(
        {e for v in top_verts for e in v.link_edges if e not in list(face.edges)}
    )
    sort_edges_from_normal_direction(edges, balcony_normal)

    left, right = edges
    front = bm.edges.get(top_verts)
    r_edges = choose_edges_from_direction(prop.open_side, front, left, right)
    create_balcony_railing(bm, r_edges, prop.rail, balcony_normal)


def sort_edges_from_normal_direction(edges, normal):
    """sort edges based on normal direction
    """
    if normal.y:
        edges.sort(key=lambda e: calc_edge_median(e).x, reverse=normal.y < 0)
    elif normal.x:
        edges.sort(key=lambda e: calc_edge_median(e).y, reverse=normal.x > 0)


def choose_edges_from_direction(direction, front, left, right):
    """filter out the edge specified by direction
    """
    return {
        "LEFT": [front, right],
        "FRONT": [left, right],
        "RIGHT": [front, left],
        "NONE": [left, right, front],
    }.get(direction)


def map_balcony_faces(bm, geom):
    """ Add balcony faces to their facemap """
    new_faces = {
        face
        for f in filter_geom(geom["geom"], BMFace)
        for e in f.edges
        for face in e.link_faces
    }
    add_faces_to_map(bm, new_faces, FaceMap.BALCONY)


def create_balcony_split(bm, face, prop):
    """Use properties from SplitOffset to subdivide face into regular quads
    """
    wall_w, wall_h = calc_face_dimensions(face)
    scale_x = prop.size.x/wall_w
    scale_y = prop.size.y/wall_h
    offset = local_to_global(face, Vector((prop.offset.x, prop.offset.y, 0.0)))
    return inset_face_with_scale_offset(bm, face, scale_y, scale_x, offset.x, offset.y, offset.z)
