"""Prometheus metrics class"""
import os
import typing
from prometheus_client import Counter, Info, Gauge, make_wsgi_app, CollectorRegistry
from octoprint.util import RepeatedTimer


class Metrics:
    """Prometheus metrics class."""

    registry = CollectorRegistry(auto_describe=True)

    # Server
    server_timelapses = Counter(
        'octoprint_server_timelapses',
        'Timelapse captured',
        registry=registry)

    server_slice_progress = Gauge(
        'octoprint_server_slice_progress',
        'Slice progress',
        ['path'],
        registry=registry)

    server_clients = Gauge(
        'octoprint_server_clients',
        'The number of connected clients',
        registry=registry)

    server_info = Info(
        'octoprint_server_info',
        'Server information',
        registry=registry)

    # Jobs
    jobs_time_total = Counter(
        'octoprint_jobs_time_seconds',
        'Total printing time in seconds',
        registry=registry)

    jobs_started = Counter(
        'octoprint_started_prints',
        'Started print jobs',
        registry=registry)

    jobs_failed = Counter(
        'octoprint_failed_prints',
        'Failed print jobs',
        registry=registry)

    jobs_done = Counter(
        'octoprint_done_prints',
        'Done print jobs',
        registry=registry)

    jobs_cancelled = Counter(
        'octoprint_cancelled_prints',
        'Cancelled print jobs',
        registry=registry)

    # Printer
    printer_travel_x = Counter(
        'octoprint_printer_travel_x',
        'Printer travel on X axis.',
        registry=registry)

    printer_travel_y = Counter(
        'octoprint_printer_travel_y',
        'Printer travel on Y axis',
        registry=registry)

    printer_travel_z = Counter(
        'octoprint_printer_travel_z',
        'Printer travel on Z axis',
        registry=registry)

    printer_extrusion = Counter(
        'octoprint_printer_extrusion',
        'Printer filament extrusion',
        registry=registry)

    printer_state = Info(
        'octoprint_printer_state',
        'Printer connection info',
        registry=registry)

    printer_fan_speed = Gauge(
        'octoprint_printer_fan_speed',
        'Fan speed',
        registry=registry)

    printer_temps_actual = Gauge(
        'octoprint_printer_temperatures_actual',
        'Reported temperatures',
        ['identifier'],
        registry=registry)

    printer_temps_target = Gauge(
        'octoprint_printer_temperatures_target',
        'Targeted temperatures',
        ['identifier'],
        registry=registry)

    # Job
    job_travel_x = Gauge(
        'octoprint_job_travel_x',
        'Print job travel on X axis',
        registry=registry)

    job_travel_y = Gauge(
        'octoprint_job_travel_y',
        'Print job travel on Y axis',
        registry=registry)

    job_travel_z = Gauge(
        'octoprint_job_travel_z',
        'Print job travel on Z axis', registry=registry)

    job_progress = Gauge(
        'octoprint_job_progress',
        'Print job progress',
        ['path'],
        registry=registry)

    job_extrusion = Gauge(
        'octoprint_job_extrusion',
        'Print job filament extrusion',
        registry=registry)

    job_time_elapsed = Gauge(
        'octoprint_job_time_elapsed_seconds',
        'Print job time elapsed in seconds.',
        ['path'],
        registry=registry)

    job_time_est = Gauge(
        'octoprint_job_time_est_seconds',
        'Print job time estimate in seconds.',
        ['path'],
        registry=registry)

    job_time_left_est = Gauge(
        'octoprint_job_time_left_estimate_seconds',
        'Print job time left estimate in seconds.',
        ['path'],
        registry=registry)

    def __init__(self, logger):
        self._logger = logger
        if self.get_raspberry_core_temperature() is not None:
            self.raspberry_core_temp = Gauge(
                'octoprint_raspberry_core_temperature',
                'Core temperature of Raspberry Pi',
                registry=self.registry)
            self.timer = RepeatedTimer(1.0, self.report_raspberry_core_temperature)
            self.timer.start()
        else:
            self._logger.info('Raspberry core temperature is not supported on this system')

    def report_raspberry_core_temperature(self):
        """Set the RPi core temperature in the registry."""
        temperature = self.get_raspberry_core_temperature()
        if temperature is not None:
            self.raspberry_core_temp.set(temperature)

    def get_raspberry_core_temperature(self) -> typing.Union[None, float]:
        """Get the RPI core temperature.

        You need to add pi users to sudoers so it can execute the vcgencmd command.

        root@octopi:/etc/sudoers.d# cat /etc/sudoers.d/octoprint-vcgencmd
        pi ALL=NOPASSWD: /usr/bin/vcgencmd
        root@octopi:/etc/sudoers.d#
        """
        if not os.path.isfile('/usr/bin/vcgencmd'):
            return None
        temp = os.popen('sudo /usr/bin/vcgencmd measure_temp').readline()
        if not temp.startswith('temp='):
            self._logger.error('Failed to execute "sudo /usr/bin/vcgencmd"')
            self._logger.error('Raspberry core temperature will not be reported')
            return None
        temp = temp.replace('temp=','').replace("'C",'')
        return float(temp)

    def job_complete(self):
        """Reset all counters relates to print jobs."""
        self.job_extrusion.set(0)
        self.job_travel_x.set(0)
        self.job_travel_y.set(0)
        self.job_travel_z.set(0)

    def render(self):
        """Return the current Prometheus metrics."""
        return make_wsgi_app(registry=self.registry)
