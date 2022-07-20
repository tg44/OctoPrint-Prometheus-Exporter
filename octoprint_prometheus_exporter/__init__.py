# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from threading import Timer
import time
import os
import octoprint.plugin
from octoprint.util.version import get_octoprint_version_string
from octoprint.util import RepeatedTimer
from prometheus_client import Counter, Info, Gauge, make_wsgi_app, CollectorRegistry

from .gcodeparser import Gcode_parser


class PrometheusExporterPlugin(octoprint.plugin.BlueprintPlugin,
							   octoprint.plugin.StartupPlugin,
							   octoprint.plugin.ProgressPlugin,
							   octoprint.plugin.EventHandlerPlugin):

	_registry = CollectorRegistry(auto_describe=True)

	def initialize(self):
		# if the following returns None it makes no sense to create the
		# timer and fail every second
		if self.get_raspberry_core_temperature() is not None:
			self.timer = RepeatedTimer(1.0, self.report_raspberry_core_temperature)
			self.timer.start()
		else:
			self._logger.error('Failed to execute "sudo /usr/bin/vcgencmd"')
			self._logger.error('Raspberry core temperature will not be reported')
		self.parser = Gcode_parser()
		self.last_extrusion_counter = 0
		self.last_x_travel = 0
		self.last_y_travel = 0
		self.last_z_travel = 0
		self.print_progress_label = ''
		self.print_completion_timer = None
		self.print_time_start = 0
		self.print_time_end = 0


	# TEMP
	temps_actual = Gauge('octoprint_temperatures_actual', 'Reported temperatures', ['identifier'], registry=_registry)
	temps_target = Gauge('octoprint_temperatures_target', 'Targeted temperatures', ['identifier'], registry=_registry)

	def get_temp_update(self, comm, parsed_temps):
		for k, v in parsed_temps.items():
			if isinstance(v, tuple) and len(v) == 2:
				if not v[0] is None:
					self.temps_actual.labels(k).set(v[0])
				if not v[1] is None:
					self.temps_target.labels(k).set(v[1])
		return parsed_temps

	raspberry_core_temp = Gauge('octoprint_raspberry_core_temperature', 'Core temperature of Raspberry Pi', registry=_registry)
	def report_raspberry_core_temperature(self):
		temp = self.get_raspberry_core_temperature()
		if temp is not None:
			self.raspberry_core_temp.set(temp)

	def get_raspberry_core_temperature(self):
		# You need to add pi users to sudoers so it can execute the vcgencmd command
		#
		# root@octopi:/etc/sudoers.d# cat /etc/sudoers.d/octoprint-vcgencmd
		# pi ALL=NOPASSWD: /usr/bin/vcgencmd
		# root@octopi:/etc/sudoers.d#
		temp = os.popen('sudo /usr/bin/vcgencmd measure_temp').readline()
		if not temp.startswith('temp='):
			return None
		temp = temp.replace('temp=','').replace("'C",'')
		return float(temp)


	# INFO
	octoprint_info = Info('octoprint_infos', 'Octoprint host informations', registry=_registry)

	def on_after_startup(self):
		import socket
		import platform
		import time
		self.octoprint_info.info({
			'octoprint_version': get_octoprint_version_string(),
			'host': socket.gethostname(),
			'platform': platform.system(),
			'app_start': str(int(time.time())),
		})
		pass

	# CLIENT NUM
	client_num = Gauge('octoprint_client_num', 'The number of connected clients', registry=_registry)

	def clientnum_inc(self):
		self.client_num.inc()
	def clientnum_dec(self):
		self.client_num.dec()

	# PRINTER STATE
	printer_state = Info('octoprint_printer_state', 'Printer connection info', registry=_registry)

	def set_printer_info(self, payload):
		self.printer_state.info(payload)

	# PRINTING
	started_print_counter = Counter('octoprint_started_prints', 'Started print jobs', registry=_registry)
	failed_print_counter = Counter('octoprint_failed_prints', 'Failed print jobs', registry=_registry)
	done_print_counter = Counter('octoprint_done_prints', 'Done print jobs', registry=_registry)
	cancelled_print_counter = Counter('octoprint_cancelled_prints', 'Cancelled print jobs', registry=_registry)

	# TIMELAPSE
	timelapse_counter = Counter('octoprint_captured_timelapses', 'Timelapse captured', registry=_registry)

	# PRINT PROGRESS
	print_progress = Gauge('octoprint_print_progress', 'Print progress', ['path'], registry=_registry)
	print_time_elapsed = Gauge('octoprint_print_time_elapsed', 'Print time elapsed', ['path'], registry=_registry)
	print_time_est = Gauge('octoprint_print_time_est', 'Print time estimate', ['path'], registry=_registry)
	print_time_left_est = Gauge('octoprint_print_time_left_estimate', 'Print time left estimate', ['path'], registry=_registry)

	# SLICE PROGRESS
	slice_progress = Gauge('octoprint_slice_progress', 'Slice progress', ['path'], registry=_registry)

	# TOTAL PRINTING TIME
	printing_time_total = Counter('octoprint_printing_time_total', 'Printing time total', registry=_registry)

	def print_complete_callback(self):
		self.extrusion_print.set(0)
		self.x_travel_print.set(0)
		self.y_travel_print.set(0)
		self.z_travel_print.set(0)
		self.print_completion_timer = None

	def print_deregister_callback(self, label):
		if label != '':
			self.print_progress.remove(label)
			self.print_time_elapsed.remove(label)
			self.print_time_est.remove(label)
			self.print_time_left_est.remove(label)
		self.print_progress_label = ''

	def slice_deregister_callback(self, label):
		self.slice_progress.remove(label)

	def print_complete(self):
		self.printing_time_total.inc(self.print_time_end - self.print_time_start)

		# In 30 seconds, reset all the progress variables back to 0
		# At a default 10 second interval, this gives us plenty of room for Prometheus to capture the 100%
		# complete gauge.

		# TODO: Is this really a good idea?

		self.print_completion_timer = Timer(30, self.print_complete_callback)
		self.print_completion_timer.start()
		Timer(30, lambda: self.print_deregister_callback(self.print_progress_label)).start()

	def deactivateMetricsIfOffline(self, payload):
		if payload['state_id'] == 'OFFLINE':
			self.print_complete_callback()
			self.print_deregister_callback(self.print_progress_label)
			#not really safe, totally not threadsafe, but I didn't found better alternative
			try:
				self.temps_actual._metrics.clear()
				self.temps_target._metrics.clear()
			except Exception as err:
				self._logger.warning(err)


	##~~ EventHandlerPlugin mixin
	def on_event(self, event, payload):
		if event == 'ClientOpened':
			self.clientnum_inc()
		if event == 'ClientClosed':
			self.clientnum_dec()
		if event == 'PrinterStateChanged':
			self.deactivateMetricsIfOffline(payload)
			self.set_printer_info(payload)
		if event == 'PrintStarted':
			self.print_time_start = time.time()
			self.started_print_counter.inc()
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
		if event == 'PrintFailed':
			self.print_time_end = time.time()
			self.failed_print_counter.inc()
			self.print_complete()
		if event == 'PrintDone':
			self.print_time_end = time.time()
			self.done_print_counter.inc()
			self.print_complete()
		if event == 'PrintCancelled':
			self.print_time_end = time.time()
			self.cancelled_print_counter.inc()
			self.print_complete()
		if event == 'CaptureDone':
			self.timelapse_counter.inc()
		pass

	# EXTRUSION
	extrusion_total = Counter('octoprint_extrusion_total', 'Filament extruded total', registry=_registry)
	extrusion_print = Gauge('octoprint_extrusion_print', 'Filament extruded this print', registry=_registry)

	# X TRAVEL
	x_travel_total = Counter('octoprint_x_travel_total', 'X axis travel total', registry=_registry)
	x_travel_print = Gauge('octoprint_x_travel_print', 'X axis travel in this print', registry=_registry)

	# Y TRAVEL
	y_travel_total = Counter('octoprint_y_travel_total', 'Y axis travel total', registry=_registry)
	y_travel_print = Gauge('octoprint_y_travel_print', 'Y axis travel in this print', registry=_registry)

	# Z TRAVEL
	z_travel_total = Counter('octoprint_z_travel_total', 'Z axis travel total', registry=_registry)
	z_travel_print = Gauge('octoprint_z_travel_print', 'Z axis travel in this print', registry=_registry)

	# FAN SPEED
	print_fan_speed = Gauge('octoprint_print_fan_speed', 'Fan speed', registry=_registry)

	def gcodephase_hook(self, comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None, *args, **kwargs):
		if phase == "sent":
			parse_result = self.parser.process_line(cmd)
			if parse_result == "movement":
				if self.parser.extrusion_counter > self.last_extrusion_counter:
					# extrusion_total is monotonically increasing for the lifetime of the plugin
					self.extrusion_print.inc(self.parser.extrusion_counter - self.last_extrusion_counter)
					self.extrusion_total.inc(self.parser.extrusion_counter - self.last_extrusion_counter)
					self.last_extrusion_counter = self.parser.extrusion_counter

				# x_travel_print is modeled as a gauge so we can reset it after every print
				self.x_travel_print.set(self.parser.x_travel)

				if self.parser.x_travel > self.last_x_travel:
					# x_travel_total is monotonically increasing for the lifetime of the plugin
					self.x_travel_total.inc(self.parser.x_travel - self.last_x_travel)
					self.last_x_travel = self.parser.x_travel

				# y_travel_print is modeled as a gauge so we can reset it after every print
				self.y_travel_print.set(self.parser.y_travel)

				if self.parser.y_travel > self.last_y_travel:
					# y_travel_total is monotonically increasing for the lifetime of the plugin
					self.y_travel_total.inc(self.parser.y_travel - self.last_y_travel)
					self.last_y_travel = self.parser.y_travel

				# z_travel_print is modeled as a gauge so we can reset it after every print
				self.z_travel_print.set(self.parser.z_travel)

				if self.parser.z_travel > self.last_z_travel:
					# z_travel_total is monotonically increasing for the lifetime of the plugin
					self.z_travel_total.inc(self.parser.z_travel - self.last_z_travel)
					self.last_z_travel = self.parser.z_travel
			elif parse_result == "print_fan_speed":
				v = getattr(self.parser, "print_fan_speed")
				if v is not None:
					self.print_fan_speed.set(v)
			if self.print_progress_label != '':
				data = self._printer.get_current_data()
				#self._logger.info(data)
				if data['progress']['printTime'] is not None:
					self.print_time_elapsed.labels(self.print_progress_label).set(data['progress']['printTime'])
				if data['progress']['printTimeLeft'] is not None:
					self.print_time_left_est.labels(self.print_progress_label).set(data['progress']['printTimeLeft'])
				if data['job']['estimatedPrintTime'] is not None:
					self.print_time_est.labels(self.print_progress_label).set(data['job']['estimatedPrintTime'])

		return None  # no change

	##~~ ProgressPlugin mixin
	def on_print_progress(self, storage, path, progress):
		self.print_progress_label = path
		self.print_progress.labels(path).set(progress)
		pass
	def	on_slicing_progress(self, slicer, source_location, source_path, destination_location, destination_path, progress):
		self.slice_progress.labels(source_path).set(progress)
		if progress >= 100:
			Timer(30, lambda: self.slice_deregister_callback(source_path)).start()
		pass

	# ENDPOINT
	@octoprint.plugin.BlueprintPlugin.route("/metrics")
	@octoprint.access.permissions.Permissions.PLUGIN_PROMETHEUS_EXPORTER_METRICS.require(403)
	def metrics_endpoint(self):
		return make_wsgi_app(registry=self._registry)

	##~~ Softwareupdate hook
	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			prometheus_exporter=dict(
				displayName="Prometheus Exporter Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="tg44",
				repo="OctoPrint-Prometheus-Exporter",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/tg44/OctoPrint-Prometheus-Exporter/archive/{target_version}.zip"
			)
		)
	
	def is_blueprint_protected(self):
		# Disable global protection, use permission system.
		return False

__plugin_name__ = "Prometheus Exporter Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"

def get_additional_permissions(*args, **kwargs):
    return [
        dict(key="METRICS",
             name="Metrics access",
             description="Allow access to Prometheus metrics. Includes the Status permission.",
             roles=["metrics"],
             dangerous=False,
             default_groups=[octoprint.access.USER_GROUP],
			 permissions=["STATUS"]),
    ]

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PrometheusExporterPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.comm.protocol.temperatures.received": __plugin_implementation__.get_temp_update,
		"octoprint.comm.protocol.gcode.sent": __plugin_implementation__.gcodephase_hook,
		"octoprint.access.permissions": get_additional_permissions
	}
