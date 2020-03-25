# OctoPrint-Prometheus-Exporter

This is a utility plugin, which enables the [prometheus server](https://prometheus.io/) to scrape metrics from your octoprint instance.
Later on, you can use data vizualisation tools (for example [grafana](https://grafana.com/)) to track and visualize your printer(s) status(es).

This plugin has no visible UI!

Currently exported metrics:
  - python version - as info
  - octoprint version, hostname, os - as info
  - actual temperature - as gauge with tool identifier label
  - target temperature - as gauge with tool identifier label
  - client number - as gauge; the actually connected clients to the host
  - printer state - as info
  - started prints - as counter
  - failed prints - as counter
  - done prints - as counter
  - cancelled prints - as counter
  - timelaps count - as counter
  - print progress - as gauge with path label
  - slice progress - as gauge with path label
  - print total time - as counter
  - last print time - as gauge
  - fan speed - as gauge
  - extrusion total - as counter
  - x, y and z travel - as a counter
  - last print extrusion - as gauge

All of the metrics are prefixed as `octoprint_` for easier identification. 

The metrics endpoint is: http://localhost:5000/plugin/prometheus_exporter/metrics (change the host+port to your actual host+port)

## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/tg44/OctoPrint-Prometheus-Exporter/archive/master.zip

## Prometheus config

Add this to the `scrape_configs` part of your `prometheus.yml`:

```
- job_name: 'octoprint'
    scrape_interval: 5s
    metrics_path: '/plugin/prometheus_exporter/metrics'
    static_configs:
      - targets: ['octoprint:80']
```

Or if you have enabled authentication:

```
 - job_name: 'octoprint'
    scrape_interval: 5s
    metrics_path: '/plugin/prometheus_exporter/metrics'
    params:
      apikey: ['__OCTOPRINT_APIKEY__']
    static_configs:
      - targets: ['octoprint:80']
```

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
