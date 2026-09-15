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
