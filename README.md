# OctoPrint-Prometheus-Exporter

This is a utility plugin, which allows to scrape metrics from your OctoPrint instance using [Prometheus](https://prometheus.io/).
Later on, you can use data vizualisation tools (for example [Grafana](https://grafana.com/)) to track and visualize your printer(s) status(es).

This plugin has no visible UI!

## Metrics

All metrics are prefixed as `octoprint_` for easier identification. Metrics for distance and temperature are showed in the units configured in the 3D printer firmware.

The metrics endpoint is: /plugin/prometheus_exporter/metrics. If your OctoPrint runs on localhost:5000 this leads to http://localhost:5000/plugin/prometheus_exporter/metrics as scrape target.

### Server

* `octoprint_server_timelapses`: Counter, captured timelapses.
* `octoprint_server_slice_progress`: Gauge, slicing progress.
* `octoprint_server_clients`: Gauge, connected clients.
* `octoprint_server_info`: Info, server information.
  * Contains labels `app_start`, `host`, `octoprint_version`, `platform`

### Jobs

* `octoprint_jobs_time_seconds`: Counter, combined printing time in seconds.
* `octoprint_jobs_started`: Counter, amount of started prints.
* `octoprint_jobs_failed`: Counter, amount of failed prints.
* `octoprint_jobs_done`: Counter, amount of finished prints.
* `octoprint_jobs_cancelled`: Counter, amount of cancelled prints.

### Printer

* `octoprint_printer_travel_x`: Gauge, printer travel on X axis.
* `octoprint_printer_travel_y`: Gauge, printer travel on Y axis.
* `octoprint_printer_travel_z`: Gauge, printer travel on Z axis.
* `octoprint_printer_extrusion`: Gauge, printer filament extrusion.
* `octoprint_printer_state`: Gauge, printer connection info.
* `octoprint_printer_fan_speed`: Gauge, fan speed.
* `octoprint_printer_temperatures_actual`: Gauge, reported temperatures.
* `octoprint_printer_temperatures_target`: Gauge, targeted temperatures.

### Job

* `octoprint_job_travel_x`: Gauge, print job travel on X axis.
* `octoprint_job_travel_y`: Gauge, print job travel on Y axis.
* `octoprint_job_travel_z`: Gauge, print job travel on Z axis.
* `octoprint_job_progress`: Gauge, print job progress.
* `octoprint_job_extrusion`: Gauge, print job filament extrusion.
* `octoprint_job_time_elapsed_seconds`: Gauge, print job time elapsed in seconds.
* `octoprint_job_time_est_seconds`: Gauge, print job time estimate in seconds.
* `octoprint_job_time_left_estimate_seconds`: Gauge, print job time left estimate in seconds.

### RaspberryPi

* `octoprint_raspberry_core_temperature`: Gauge, core temperature of Raspberry Pi.

You need to add the `pi` users to sudoers so it can execute the vcgencmd command without password. Create a file `/etc/sudoers.d/octoprint-vcgencmd` with
```
pi ALL=NOPASSWD: /usr/bin/vcgencmd
```

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

### Permission system

New in version 0.2.0: by default all users / operators have access to the metrics endpoint. If you want to make metrics accessible to anonymous users (guests) without disabling your entire authentication system simply add the metrics permission to the guest user group.

## Local developement/testing

There is a docker-compose file, which will start:
 - an octoprint instance on port 5000
   - !!! you should install the plugin to it
   - TODO: auto load the plugin to the newly created container
   - !!! you should add [virtual printer](https://docs.octoprint.org/en/master/development/virtual_printer.html#enabling-the-virtual-printer) to it (after the first start docker/octoprint_data/config.yaml and restart the container)
   - without docker:
     - clone
     - cd to the dir
     - virtualenv --python=/usr/bin/python3 venv3
     - source venv3/bin/activate
     - pip install "OctoPrint>=1.4.0"
     - pip install -e .
     - octoprint serve --debug
     - (on mac there could be a hidden "give me a root password" line)
 - a prometheus instance on port 9090
   - configured to pull the metrics from the octoprint
 - a grafana instance on port 3000
   - configured prometheus as datasource
   - user/pass is admin/foobar

You can start the stack with a regular `docker-compose up -d`.
