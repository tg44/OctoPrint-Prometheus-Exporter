from __future__ import absolute_import, division, print_function, unicode_literals

import re
import sys

# https://community.octoprint.org/t/how-to-determine-filament-extruded/7828

# stolen directly from filaswitch
class Gcode_parser(object):
    
    MOVE_RE = re.compile(r"^G0\s+|^G1\s+")
    X_COORD_RE = re.compile(r".*\s+X([-]*\d+\.*\d*)")
    Y_COORD_RE = re.compile(r".*\s+Y([-]*\d+\.*\d*)")
    E_COORD_RE = re.compile(r".*\s+E([-]*\d+\.*\d*)")
    Z_COORD_RE = re.compile(r".*\s+Z([-]*\d+\.*\d*)")
    SPEED_VAL_RE = re.compile(r".*\s+F(\d+\.*\d*)")
    FAN_SET_RE = re.compile(r"^M106\s+")
    FAN_SPEED_RE = re.compile(r".*\s+S(\d+\.*\d*)")
    FAN_OFF_RE = re.compile(r"^M107")

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

        if m is None:
            return

        m = self.X_COORD_RE.match(line)
        x = float(m.groups()[0]) if m else None

        m = self.Y_COORD_RE.match(line)
        y = float(m.groups()[0]) if m else None

        m = self.Z_COORD_RE.match(line)
        z = float(m.groups()[0]) if m else None

        m = self.E_COORD_RE.match(line)
        e = float(m.groups()[0]) if m else None

        m = self.SPEED_VAL_RE.match(line)
        speed = float(m.groups()[0]) if m else None

        return x, y, z, e, speed

    def parse_fan_speed(self, line):
        if self.FAN_SET_RE.match(line):
            m = self.FAN_SPEED_RE.match(line)
            return float(m.groups()[0]) if m else 255.0
        return 0.0 if self.FAN_OFF_RE.match(line) else None

    def process_axis_movement(self, target_position, current_position):
        return abs(current_position - target_position)

    def process_line(self, line):
        movement = self.parse_move_args(line)
        if movement:
            (x, y, z, e, speed) = movement
            if e:
                self.extrusion_counter += e
                self.e = e
            if x:
                self.x_travel += abs(self.x - x) if self.x else 0
                self.x = x
            if y:
                self.y_travel += abs(self.y - y) if self.y else 0
                self.y = y
            if z:
                self.z_travel += abs(self.z - z) if self.z else 0
                self.z = z
            if speed:
                self.speed = speed
            return "movement"

        fanspeed = self.parse_fan_speed(line)
        if fanspeed:
            self.print_fan_speed = fanspeed
            return "print_fan_speed"

        return None
