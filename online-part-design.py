#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "cadquery",
# ]
# ///

import os
import sys
import traceback
import cadquery as cq
import importlib.util
import time
import datetime

if len(sys.argv) < 2:
    print('Usage: online-part-design.py /path/to/shared/folder/')
    sys.exit(1)

io_folder = os.path.abspath(sys.argv[1])
input_variables = os.path.join(io_folder, 'input-variables.py')
output_stl = os.path.join(io_folder, 'part.stl')
output_file = os.path.join(io_folder, 'output.txt')
output_errors = os.path.join(io_folder, 'errors.txt')

input_variables_last_mtime = 0

def now_timestamp():
    return '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())

def output(txt):
    print(txt)
    with open(output_file, 'a+') as fd:
        fd.write(txt)
        fd.write('\n')

def load_variables(filename):
    spec = importlib.util.spec_from_file_location(
        "_dynamic_inputs",
        filename,
    )

    module = importlib.util.module_from_spec(spec)

    # Executes the file every time.
    spec.loader.exec_module(module)

    # Copy every public variable into a dictionary.
    return {
        name: value
        for name, value in vars(module).items()
        if not name.startswith("__")
    }

while True:
    if not os.path.exists(input_variables):
        with open(input_variables, 'w+') as fd:
            fd.write('''
inner_length = 10.7
inner_width = 3.07
base_height = 1.00
cylinder_radius = 3.1 / 2.0 # 1.5
cylinder_extension_height = 3.11
cylinder_lcut_base_inset = 0.85   # Section in line w/ base, distance from edge in towards center
cylinder_lcut_raised_inset = cylinder_lcut_base_inset + 1.3 # Section above the base
cylinder_lcut_width = 1.0 # Width of the lcut, centered on the cylinder

part_total_length = inner_length + (2.0*cylinder_radius)
cylinder_total_height = base_height + cylinder_extension_height

    ''')

    time.sleep(30)

    try:
        input_variables_mtime = os.path.getmtime(input_variables)
        if input_variables_mtime > input_variables_last_mtime:
            input_variables_last_mtime = input_variables_mtime
            if os.path.exists(output_file): # Clean run output
                os.remove(output_file)
            output(f'Beginning build at {now_timestamp()}')

            variables = load_variables(input_variables)

            # Create rectangle
            base = (
                cq.Workplane("XY")
                .box(
                    variables['inner_length'],
                    variables['inner_width'],
                    variables['base_height']
                )
            )

            # End cylinders
            left_cylinder = (
                cq.Workplane("XY")
                .cylinder(
                    variables['cylinder_total_height'],
                    variables['cylinder_radius']
                )
                .translate(
                    (
                        (-(variables['inner_length']) / 2.0),
                        0,
                        (variables['cylinder_total_height'] / 2.0) - (variables['base_height']/2.0)
                    )
                )
            )

            right_cylinder = (
                cq.Workplane("XY")
                .cylinder(
                    variables['cylinder_total_height'],
                    variables['cylinder_radius']
                )
                .translate(
                    (
                        ((variables['inner_length']) / 2.0),
                        0,
                        (variables['cylinder_total_height'] / 2.0) - (variables['base_height']/2.0)
                    )
                )
            )

            part = (
                base
                .union(left_cylinder)
                .union(right_cylinder)
            )

            cutters = []

            top_l_box_positive = (
                cq.Workplane("XY")
                .box(
                    variables['cylinder_lcut_raised_inset'] * 2.0,
                    variables['cylinder_lcut_width'],
                    variables['cylinder_extension_height']
                )
                .translate(
                    (
                        ((variables['part_total_length']) / 2.0),
                        0,
                        variables['cylinder_total_height'] / 2.0
                    )
                )
            )
            cutters.append(top_l_box_positive)

            top_l_box_negative = (
                cq.Workplane("XY")
                .box(
                    variables['cylinder_lcut_raised_inset'] * 2.0,
                    variables['cylinder_lcut_width'],
                    variables['cylinder_extension_height']
                )
                .translate(
                    (
                        -((variables['part_total_length']) / 2.0),
                        0,
                        variables['cylinder_total_height'] / 2.0
                    )
                )
            )
            cutters.append(top_l_box_negative)


            base_l_box_positive = (
                cq.Workplane("XY")
                .box(
                    variables['cylinder_lcut_base_inset'] * 2.0,
                    variables['cylinder_lcut_width'],
                    variables['cylinder_extension_height']
                )
                .translate(
                    (
                        ((variables['part_total_length']) / 2.0),
                        0,
                        0
                    )
                )
            )
            cutters.append(base_l_box_positive)


            base_l_box_negative = (
                cq.Workplane("XY")
                .box(
                    variables['cylinder_lcut_base_inset'] * 2.0,
                    variables['cylinder_lcut_width'],
                    variables['cylinder_extension_height']
                )
                .translate(
                    (
                        -((variables['part_total_length']) / 2.0),
                        0,
                        0
                    )
                )
            )
            cutters.append(base_l_box_negative)


            # Now we slice the computex boxes off one at a time
            for cutter in cutters:
                part = part.cut(cutter)

            # Export as STL
            cq.exporters.export(part, output_stl)

            output(f'Successfully wrote {output_stl} at {now_timestamp()}')

        if os.path.exists(output_errors):
            os.remove(output_errors) # No errors, clear file
    except:
        traceback.print_exc()
        error_msg = traceback.format_exc()
        with open(output_errors, 'w+') as fd:
            fd.write(f'An error occurred at {now_timestamp()} and the .stl file was not modified. Update the file {os.path.basename(input_variables)} to try again.')
            fd.write(f'\n\n')
            fd.write(error_msg+'\n')

