from __future__ import absolute_import, division, print_function, unicode_literals

import re

# https://community.octoprint.org/t/how-to-determine-filament-extruded/7828


class Gcode_parser(object):
    """Stolen directly from filaswitch"""

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
        self.extrusion_counter = 0
        self.x_travel = 0
        self.x_pos = None
        self.y_travel = 0
        self.y_pos = None
        self.z_travel = 0
        self.z_pos = None
        self.speed = None
        self.print_fan_speed = None

    def parse_move_args(self, line):
        """ returns a tuple (x,y,z,e,speed) or None
        """

        parsed = self.MOVE_RE.match(line)

        if parsed is None:
            return None

        parsed = self.X_COORD_RE.match(line)
        x_target = float(parsed.groups()[0]) if parsed else None

        parsed = self.Y_COORD_RE.match(line)
        y_target = float(parsed.groups()[0]) if parsed else None

        parsed = self.Z_COORD_RE.match(line)
        z_target = float(parsed.groups()[0]) if parsed else None

        parsed = self.E_COORD_RE.match(line)
        e_target = float(parsed.groups()[0]) if parsed else None

        parsed = self.SPEED_VAL_RE.match(line)
        speed = float(parsed.groups()[0]) if parsed else None

        return x_target, y_target, z_target, e_target, speed

    def parse_fan_speed(self, line):
        if self.FAN_SET_RE.match(line):
            parsed = self.FAN_SPEED_RE.match(line)
            return float(parsed.groups()[0]) if parsed else 255.0
        return 0.0 if self.FAN_OFF_RE.match(line) else None

    def process_line(self, line):
        movement = self.parse_move_args(line)
        if movement:
            x_target, y_target, z_target, e_target, speed = movement
            if e_target:
                self.extrusion_counter += e_target
            if x_target:
                self.x_travel += abs(self.x_pos - x_target) if self.x_pos else 0
                self.x_pos = x_target
            if y_target:
                self.y_travel += abs(self.y_pos - y_target) if self.y_pos else 0
                self.y_pos = y_target
            if z_target:
                self.z_travel += abs(self.z_pos - z_target) if self.z_pos else 0
                self.z_pos = z_target
            if speed:
                self.speed = speed
            return "movement"

        fanspeed = self.parse_fan_speed(line)
        if fanspeed:
            self.print_fan_speed = fanspeed
            return "print_fan_speed"

        return None
