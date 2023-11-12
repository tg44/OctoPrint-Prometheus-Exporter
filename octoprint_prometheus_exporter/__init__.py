"""PrometheusExporterPlugin module."""
# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from threading import Timer
import time
import octoprint.plugin
from octoprint.access.permissions import Permissions
from octoprint.access import USER_GROUP
from octoprint.util.version import get_octoprint_version_string
from octoprint.util.platform import get_os
from .metrics import Metrics
from .gcodeparser import Gcode_parser


class PrometheusExporterPlugin(octoprint.plugin.BlueprintPlugin,
                               octoprint.plugin.StartupPlugin,
                               octoprint.plugin.ProgressPlugin,
                               octoprint.plugin.SettingsPlugin,
                               octoprint.plugin.EventHandlerPlugin):
    """PrometheusExporter plugin class"""

    def initialize(self):
        """Initialize plugin."""
        self.metrics = Metrics(logger=self._logger)
        self.parser = Gcode_parser()
        self.last_extrusion_counter = 0
        self.last_x_travel = 0
        self.last_y_travel = 0
        self.last_z_travel = 0
        self.print_progress_label = ''
        self.print_completion_timer = None
        self.print_time_start = 0

    def on_temp_received(self, comm, parsed_temps: dict) -> dict:
        """Process parsed temperature updates"""
        for k, v in parsed_temps.items():
            if isinstance(v, tuple) and len(v) == 2:
                if not v[0] is None:
                    self.metrics.printer_temps_actual.labels(k).set(v[0])
                if not v[1] is None:
                    self.metrics.printer_temps_target.labels(k).set(v[1])
        return parsed_temps

    def on_after_startup(self):
        """Set information endpoint after startup."""
        self.metrics.server_info.info({
            'octoprint_version': get_octoprint_version_string(),
            'host': self._settings.get(['appearance', 'name']) or 'OctoPrint',
            'platform': get_os(),
            'app_start': str(int(time.time()))
        })

    def on_job_complete_callback(self):
        """Printjob complete callback"""
        self.metrics.job_complete()
        self.print_completion_timer = None

    def print_deregister_callback(self, label):
        """Deregister job metrics callback"""
        if label != '':
            self.metrics.job_progress.remove(label)
            self.metrics.job_time_elapsed.remove(label)
            self.metrics.job_time_est.remove(label)
            self.metrics.job_time_left_est.remove(label)
        self.print_progress_label = ''

    def slice_deregister_callback(self, label):
        """Deregister slice metrics callback"""
        self.metrics.server_slice_progress.remove(label)

    def on_job_complete(self):
        """Actions to perform on job complete event"""
        self.metrics.jobs_time_total.inc(time.time() - self.print_time_start)

        # In 30 seconds, reset all the progress variables back to 0
        # At a default 10 second interval, this gives us plenty of room for Prometheus to capture the 100%
        # complete gauge.

        # TODO: Is this really a good idea?

        self.print_completion_timer = Timer(30, self.on_job_complete_callback)
        self.print_completion_timer.start()
        Timer(30, lambda: self.print_deregister_callback(self.print_progress_label)).start()

    def on_printer_offline(self, payload):
        """Actions to perform if printer goes offline"""
        if payload['state_id'] == 'OFFLINE':
            self.on_job_complete_callback()
            self.print_deregister_callback(self.print_progress_label)
            #not really safe, totally not threadsafe, but I didn't found better alternative
            try:
                self.metrics.printer_temps_actual._metrics.clear()
                self.metrics.printer_temps_target._metrics.clear()
            except Exception as err:
                self._logger.warning(err)

    def on_print_started(self):
        """On print started actions."""
        self.print_time_start = time.time()
        self.metrics.jobs_started.inc()
        # If there's a completion timer running, kill it.
        if self.print_completion_timer:
            self.print_completion_timer.cancel()
            self.print_completion_timer = None
        # reset the extrusion counter
        self.parser.reset()
        self.last_extrusion_counter = 0
        self.last_x_travel = 0
        self.last_y_travel = 0
        self.last_z_travel = 0

    def on_state_changed(self):
        """On printer state changed."""
        self.on_printer_offline(payload)
        self.metrics.printer_state.info(payload)

    def on_event(self, event: str, payload: dict):
        """Event callback.

        Called by the EventHandlerPlugin.
        """
        if event == 'ClientOpened':
            self.metrics.server_clients.inc()
        if event == 'ClientClosed':
            self.metrics.server_clients.dec()
        if event == 'PrinterStateChanged':
            self.on_state_changed()
        if event == 'PrintStarted':
            self.on_print_started()
        if event == 'PrintFailed':
            self.metrics.jobs_failed.inc()
            self.on_job_complete()
        if event == 'PrintDone':
            self.metrics.jobs_done.inc()
            self.on_job_complete()
        if event == 'PrintCancelled':
            self.metrics.jobs_cancelled.inc()
            self.on_job_complete()
        if event == 'CaptureDone':
            self.metrics.server_timelapses.inc()

    def process_travel_x(self, travel_x):
        """Process travel in X direction"""
        self.metrics.job_travel_x.set(travel_x)
        if travel_x > self.last_x_travel:
            self.metrics.printer_travel_x.inc(travel_x - self.last_x_travel)
            self.last_x_travel = travel_x

    def process_travel_y(self, travel_y):
        """Process travel in Y direction"""
        self.metrics.job_travel_y.set(travel_y)
        if travel_y > self.last_y_travel:
            self.metrics.printer_travel_y.inc(travel_y - self.last_y_travel)
            self.last_y_travel = travel_y

    def process_travel_z(self, travel_z):
        """Process travel in Z direction"""
        self.metrics.job_travel_z.set(travel_z)
        if travel_z > self.last_z_travel:
            self.metrics.printer_travel_z.inc(travel_z - self.last_z_travel)
            self.last_z_travel = travel_z

    def process_extrusion(self, extrusion):
        """Process extrusion"""
        if extrusion > self.last_extrusion_counter:
            self.metrics.job_extrusion.inc(extrusion - self.last_extrusion_counter)
            self.metrics.printer_extrusion.inc(extrusion - self.last_extrusion_counter)
            self.last_extrusion_counter = extrusion

    def on_gcode_sent(self, comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None, *args, **kwargs):
        """GCode callback."""
        if phase == "sent":
            parse_result = self.parser.process_line(cmd)
            if parse_result == "movement":
                self.process_travel_x(self.parser.x_travel)
                self.process_travel_y(self.parser.y_travel)
                self.process_travel_z(self.parser.z_travel)
                self.process_extrusion(self.parser.extrusion_counter)
            elif parse_result == "print_fan_speed":
                v = getattr(self.parser, "print_fan_speed")
                if v is not None:
                    self.metrics.printer_fan_speed.set(v)
            if self.print_progress_label != '':
                data = self._printer.get_current_data()
                #self._logger.info(data)
                if data['progress']['printTime'] is not None:
                    self.metrics.job_time_elapsed.labels(self.print_progress_label).set(data['progress']['printTime'])
                if data['progress']['printTimeLeft'] is not None:
                    self.metrics.job_time_left_est.labels(self.print_progress_label).set(data['progress']['printTimeLeft'])
                if data['job']['estimatedPrintTime'] is not None:
                    self.metrics.job_time_est.labels(self.print_progress_label).set(data['job']['estimatedPrintTime'])

        return None  # no change

    def on_print_progress(self, storage: str, path: str, progress: int):
        """Print progress callback"""
        self.metrics.print_progress_label = path
        self.metrics.job_progress.labels(path).set(progress)

    def	on_slicing_progress(self,
                            slicer: str,
                            source_location: str,
                            source_path: str,
                            destination_location: str,
                            destination_path: str,
                            progress: int):
        """Slicing progress callback"""
        self.metrics.server_slice_progress.labels(source_path).set(progress)
        if progress >= 100:
            Timer(30, lambda: self.slice_deregister_callback(source_path)).start()

    @octoprint.plugin.BlueprintPlugin.route('/metrics')
    @Permissions.PLUGIN_PROMETHEUS_EXPORTER_SCRAPE.require(403)
    def metrics_endpoint(self):
        """Metrics API endpoint"""
        return self.metrics.render()

    def get_update_information(self) -> dict:
        """Define the configuration for your plugin to use with the Software Update Plugin.

        See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update for details.
        """
        return {'prometheus_exporter':{
            'displayName': 'Prometheus Exporter Plugin',
            'displayVersion': self._plugin_version,
            'type': 'github_release',
            'user': 'tg44',
            'repo': 'OctoPrint-Prometheus-Exporter',
            'current': self._plugin_version,
            'pip':
                'https://github.com/tg44/OctoPrint-Prometheus-Exporter/archive/{target_version}.zip'
        }}

    def is_blueprint_protected(self) -> bool:
        """Disable global protection, use permission system."""
        return False

    def get_additional_permissions(self) -> list:
        """Register permissions for this plugin"""
        return [{
            'key': 'SCRAPE',
            'name': 'Metrics access',
            'description': 'Allow access to Prometheus metrics.',
            'dangerous': False,
            'default_groups': [USER_GROUP],
            'roles': ['scrape'],
            'permissions': ['STATUS']
        }]


__plugin_name__ = 'Prometheus Exporter Plugin'
__plugin_pythoncompat__ = '>=2.7,<4'


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PrometheusExporterPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        'octoprint.plugin.softwareupdate.check_config': __plugin_implementation__.get_update_information,
        'octoprint.comm.protocol.temperatures.received': __plugin_implementation__.on_temp_received,
        'octoprint.comm.protocol.gcode.sent': __plugin_implementation__.on_gcode_sent,
        'octoprint.access.permissions': __plugin_implementation__.get_additional_permissions
    }
