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
    
You can also get the general prometheus configuration idea from the docker-compose file and the `docker/prometheus/prometheus.yml` file.

## Local developement/testing

There is a docker-compose file, which will start:
 - an octoprint instance on port 5000
   - !!! you should install the plugin to it
   - TODO: auto load the plugin to the newly created container
   - !!! you should add [virtual printer](https://docs.octoprint.org/en/master/development/virtual_printer.html#enabling-the-virtual-printer) to it (after the first start docker/octoprint_data/config.yaml and restart the container) 
 - a prometheus instance on port 9090
   - configured to pull the metrics from the octoprint
 - a grafana instance on port 3000
   - configured prometheus as datasource
   - user/pass is admin/foobar
   
You can start the stack with a regular `docker-compose up -d`.
