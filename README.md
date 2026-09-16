# GrowBud

`growbud.yaml` is the canonical ESPHome package for GrowBud controllers.

```yaml
substitutions:
  id_prefix: tent_1
  name_prefix: "Tent 1"
  growbud_component_source: github://precisionfarms/growbud@main
  reservoir_trigger_pin: GPIO32
  reservoir_echo_pin: GPIO33

packages:
  growbud:
    url: https://github.com/precisionfarms/growbud
    ref: main
    files: [growbud.yaml]
```

GrowBud uses ESPHome's build-environment timezone by default. When ESPHome runs
in the same correctly configured Home Assistant environment, no second timezone
setting is needed. ESPHome converts that timezone to a DST-aware POSIX rule and
embeds it in the firmware, while SNTP remains the independent source of current
time.

If firmware is built on a machine whose timezone differs from the grow site,
override the package's time component explicitly:

```yaml
time:
  - id: !extend growbud_time
    timezone: America/Denver
```

Use a local [TZ database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)
region such as `America/Denver` or `Europe/London`. Rebuild and install the
firmware after changing the timezone.

`growbud.yaml` loads the reusable `growbud` external component from the same
GitHub repository. When pinning the package to a release tag, also set
`growbud_component_source` to that tag so the YAML package and component stay
on the same version, for example `github://precisionfarms/growbud@v1.2.3`.

## Development validation

`growbud.yaml` is validated through a representative ESP32/ESP-IDF device configuration in `tests/growbud_test_device.yaml`. The fixture uses local package inclusion and contains no production credentials.

Set up the pinned validation environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

Validate the merged ESPHome configuration:

```sh
.venv/bin/esphome config tests/growbud_test_device.yaml
```

Compile the representative firmware:

```sh
.venv/bin/esphome compile tests/growbud_test_device.yaml
```

GrowBud configuration validation is tested with ESPHome 2026.8.2, the version pinned in `requirements-dev.txt`. Production device configurations should pin a released GrowBud tag rather than following `main`.

## Reservoir sensor

GrowBud's prototype reservoir monitor uses an HC-SR04 with GPIO32 for TRIG and
GPIO33 for ECHO by default. Both pins are substitutions and may be overridden by
the consuming device. Power the HC-SR04 from 5 V, connect grounds, and reduce its
5 V ECHO output to approximately 3.3 V with an appropriate divider or level
converter before connecting it to the ESP32. Software cannot make a direct 5 V
ECHO connection safe.

Set `Reservoir Full Distance`, `Reservoir Empty Distance`, and `Reservoir
Capacity` for the installed reservoir. Full distance must be less than empty
distance. Volume is a linear estimate intended for reservoirs with approximately
constant horizontal cross-section.
