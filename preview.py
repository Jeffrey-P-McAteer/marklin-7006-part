#!/usr/bin/env -S uv run
# /// script
# requires-python = "<=3.13"
# dependencies = [
#   "moderngl-window>=3.1",
#   "moderngl>=5.10",
#   "numpy",
#   "scipy",
#   "trimesh",
#   "pyrr",
# ]
# ///

import math
import os
import sys

import moderngl
import moderngl_window as mglw
import numpy as np
import trimesh
from pyrr import Matrix44


# ------------------------------------------------------------
# Consume our argument before moderngl-window sees argv
# ------------------------------------------------------------

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} file.stl")
    raise SystemExit(1)

STL_FILE = sys.argv[1]

# Leave only moderngl-window arguments
sys.argv = [sys.argv[0]] + sys.argv[2:]


VERTEX_SHADER = """
#version 330

uniform mat4 mvp;

in vec3 in_position;
in vec3 in_normal;

out vec3 v_normal;

void main()
{
    gl_Position = mvp * vec4(in_position, 1.0);
    v_normal = in_normal;
}
"""


FRAGMENT_SHADER = """
#version 330

in vec3 v_normal;

out vec4 f_color;

void main()
{
    float light = dot(
        normalize(v_normal),
        normalize(vec3(0.4,0.8,1.0))
    );

    light = clamp(light, 0.15, 1.0);

    vec3 base = vec3(0.72,0.74,0.78);

    f_color = vec4(
        base * light,
        1.0
    );
}
"""


class STLViewer(mglw.WindowConfig):

    gl_version = (3, 3)
    title = "STL Preview"
    window_size = (1200, 800)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.program = self.ctx.program(
            vertex_shader=VERTEX_SHADER,
            fragment_shader=FRAGMENT_SHADER,
        )

        self.ctx.enable(moderngl.DEPTH_TEST)

        self.vao = None

        self.last_mtime = 0

        self.center = np.zeros(3, dtype="f4")
        self.radius = 10

        self.distance = 50

        self.yaw = 30
        self.pitch = -25

        self.pan = np.zeros(3, dtype="f4")

        self.reload_mesh()


    def reload_mesh(self):

        try:
            mtime = os.path.getmtime(STL_FILE)
        except OSError:
            return

        if mtime == self.last_mtime:
            return

        self.last_mtime = mtime

        print("Loading:", STL_FILE)

        mesh = trimesh.load(
            STL_FILE,
            force="mesh"
        )

        mesh.remove_unreferenced_vertices()

        #
        # Flat shading:
        # duplicate vertices per triangle so each face
        # has its own normal.
        #

        triangles = mesh.triangles.astype("f4")

        face_normals = mesh.face_normals.astype("f4")

        vertices = triangles.reshape(
            (-1, 3)
        )

        normals = np.repeat(
            face_normals,
            3,
            axis=0
        ).astype("f4")

        faces = np.arange(
            len(vertices),
            dtype="u4"
        ).reshape((-1, 3))

        self.center = mesh.bounding_box.centroid.astype("f4")

        self.radius = np.linalg.norm(
            mesh.extents
        )

        self.distance = max(
            self.radius * 2.5,
            10
        )

        vbo = self.ctx.buffer(
            vertices.tobytes()
        )

        nbo = self.ctx.buffer(
            normals.tobytes()
        )

        ibo = self.ctx.buffer(
            faces.tobytes()
        )

        self.vao = self.ctx.vertex_array(
            self.program,
            [
                (vbo, "3f", "in_position"),
                (nbo, "3f", "in_normal"),
            ],
            ibo,
        )

        print(
            f"Loaded {len(faces)} triangles"
        )


    def on_render(self, time, frame_time):

        self.reload_mesh()

        self.ctx.clear(
            0.1,
            0.1,
            0.11
        )

        if self.vao is None:
            return


        projection = Matrix44.perspective_projection(
            45,
            self.wnd.aspect_ratio,
            0.01,
            100000,
            dtype="f4"
        )

        view = (
            Matrix44.from_translation(
                (0, 0, -self.distance)
            )
            *
            Matrix44.from_x_rotation(
                math.radians(self.pitch)
            )
            *
            Matrix44.from_y_rotation(
                math.radians(self.yaw)
            )
            *
            Matrix44.from_translation(
                -self.center + self.pan
            )
        )

        self.program["mvp"].write(
            (projection * view).astype("f4")
        )

        # Solid shaded pass
        self.ctx.wireframe = False
        self.vao.render()

        # Wireframe inspection overlay
        self.ctx.wireframe = True
        self.vao.render()

        self.ctx.wireframe = False


    def mouse_drag_event(
        self,
        x,
        y,
        dx,
        dy
    ):

        buttons = self.wnd.mouse_states.buttons

        if buttons.left:
            #
            # Orbit
            #
            self.yaw += dx * 0.5
            self.pitch += dy * 0.5

        elif buttons.middle or buttons.right:
            #
            # Pan
            #
            scale = self.distance * 0.002

            self.pan[0] += dx * scale
            self.pan[1] -= dy * scale


    def mouse_scroll_event(
        self,
        x,
        y,
        dx,
        dy
    ):

        self.distance *= 0.9 ** dy

        if self.vao is None:
            self.distance = max(
                self.radius * 2.5,
                10
            )


mglw.run_window_config(STLViewer)

