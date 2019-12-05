# coding=utf-8
from __future__ import absolute_import

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin
from octoprint.util.version import get_octoprint_version_string
from prometheus_client import make_wsgi_app
from prometheus_client import Gauge
from prometheus_client import Info

class PrometheusExporterPlugin(octoprint.plugin.BlueprintPlugin,
							   octoprint.plugin.StartupPlugin):

	# TEMP
	temps_actual = Gauge('temperaturesActual', 'Reported temperatures', ['identifier'])
	temps_target = Gauge('temperaturesTarget', 'Targeted temperatures', ['identifier'])

	def get_temp_update(self, comm, parsed_temps):
		for k, v in parsed_temps.items():
			if isinstance(v, tuple) and len(v) == 2:
				self.temps_actual.labels(k).set(v[0])
				self.temps_target.labels(k).set(v[1])
		return parsed_temps

	# INFO
	octoprint_info = Info('octoprintInfos', 'Octoprint host informations')

	def on_after_startup(self):
		import socket
		import platform
		import time
		self.octoprint_info.info({
			'oxtoprint_version': get_octoprint_version_string(),
			'host': socket.gethostname(),
			'platform': platform.system(),
			'app_start': str(int(time.time())),
		})
		pass

	# ENDPOINT
	@octoprint.plugin.BlueprintPlugin.route("/metrics")
	def metrics_endpoint(self):
		return make_wsgi_app()

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

__plugin_name__ = "Prometheus Exporter Plugin"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PrometheusExporterPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.comm.protocol.temperatures.received": __plugin_implementation__.get_temp_update
	}

