"""Prometheus metrics class"""
import os
from prometheus_client import Counter, Info, Gauge, make_wsgi_app, CollectorRegistry
from octoprint.util import RepeatedTimer


class Metrics:

    registry = CollectorRegistry(auto_describe=True)

    def __init__(self, logger) -> None:
        self._logger = logger
        if self.get_raspberry_core_temperature() is not None:
            raspberry_core_temp = Gauge('octoprint_raspberry_core_temperature', 'Core temperature of Raspberry Pi', registry=self.registry)
            self.timer = RepeatedTimer(1.0, self.report_raspberry_core_temperature)
            self.timer.start()
        else:
            self._logger.info('Raspberry core temperature is not supported on this system')

    def report_raspberry_core_temperature(self):
        temperature = self.get_raspberry_core_temperature()
        if temperature is not None:
            self.raspberry_core_temp.set(temperature)

    def get_raspberry_core_temperature(self):
        # You need to add pi users to sudoers so it can execute the vcgencmd command
        #
        # root@octopi:/etc/sudoers.d# cat /etc/sudoers.d/octoprint-vcgencmd
        # pi ALL=NOPASSWD: /usr/bin/vcgencmd
        # root@octopi:/etc/sudoers.d#
        if not os.path.isfile('/usr/bin/vcgencmd'):
            return None
        temp = os.popen('sudo /usr/bin/vcgencmd measure_temp').readline()
        if not temp.startswith('temp='):
            self._logger.error('Failed to execute "sudo /usr/bin/vcgencmd"')
            self._logger.error('Raspberry core temperature will not be reported')
            return None
        temp = temp.replace('temp=','').replace("'C",'')
        return float(temp)

    # Temperatures
    temps_actual = Gauge('octoprint_temperatures_actual', 'Reported temperatures', ['identifier'], registry=registry)
    temps_target = Gauge('octoprint_temperatures_target', 'Targeted temperatures', ['identifier'], registry=registry)

    # Metadata
    client_num = Gauge('octoprint_client_num', 'The number of connected clients', registry=registry)
    octoprint_info = Info('octoprint_infos', 'Octoprint host informations', registry=registry)
    printer_state = Info('octoprint_printer_state', 'Printer connection info', registry=registry)

    # Statistics
    started_print_counter = Counter('octoprint_started_prints', 'Started print jobs', registry=registry)
    failed_print_counter = Counter('octoprint_failed_prints', 'Failed print jobs', registry=registry)
    done_print_counter = Counter('octoprint_done_prints', 'Done print jobs', registry=registry)
    cancelled_print_counter = Counter('octoprint_cancelled_prints', 'Cancelled print jobs', registry=registry)
    timelapse_counter = Counter('octoprint_captured_timelapses', 'Timelapse captured', registry=registry)
    slice_progress = Gauge('octoprint_slice_progress', 'Slice progress', ['path'], registry=registry)


    # Print information
    print_progress = Gauge('octoprint_print_progress', 'Print progress', ['path'], registry=registry)
    print_time_elapsed = Gauge('octoprint_print_time_elapsed', 'Print time elapsed', ['path'], registry=registry)
    print_time_est = Gauge('octoprint_print_time_est', 'Print time estimate', ['path'], registry=registry)
    print_time_left_est = Gauge('octoprint_print_time_left_estimate', 'Print time left estimate', ['path'], registry=registry)
    print_fan_speed = Gauge('octoprint_print_fan_speed', 'Fan speed', registry=registry)
    printing_time_total = Counter('octoprint_printing_time_total', 'Printing time total', registry=registry)
    
    # Extrusion
    extrusion_total = Counter('octoprint_extrusion_total', 'Filament extruded total', registry=registry)
    extrusion_print = Gauge('octoprint_extrusion_print', 'Filament extruded this print', registry=registry)

    # Movements
    x_travel_total = Counter('octoprint_x_travel_total', 'X axis travel total', registry=registry)
    x_travel_print = Gauge('octoprint_x_travel_print', 'X axis travel in this print', registry=registry)
    y_travel_total = Counter('octoprint_y_travel_total', 'Y axis travel total', registry=registry)
    y_travel_print = Gauge('octoprint_y_travel_print', 'Y axis travel in this print', registry=registry)
    z_travel_total = Counter('octoprint_z_travel_total', 'Z axis travel total', registry=registry)
    z_travel_print = Gauge('octoprint_z_travel_print', 'Z axis travel in this print', registry=registry)

    def render(self):
        return make_wsgi_app(registry=self.registry)
