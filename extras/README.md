# Helpful Extras

Currently Cookiecutter generates the following helpful extras to this folder:

- [prometheus_exporter.md](./prometheus_exporter.md)
  Data file for plugins.octoprint.org. Fill in the missing TODOs once your
  plugin is ready for release and file a PR as described at
  http://plugins.octoprint.org/help/registering/ to get it published.

- `octoprint-grafana.json`
  Example configuration of Grafana dashboard

![Grafana dashboard](./grafana-screenshot.png)

> This folder may be safely removed if you don't need it.

## Sample GCode Files

### xyz_calibration_cube.gcode

100 x 100 x 100mm calibration cube sliced with Cura 5.1.0 with a 0,4mm nozzle, 1,75mm filament on default *Normal 0,15mm* settings.

#### Distances
* Total distance 2724,24m
  * X: 1808,27m
  * Y: 1705,05m
  * Z: 0,13m
  * E: 62,36m
* Printing distance: 2456,59m
* Travel distance: 264,65m

#### Commands
* G0/G1: 190229