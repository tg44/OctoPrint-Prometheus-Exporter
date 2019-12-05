# OctoPrint-Prometheus-Exporter

This is a utility plugin, which enables the [prometheus server](https://prometheus.io/) to scrape metrics from your octoprint instance.
Later on, you can use data vizualisation tools (for example [grafana](https://grafana.com/)) to track and visualize your printer(s) status(es).

This plugin has no visible UI!

Currently exported metrics:
 - python version - as info
 - octoprint version, hostname, os - as info
 - actual temperature - as gauge with tool identifier label
 - target temperature - as gauge with tool identifier label
 
The metrics endpoint is: http://localhost:5000/plugin/prometheus_exporter/metrics (change the host+port to your actual host+port)

## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/tg44/OctoPrint-Prometheus-Exporter/archive/master.zip
