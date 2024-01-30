from __future__ import absolute_import, division, print_function, unicode_literals

import re

# https://community.octoprint.org/t/how-to-determine-filament-extruded/7828

# stolen directly from filaswitch
class Gcode_parser(object):
    MOVE_RE = re.compile("^G0\s+|^G1\s+")
    X_COORD_RE = re.compile(".*\s+X([-]*\d+\.*\d*)")
    Y_COORD_RE = re.compile(".*\s+Y([-]*\d+\.*\d*)")
    E_COORD_RE = re.compile(".*\s+E([-]*\d+\.*\d*)")
    Z_COORD_RE = re.compile(".*\s+Z([-]*\d+\.*\d*)")
    SPEED_VAL_RE = re.compile(".*\s+F(\d+\.*\d*)")

    FAN_SET_RE = re.compile("^M106\s+")
    FAN_SPEED_RE = re.compile(".*\s+S(\d+\.*\d*)")

    FAN_OFF_RE = re.compile("^M107")

    COORDINATE_MODESWITCH_RE = re.compile("^(M82|M83|G90|G91)(?![0-9.])")

    def __init__(self):
        self.reset()

    def reset(self):
        self.last_extrusion_move = None
        self.extrusion_counter = 0
        self.x_travel = 0
        self.x = None
        self.y_travel = 0
        self.y = None
        self.z_travel = 0
        self.z = None
        self.e = None
        self.absolute_e = True
        self.absolute_moves = True
        self.speed = None
        self.print_fan_speed = None

    def is_extrusion_move(self, m):
        """ args are a tuple (x,y,z,e,speed)
        """
        if m and (m[0] is not None or m[1] is not None) and m[3] is not None and m[3] != 0:
            return True
        else:
            return False

    def parse_move_args(self, line):
        """ returns a tuple (x,y,z,e,speed) or None
        """

        m = self.MOVE_RE.match(line)
        if m:
            x = None
            y = None
            z = None
            e = None
            speed = None

            m = self.X_COORD_RE.match(line)
            if m:
                x = float(m.groups()[0])

            m = self.Y_COORD_RE.match(line)
            if m:
                y = float(m.groups()[0])

            m = self.Z_COORD_RE.match(line)
            if m:
                z = float(m.groups()[0])

            m = self.E_COORD_RE.match(line)
            if m:
                e = float(m.groups()[0])

            m = self.SPEED_VAL_RE.match(line)
            if m:
                speed = float(m.groups()[0])

            return x, y, z, e, speed

        return None

    def parse_fan_speed(self, line):
        m = self.FAN_SET_RE.match(line)
        if m:
            m = self.FAN_SPEED_RE.match(line)
            if m:
                speed = float(m.groups()[0])
            else:
                speed = 255.0
            return speed

        m = self.FAN_OFF_RE.match(line)
        if m:
            return 0.0

        return None

    def parse_coordinate_modeswitch(self, line):
        m = self.COORDINATE_MODESWITCH_RE.match(line)

        if not m:
            return None

        gcode = m.group(1)
        absolute_e = gcode in ("M82", "G90")
        absolute_moves = None

        if gcode.startswith("G"):
            absolute_moves = gcode == "G90"

        return (absolute_e, absolute_moves)

    def process_axis_movement(self, target_position, current_position, absolute):
        if target_position is None:
            return (0, current_position)

        if absolute:
            relative_movement = abs(current_position - target_position) if current_position is not None else None
            new_position = target_position

        else:
            relative_movement = abs(target_position)
            new_position = current_position + target_position if current_position is not None else None

        return (relative_movement, new_position)

    def process_line(self, line):
        movement = self.parse_move_args(line)
        if movement is not None:
            (x, y, z, e, speed) = movement

            (rel_e, new_e) = self.process_axis_movement(e, self.e, self.absolute_e)
            (rel_x, new_x) = self.process_axis_movement(x, self.x, self.absolute_moves)
            (rel_y, new_y) = self.process_axis_movement(y, self.y, self.absolute_moves)
            (rel_z, new_z) = self.process_axis_movement(z, self.z, self.absolute_moves)

            self.extrusion_counter += rel_e
            self.x_travel += rel_x
            self.y_travel += rel_y
            self.z_travel += rel_z

            (self.x, self.y, self.z, self.e) = (new_x, new_y, new_z, new_e)

            if speed is not None:
                self.speed = speed

            return "movement"

        fanspeed = self.parse_fan_speed(line)
        if fanspeed is not None:
            self.print_fan_speed = fanspeed
            return "print_fan_speed"

        coordinate_modes = self.parse_coordinate_modeswitch(line)
        if coordinate_modes is not None:
            (absolute_e, absolute_moves) = coordinate_modes

            if absolute_e is not None:
                self.absolute_e = absolute_e
            if absolute_moves is not None:
                self.absolute_moves = absolute_moves
            return "coordinate_modeswitch"

        return None
