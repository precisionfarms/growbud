# GrowBud

`growbud.yaml` is the canonical ESPHome package for GrowBud controllers.

```yaml
substitutions:
  id_prefix: tent_1
  name_prefix: "Tent 1"
  timezone: America/Denver

packages:
  growbud:
    url: https://github.com/precisionfarms/growbud
    ref: main
    files: [growbud.yaml]
```

Set `timezone` to the controller's local [TZ database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) region, such as `America/Denver` or `Europe/London`.

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

GrowBud configuration validation is tested with ESPHome 2025.5.0, the version pinned in `requirements-dev.txt`. Production device configurations should pin a released GrowBud tag rather than following `main`.
