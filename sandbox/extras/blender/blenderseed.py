
#
# This source file is part of appleseed.
# Visit http://appleseedhq.net/ for additional information and resources.
#
# This software is released under the MIT license.
#
# Copyright (c) 2010-2011 Francois Beaune
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

# Imports.
import bpy
import os


#
# Plugin information.
#

bl_info = {
    "name": "appleseed (.appleseed)",
    "author": "Franz Beaune",
    "version": (1, 1, 0),
    "blender": (2, 5, 7),
    "api": 36339,
    "location": "File > Export > appleseed (.appleseed)",
    "description": "appleseed (.appleseed)",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"}

script_name = "blenderseed.py"

def get_version_string():
    return "version " + ".".join(map(str, bl_info["version"]))


#
# Write a mesh object to disk in Wavefront OBJ format.
#

def write_mesh_object_to_disk(object, filepath):
    try:
        output_file = open(filepath, "w")

        # Write file header.
        output_file.write("# File generated by {0} {1}.\n".format(script_name, get_version_string()))

        # Write vertices.
        vertices = object.data.vertices
        output_file.write("# {0} vertices.\n".format(len(vertices)))
        for v in vertices:
            output_file.write("v {0} {1} {2}\n".format(v.co[0], v.co[2], -v.co[1]))

        # Write faces.
        faces = object.data.faces
        output_file.write("# {0} faces.\n".format(len(faces)))
        for f in faces:
            output_file.write("f")
            for fv in f.vertices:
                fv_index = fv + 1
                output_file.write(" " + str(fv_index))
            output_file.write("\n")

        output_file.close()
    except IOError:
        # todo: display error.
        return


#
# Exporter class.
#

class Exporter(bpy.types.Operator):
    bl_idname = "export.appleseed"
    bl_label = "Export to appleseed"

    filepath = StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        self.__export(os.path.splitext(self.filepath)[0] + ".appleseed")
        return { 'FINISHED' }

    def invoke(self, context, event):
        WindowManager = context.window_manager
        WindowManager.fileselect_add(self)
        return { 'RUNNING_MODAL' }

    def __export(self, file_path):
        try:
            self._output_file = open(file_path, "w")
            self._indent = 0
            self.__emit_file_header()
            self.__emit_project()
            self._output_file.close()
        except IOError:
            # todo: display error.
            return

    def __emit_file_header(self):
        self.__emit_line("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
        self.__emit_line("<!-- File generated by " + script_name + " " + get_version_string() + ". -->")

    def __emit_project(self):
        self.__open_element("project")
        self.__emit_scene()
        self.__emit_output()
        self.__emit_configurations()
        self.__close_element("project")

    def __emit_scene(self):
        self.__open_element("scene")
        self.__emit_camera()
        self.__emit_assembly()
        self.__emit_assembly_instance()
        self.__close_element("scene")

    def __emit_camera(self):
        camera = bpy.context.scene.camera

        film_width = 32.0 / 1000                                # Blender's film width is hardcoded to 32 mm
        aspect_ratio = 640.0 / 480                              # todo: compute
        focal_length = camera.data.lens / 1000.0                # Blender's camera focal length is expressed in mm

        self.__open_element('camera name="' + camera.name + '" model="pinhole_camera"')
        self.__emit_parameter("film_width", film_width)
        self.__emit_parameter("aspect_ratio", aspect_ratio)
        self.__emit_parameter("focal_length", focal_length)
        self.__open_element("transform")

        origin = camera.matrix_world[3]
        forward = -camera.matrix_world[2]
        up = camera.matrix_world[1]
        target = origin + forward

        origin_str = str(origin[0]) + " " + str(origin[2]) + " " + str(-origin[1])
        target_str = str(target[0]) + " " + str(target[2]) + " " + str(-target[1])
        up_str =     str(    up[0]) + " " + str(    up[2]) + " " + str(    -up[1])

        self.__emit_line('<look_at origin="' + origin_str + '" target="' + target_str + '" up="' + up_str + '" />')
        self.__close_element("transform")
        self.__close_element("camera")

    def __emit_assembly(self):
        self.__open_element("assembly name=\"assembly\"")
        self.__emit_objects()
        self.__close_element("assembly")

    def __emit_objects(self):
        for object in bpy.context.scene.objects:
            if object.type == 'MESH':
                self.__emit_object(object)

    def __emit_object(self, object):
        self.__emit_mesh_object(object)
        self.__emit_object_instance(object)

    def __emit_mesh_object(self, object):
        filename = object.name + ".obj"
        filepath = os.path.join(os.path.dirname(self.filepath), filename)
        write_mesh_object_to_disk(object, filepath)
        self.__open_element('object name="' + object.name + '" model="mesh_object"')
        self.__emit_parameter("filename", filename)
        self.__close_element("object")

    def __emit_object_instance(self, object):
        self.__open_element('object_instance name="' + object.name + '_inst" object="' + object.name + '.0"')
        self.__emit_transform(object.matrix_world)
        self.__close_element("object_instance")

    def __emit_assembly_instance(self):
        self.__open_element('assembly_instance name="assembly_inst" assembly="assembly"')
        self.__close_element("assembly_instance")

    def __emit_output(self):
        self.__open_element("output")
        self.__emit_frame()
        self.__close_element("output")

    def __emit_frame(self):
        self.__open_element("frame name=\"beauty\"")
        self.__emit_parameter("camera", bpy.context.scene.camera.name)
        self.__emit_custom_prop(bpy.context.scene, "resolution", "640 480")
        self.__emit_custom_prop(bpy.context.scene, "color_space", "srgb")
        self.__close_element("frame")

    def __emit_configurations(self):
        self.__open_element("configurations")
        self.__emit_configuration("final", "base_final")
        self.__emit_configuration("interactive", "base_interactive")
        self.__close_element("configurations")

    def __emit_configuration(self, name, base):
        self.__open_element("configuration name=\"" + name + "\" base=\"" + base + "\"")
        self.__close_element("configuration")

    def __emit_transform(self, matrix):
        self.__open_element("transform")
        self.__emit_matrix(matrix)
        self.__close_element("transform")

    def __emit_matrix(self, matrix):
        self.__open_element("matrix")
        self.__emit_matrix_values(matrix)
        self.__close_element("matrix")

    def __emit_matrix_values(self, values):
        self.__emit_line("{0} {1} {2} {3}".format(values[0][0], values[0][2], -values[0][1], values[3][0]))
        self.__emit_line("{0} {1} {2} {3}".format(values[1][0], values[1][2], -values[1][1], values[3][2]))
        self.__emit_line("{0} {1} {2} {3}".format(values[2][0], values[2][2], -values[2][1], -values[3][1]))
        self.__emit_line("{0} {1} {2} {3}".format(values[0][3], values[2][3], -values[1][3], values[3][3]))

    def __emit_custom_prop(self, object, prop_name, default_value):
        value = self.__get_custom_prop(object, prop_name, default_value)
        self.__emit_parameter(prop_name, value)

    def __get_custom_prop(self, object, prop_name, default_value):
        if prop_name in object:
            return object[prop_name]
        else:
            return default_value

    def __emit_parameter(self, name, value):
        self.__emit_line("<parameter name=\"" + name + "\" value=\"" + str(value) + "\" />")

    def __open_element(self, name):
        self.__emit_line("<" + name + ">")
        self.__indent()

    def __close_element(self, name):
        self.__unindent()
        self.__emit_line("</" + name + ">")

    def __emit_line(self, line):
        self.__emit_indent()
        self._output_file.write(line + "\n")

    def __indent(self):
        self._indent += 1

    def __unindent(self):
        assert self._indent > 0
        self._indent -= 1

    def __emit_indent(self):
        IndentSize = 4
        self._output_file.write(" " * self._indent * IndentSize)


#
# Hook into Blender.
#

def menu_func(self, context):
    default_path = os.path.splitext(bpy.data.filepath)[0] + ".appleseed"
    self.layout.operator(Exporter.bl_idname, text="appleseed (.appleseed)").filepath = default_path

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func)

def unregister():
    bpy.types.INFO_MT_file_export.remove(menu_func)
    bpy.utils.unregister_module(__name__)


#
# Entry point.
#

if __name__ == "__main__":
    register()
