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

	def initialize(self):
		# if the following returns None it makes no sense to create the
		# timer and fail every second
		self.metrics = Metrics(logger=self._logger)
		self.parser = Gcode_parser()
		self.last_extrusion_counter = 0
		self.last_x_travel = 0
		self.last_y_travel = 0
		self.last_z_travel = 0
		self.print_progress_label = ''
		self.print_completion_timer = None
		self.print_time_start = 0

	def get_temp_update(self, comm, parsed_temps):
		for k, v in parsed_temps.items():
			if isinstance(v, tuple) and len(v) == 2:
				if not v[0] is None:
					self.metrics.temps_actual.labels(k).set(v[0])
				if not v[1] is None:
					self.metrics.temps_target.labels(k).set(v[1])
		return parsed_temps

	def on_after_startup(self):
		self.metrics.octoprint_info.info({
			'octoprint_version': get_octoprint_version_string(),
			'host': self._settings.get(['appearance', 'name']) or 'OctoPrint',
			'platform': get_os(),
			'app_start': str(int(time.time()))
		})

	def print_complete_callback(self):
		self.metrics.print_complete()
		self.print_completion_timer = None

	def print_deregister_callback(self, label):
		if label != '':
			self.metrics.print_progress.remove(label)
			self.metrics.print_time_elapsed.remove(label)
			self.metrics.print_time_est.remove(label)
			self.metrics.print_time_left_est.remove(label)
		self.print_progress_label = ''

	def slice_deregister_callback(self, label):
		self.metrics.slice_progress.remove(label)

	def print_complete(self):
		self.metrics.printing_time_total.inc(time.time() - self.print_time_start)

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
				self.metrics.temps_actual._metrics.clear()
				self.metrics.temps_target._metrics.clear()
			except Exception as err:
				self._logger.warning(err)

	##~~ EventHandlerPlugin mixin
	def on_event(self, event, payload):
		if event == 'ClientOpened':
			self.metrics.client_num.inc()
		if event == 'ClientClosed':
			self.metrics.client_num.dec()
		if event == 'PrinterStateChanged':
			self.deactivateMetricsIfOffline(payload)
			self.metrics.printer_state.info(payload)
		if event == 'PrintStarted':
			self.print_time_start = time.time()
			self.metrics.started_print_counter.inc()
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
			self.metrics.failed_print_counter.inc()
			self.print_complete()
		if event == 'PrintDone':
			self.metrics.done_print_counter.inc()
			self.print_complete()
		if event == 'PrintCancelled':
			self.metrics.cancelled_print_counter.inc()
			self.print_complete()
		if event == 'CaptureDone':
			self.metrics.timelapse_counter.inc()
		pass

	def gcodephase_hook(self, comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None, *args, **kwargs):
		if phase == "sent":
			parse_result = self.parser.process_line(cmd)
			if parse_result == "movement":
				if self.parser.extrusion_counter > self.last_extrusion_counter:
					# extrusion_total is monotonically increasing for the lifetime of the plugin
					self.metrics.extrusion_print.inc(self.parser.extrusion_counter - self.last_extrusion_counter)
					self.metrics.extrusion_total.inc(self.parser.extrusion_counter - self.last_extrusion_counter)
					self.last_extrusion_counter = self.parser.extrusion_counter
				self.metrics.current_e.set(self.parser.e)

				# x_travel_print is modeled as a gauge so we can reset it after every print
				self.metrics.x_travel_print.set(self.parser.x_travel)
				self.metrics.current_x.set(self.parser.x)

				if self.parser.x_travel > self.last_x_travel:
					# x_travel_total is monotonically increasing for the lifetime of the plugin
					self.metrics.x_travel_total.inc(self.parser.x_travel - self.last_x_travel)
					self.last_x_travel = self.parser.x_travel

				# y_travel_print is modeled as a gauge so we can reset it after every print
				self.metrics.y_travel_print.set(self.parser.y_travel)
				self.metrics.current_y.set(self.parser.y)

				if self.parser.y_travel > self.last_y_travel:
					# y_travel_total is monotonically increasing for the lifetime of the plugin
					self.metrics.y_travel_total.inc(self.parser.y_travel - self.last_y_travel)
					self.last_y_travel = self.parser.y_travel

				# z_travel_print is modeled as a gauge so we can reset it after every print
				self.metrics.z_travel_print.set(self.parser.z_travel)
				self.metrics.current_z.set(self.parser.z)

				if self.parser.z_travel > self.last_z_travel:
					# z_travel_total is monotonically increasing for the lifetime of the plugin
					self.metrics.z_travel_total.inc(self.parser.z_travel - self.last_z_travel)
					self.last_z_travel = self.parser.z_travel
			elif parse_result == "print_fan_speed":
				v = getattr(self.parser, "print_fan_speed")
				if v is not None:
					self.metrics.print_fan_speed.set(v)
			if self.print_progress_label != '':
				data = self._printer.get_current_data()
				#self._logger.info(data)
				if data['progress']['printTime'] is not None:
					self.metrics.print_time_elapsed.labels(self.print_progress_label).set(data['progress']['printTime'])
				if data['progress']['printTimeLeft'] is not None:
					self.metrics.print_time_left_est.labels(self.print_progress_label).set(data['progress']['printTimeLeft'])
				if data['job']['estimatedPrintTime'] is not None:
					self.metrics.print_time_est.labels(self.print_progress_label).set(data['job']['estimatedPrintTime'])

		return None  # no change

	##~~ ProgressPlugin mixin
	def on_print_progress(self, storage, path, progress):
		self.print_progress_label = path
		self.metrics.print_progress.labels(path).set(progress)
		pass
	def	on_slicing_progress(self, slicer, source_location, source_path, destination_location, destination_path, progress):
		self.metrics.slice_progress.labels(source_path).set(progress)
		if progress >= 100:
			Timer(30, lambda: self.slice_deregister_callback(source_path)).start()
		pass

	# ENDPOINT
	@octoprint.plugin.BlueprintPlugin.route("/metrics")
	@Permissions.PLUGIN_PROMETHEUS_EXPORTER_SCRAPE.require(403)
	def metrics_endpoint(self):
		return self.metrics.render()

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

	def get_additional_permissions(self):
		return [{
			"key": "SCRAPE",
			"name": "Metrics access",
			"description": "Allow access to Prometheus metrics.",
			"dangerous": False,
			"default_groups": [USER_GROUP],
			"roles": ["scrape"],
			"permissions": ["STATUS"]
		}]

__plugin_name__ = "Prometheus Exporter Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PrometheusExporterPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.comm.protocol.temperatures.received": __plugin_implementation__.get_temp_update,
		"octoprint.comm.protocol.gcode.sent": __plugin_implementation__.gcodephase_hook,
		"octoprint.access.permissions": __plugin_implementation__.get_additional_permissions
	}
