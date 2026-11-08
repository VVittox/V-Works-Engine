







from __future__ import annotations
from array import array
import math

_VERTEX = '''#version 330
in vec3 in_position;
in vec3 in_color;
out vec3 fragment_color;
uniform float tan_y;
uniform float aspect;
uniform float near_plane;
uniform float far_plane;
uniform float ortho_half_y;
uniform int orthographic;
void main() {
    fragment_color = in_color;
    if (orthographic == 1) {
        float half_x = ortho_half_y * aspect;
        float z = (-2.0 * in_position.z - far_plane - near_plane) / (far_plane - near_plane);
        gl_Position = vec4(in_position.x / half_x, in_position.y / ortho_half_y, z, 1.0);
    } else {
        float yscale = 1.0 / tan_y;
        float z = -(far_plane + near_plane) / (far_plane - near_plane) * in_position.z
                  - 2.0 * far_plane * near_plane / (far_plane - near_plane);
        gl_Position = vec4(in_position.x * yscale / aspect,
                           in_position.y * yscale, z, -in_position.z);
    }
}
'''
_FRAGMENT = '''#version 330
in vec3 fragment_color;
out vec4 color;
void main() { color = vec4(fragment_color, 1.0); }
'''


class GpuTriangles3D:
    def __init__(self):
        try:
            import moderngl
        except ImportError as exc:
            raise RuntimeError('GPU 3D requires the optional moderngl package') from exc
        self.mgl = moderngl

        self.ctx = moderngl.create_standalone_context(require=330)
        self.program = self.ctx.program(vertex_shader=_VERTEX, fragment_shader=_FRAGMENT)
        self.size = None
        self.color_target = None
        self.depth_target = None
        self.framebuffer = None
        self.vertices = array('f')

    def resize(self, size):
        size = tuple(max(1, int(x)) for x in size)
        if size == self.size:
            return
        for obj in (self.framebuffer, self.color_target, self.depth_target):
            if obj is not None:
                obj.release()
        self.size = size
        self.color_target = self.ctx.texture(size, components=4)
        self.color_target.filter = (self.mgl.NEAREST, self.mgl.NEAREST)
        self.depth_target = self.ctx.depth_renderbuffer(size)
        self.framebuffer = self.ctx.framebuffer(
            color_attachments=[self.color_target], depth_attachment=self.depth_target
        )

    def add_face(self, vertices, color):

        if len(vertices) < 3:
            return
        r, g, b = (max(0.0, min(1.0, float(c) / 255.0)) for c in color[:3])
        for index in range(1, len(vertices) - 1):
            for p in (vertices[0], vertices[index], vertices[index + 1]):
                self.vertices.extend((p.x, p.y, p.z, r, g, b))

    def draw(self, projection, pygame):
        if not self.vertices:
            return None
        self.resize((projection.width, projection.height))
        self.framebuffer.use()
        self.ctx.viewport = (0, 0, *self.size)
        self.framebuffer.clear(0.0, 0.0, 0.0, 0.0, depth=1.0)
        self.ctx.enable(self.mgl.DEPTH_TEST)
        self.ctx.disable(self.mgl.BLEND)
        self.program['tan_y'].value = max(0.00001, projection.tany)
        self.program['aspect'].value = projection.width / projection.height
        self.program['near_plane'].value = projection.near
        self.program['far_plane'].value = projection.far
        self.program['ortho_half_y'].value = projection.halfy
        self.program['orthographic'].value = int(projection.orthographic)
        payload = self.vertices.tobytes()
        vbo = self.ctx.buffer(payload)
        vao = self.ctx.vertex_array(
            self.program, [(vbo, '3f 3f', 'in_position', 'in_color')]
        )
        try:
            vao.render(self.mgl.TRIANGLES)
            pixels = self.framebuffer.read(components=4, alignment=1)
        finally:
            vao.release()
            vbo.release()
            self.vertices = array('f')
        result = pygame.image.frombuffer(pixels, self.size, 'RGBA')
        return pygame.transform.flip(result, False, True)

    def clear(self):
        self.vertices = array('f')

    def release(self):
        for obj in (self.framebuffer, self.color_target, self.depth_target, self.program):
            if obj is not None:
                obj.release()
        self.ctx.release()
