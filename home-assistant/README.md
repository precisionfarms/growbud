# GrowBud Home Assistant dashboard prototype

This directory contains a YAML-mode Lovelace prototype built only from Home
Assistant's standard cards. It does not require HACS and does not change
GrowBud firmware.

## Entity-ID scope

The dashboard uses the default Home Assistant object IDs derived from the
entity names exposed by `growbud.yaml`. The repository's documented deployment
substitution (`name_prefix: "Tent 1"`) makes the EC entity
`sensor.tent_1_conductivity_ec`. That is the only dashboard entity ID whose
display name depends on a package substitution.

Home Assistant's entity registry preserves locally renamed IDs and may append a
numeric suffix after a collision. Before import, use **Settings > Devices &
services > ESPHome > GrowBud** to compare the installed IDs with the inventory
below. If the deployment uses a different `name_prefix`, replace only
`sensor.tent_1_conductivity_ec` in `dashboard.yaml` with that registered EC ID.

## Install

### Storage-mode Home Assistant (usual installation)

1. Open **Settings > Dashboards > Add dashboard** and create `GrowBud`.
2. Open the new dashboard, choose **Edit dashboard**, then **Raw configuration
   editor**.
3. Copy the complete contents of `dashboard.yaml`, save, and verify that no card
   reports an unavailable entity.

### YAML-mode Home Assistant

Copy this directory (or just `dashboard.yaml`) under the Home Assistant config
directory and add an entry like this to `configuration.yaml`:

```yaml
lovelace:
  mode: storage
  dashboards:
    growbud:
      mode: yaml
      title: GrowBud
      icon: mdi:sprout
      show_in_sidebar: true
      filename: home-assistant/dashboard.yaml
```

Restart Home Assistant or reload dashboards after validating the main
configuration.

## Source-to-dashboard inventory

| Dashboard concept | Exposed name in `growbud.yaml` | Default HA entity ID | Used in |
|---|---|---|---|
| pH | pH | `sensor.ph` | Overview, Reservoir |
| pH status | pH Measurement Status | `sensor.ph_measurement_status` | Overview, Reservoir |
| EC | `${name_prefix} Conductivity (EC)` | `sensor.tent_1_conductivity_ec`* | Overview, Reservoir |
| EC status | EC Measurement Status | `sensor.ec_measurement_status` | Overview, Reservoir |
| Reservoir level | Reservoir Level | `sensor.reservoir_level` | Overview, Reservoir |
| Reservoir volume | Reservoir Volume | `sensor.reservoir_volume` | Overview, Reservoir |
| Reservoir status | Reservoir Measurement Status | `sensor.reservoir_measurement_status` | Overview, Reservoir |
| Filtered distance | Reservoir Distance | `sensor.reservoir_distance` | Reservoir, Maintenance |
| Raw distance | Reservoir Raw Distance | `sensor.reservoir_raw_distance` | Reservoir, Maintenance |
| Read chemistry | Read Chemistry | `button.read_chemistry` | Overview, Reservoir |
| Read reservoir | Read Reservoir | `button.read_reservoir` | Overview, Reservoir |
| Safe pump | Pump (template switch) | `switch.pump` | Overview, Irrigation |
| Next pump time | Next Pump Time | `sensor.next_pump_time` | Overview, Irrigation |
| Pump duration | Pump Duration (sec) | `number.pump_duration_sec` | Overview, Irrigation |
| On interval | Lights On Pump Interval (min) | `number.lights_on_pump_interval_min` | Overview, Irrigation |
| Off interval | Lights Off Pump Interval (min) | `number.lights_off_pump_interval_min` | Overview, Irrigation |
| Manual run | Run Pump | `button.run_pump` | Overview, Irrigation |
| Lights | Lights | `switch.lights` | Overview, Lighting |
| Veg on time | Lights On Time | `select.lights_on_time` | Lighting |
| Bloom on time | Bloom Lights On Time | `select.bloom_lights_on_time` | Lighting |
| Veg duration | Veg Light Duration | `number.veg_light_duration` | Overview, Lighting |
| Bloom duration | Bloom Light Duration | `number.bloom_light_duration` | Overview, Lighting |
| Calculated on | On Time | `sensor.on_time` | Overview, Lighting |
| Calculated off | Off Time | `sensor.off_time` | Overview, Lighting |
| Start date | Start Date | `date.start_date` | Overview, Grow |
| Bloom date | Bloom Date | `sensor.bloom_date` | Overview, Grow |
| Harvest date | Harvest Date | `sensor.harvest_date` | Overview, Grow |
| Days blooming | Days Blooming | `sensor.days_blooming` | Overview, Grow |
| Veg length | Days in Veg | `number.days_in_veg` | Grow |
| Bloom length | Days in Bloom | `number.days_in_bloom` | Grow |
| Veg transition | Veg Transition | `number.veg_transition` | Grow |
| Bloom transition | Bloom Transition | `number.bloom_transition` | Grow |
| pH target | pH Target | `number.ph_target` | Grow |
| Full distance | Reservoir Full Distance | `number.reservoir_full_distance` | Reservoir |
| Empty distance | Reservoir Empty Distance | `number.reservoir_empty_distance` | Reservoir |
| Capacity | Reservoir Capacity | `number.reservoir_capacity` | Reservoir |

\* Assumes the documented `name_prefix: "Tent 1"` deployment substitution.

## Maintenance inventory

Calibration includes `button.calibrate_ph_mid` and
`button.calibrate_ph_high`. Chemistry diagnostics include
`button.read_ph`, `button.read_conductivity`, `sensor.ezo_ec_response`,
`sensor.last_stored_ph`, `sensor.tds`, `sensor.salinity`, and
`sensor.specific_gravity`. Protocol commands `button.uart_to_i2c` and
`button.i2c` are isolated below a warning and require confirmation.
Calibration commands also require confirmation.

The internal GPIO pump relay (`${id_prefix}_pump_switch`) is intentionally not
exposed by ESPHome and is not referenced. Only the product-facing template
`switch.pump` is used. No dosing UI is present.

## Known entity gaps

| Requested concept | Gap |
|---|---|
| Grow stage | No Grow Stage entity is exposed. Dates and Days Blooming are shown instead. |
| Active veg/bloom duration | Both duration controls exist, but there is no entity that identifies the active phase or active duration. Both are shown with the calculated schedule. |
| Irrigation scheduled/healthy state | Next Pump Time exists, but there is no dedicated schedule-enabled or irrigation-health entity. |
| Reservoir okay/alarm | Level and readable measurement status exist, but there is no explicit low-level or reservoir-health binary sensor. |
| Calibration result/status | Calibration buttons exist, but no calibration-result entity is exposed. |

## Prototype notes and v2 candidates

For v2, consider firmware work only as a separate task: stable explicit
`object_id` values for portable dashboard installs, active grow-stage and active
light-duration sensors, reservoir low/healthy status, irrigation scheduler
health/enabled state, and calibration feedback. Once operational ranges are
defined, gauge severity thresholds can be added without implying unsupported
limits in this prototype.
