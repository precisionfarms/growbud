#include <cassert>
#include <cmath>

#include "components/growbud/growbud.h"
#include "esphome/components/time/posix_tz.h"

using esphome::ESPTime;
using namespace esphome::growbud;

namespace {

ESPTime local_time(int year, int month, int day, int hour, int minute = 0) {
  ESPTime value{};
  value.year = year;
  value.month = month;
  value.day_of_month = day;
  value.hour = hour;
  value.minute = minute;
  value.recalc_timestamp_local();
  return ESPTime::from_epoch_local(value.timestamp);
}

std::string local_string(time_t timestamp) {
  return ESPTime::from_epoch_local(timestamp).strftime("%Y-%m-%d %H:%M");
}

void test_lighting() {
  const auto bloom = GrowBudComponent::calculate_lighting_schedule(local_time(2026, 9, 15, 12), 5, 13.0f);
  assert(bloom.lights_should_be_on);
  assert(local_string(bloom.window_start) == "2026-09-15 05:00");
  assert(local_string(bloom.window_off) == "2026-09-15 18:00");

  const auto fractional = GrowBudComponent::calculate_lighting_schedule(local_time(2026, 9, 15, 23, 15), 5, 18.5f);
  assert(fractional.lights_should_be_on);
  assert(local_string(fractional.window_off) == "2026-09-15 23:30");

  const auto overnight = GrowBudComponent::calculate_lighting_schedule(local_time(2026, 9, 16, 1), 20, 18.0f);
  assert(overnight.lights_should_be_on);
  assert(local_string(overnight.window_start) == "2026-09-15 20:00");
  assert(local_string(overnight.window_off) == "2026-09-16 14:00");
  assert(!GrowBudComponent::calculate_lighting_schedule(local_time(2026, 9, 16, 14, 1), 20, 18.0f)
              .lights_should_be_on);

  assert(local_string(GrowBudComponent::calculate_lighting_schedule(local_time(2026, 7, 15, 12), 5, 13.0f)
                          .window_start) == "2026-07-15 05:00");
  assert(local_string(GrowBudComponent::calculate_lighting_schedule(local_time(2026, 1, 15, 12), 5, 13.0f)
                          .window_start) == "2026-01-15 05:00");

  const auto spring = GrowBudComponent::calculate_lighting_schedule(local_time(2026, 3, 8, 1), 20, 18.0f);
  assert(spring.lights_should_be_on);
  assert(local_string(spring.window_start) == "2026-03-07 20:00");
  assert(local_string(spring.window_off) == "2026-03-08 15:00");
  const auto fall = GrowBudComponent::calculate_lighting_schedule(local_time(2026, 11, 1, 1), 20, 18.0f);
  assert(fall.lights_should_be_on);
  assert(local_string(fall.window_start) == "2026-10-31 20:00");
  assert(local_string(fall.window_off) == "2026-11-01 13:00");
}

void test_grow_cycle() {
  auto cycle = GrowBudComponent::calculate_grow_cycle(local_time(2026, 9, 15, 0), 30, 60);
  assert(cycle.bloom.strftime("%Y-%m-%d") == "2026-10-15");
  assert(cycle.harvest.strftime("%Y-%m-%d") == "2026-12-14");
  assert(GrowBudComponent::calculate_grow_cycle(local_time(2026, 2, 15, 0), 30, 60)
             .bloom.strftime("%Y-%m-%d") == "2026-03-17");
  assert(GrowBudComponent::calculate_grow_cycle(local_time(2026, 10, 15, 0), 30, 60)
             .bloom.strftime("%Y-%m-%d") == "2026-11-14");
  assert(GrowBudComponent::calculate_grow_cycle(local_time(2026, 12, 15, 0), 30, 60)
             .bloom.strftime("%Y-%m-%d") == "2027-01-14");
}

void test_chemistry() {
  ChemistryState chemistry;
  assert(chemistry.ph_status(0) == MeasurementStatus::UNAVAILABLE);
  assert(chemistry.ec_status(0) == MeasurementStatus::UNAVAILABLE);
  assert(chemistry.record_ph(6.25f, 1000));
  assert(chemistry.record_ec(1450.0f, 2000));
  assert(chemistry.ph_status(181000) == MeasurementStatus::VALID);
  assert(chemistry.ph_status(181001) == MeasurementStatus::STALE);
  assert(chemistry.ec_status(182001) == MeasurementStatus::STALE);
  assert(chemistry.record_ph(6.3f, 200000));
  assert(chemistry.ph_status(200001) == MeasurementStatus::VALID);
  assert(!chemistry.record_ec(NAN, 200000));
  assert(chemistry.ec_status(200001) == MeasurementStatus::UNAVAILABLE);
  assert(chemistry.record_ec(1451.0f, 200002));
  assert(chemistry.ec_status(200003) == MeasurementStatus::VALID);
}

void test_irrigation_and_pump() {
  IrrigationSchedule irrigation;
  auto initial = irrigation.evaluate(1000, 20, false);
  assert(initial.next_run == 2200 && !initial.run_due && initial.initialized);
  auto due = irrigation.evaluate(2200, 20, false);
  assert(due.next_run == 3400 && due.run_due && !due.initialized);
  irrigation.reset();
  assert(irrigation.evaluate(1000, 60, false).next_run == 4600);
  irrigation.reset();
  irrigation.evaluate(1000, 20, false);
  auto blocked = irrigation.evaluate(2200, 20, true);
  assert(blocked.next_run == 2200 && !blocked.run_due);

  assert(PumpState::bounded_duration_seconds(0) == 1);
  assert(PumpState::bounded_duration_seconds(301) == 300);
  PumpState pump;
  assert(pump.begin(60, 1000));
  assert(!pump.begin(60, 1001));
  assert(!pump.watchdog_should_stop(true, 60999));
  assert(pump.watchdog_should_stop(true, 61000));
  assert(pump.begin(60, UINT32_MAX - 1000));
  assert(!pump.watchdog_should_stop(true, 58000));
  assert(pump.watchdog_should_stop(true, 59000));
}

void test_reservoir() {
  ReservoirState reservoir;
  assert(reservoir.status(10.0f, 50.0f) == MeasurementStatus::UNAVAILABLE);
  assert(std::isnan(reservoir.level_fraction(10.0f, 50.0f)));
  assert(std::isnan(reservoir.volume_gallons(10.0f, 50.0f, 20.0f)));

  reservoir.measurement_requested();
  assert(reservoir.record_distance(10.0f));
  assert(reservoir.level_fraction(10.0f, 50.0f) == 1.0f);
  assert(reservoir.volume_gallons(10.0f, 50.0f, 20.0f) == 20.0f);
  assert(reservoir.status(10.0f, 50.0f) == MeasurementStatus::VALID);

  ReservoirState empty;
  assert(empty.record_distance(50.0f));
  assert(empty.level_fraction(10.0f, 50.0f) == 0.0f);
  ReservoirState midpoint;
  assert(midpoint.record_distance(30.0f));
  assert(std::fabs(midpoint.level_fraction(10.0f, 50.0f) - 0.5f) < 0.0001f);
  assert(midpoint.volume_gallons(10.0f, 50.0f, 20.0f) == 10.0f);
  ReservoirState three_quarters;
  assert(three_quarters.record_distance(20.0f));
  assert(three_quarters.volume_gallons(10.0f, 50.0f, 20.0f) == 15.0f);

  ReservoirState clamped_full;
  assert(clamped_full.record_distance(5.0f));
  assert(clamped_full.level_fraction(10.0f, 50.0f) == 1.0f);
  ReservoirState clamped_empty;
  assert(clamped_empty.record_distance(60.0f));
  assert(clamped_empty.level_fraction(10.0f, 50.0f) == 0.0f);
  assert(std::isnan(midpoint.level_fraction(50.0f, 50.0f)));
  assert(midpoint.status(50.0f, 50.0f) == MeasurementStatus::UNAVAILABLE);

  ReservoirState filtered;
  assert(filtered.record_distance(30.0f));
  assert(filtered.record_distance(31.0f));
  assert(filtered.record_distance(100.0f));
  assert(filtered.distance_cm() == 31.0f);
  filtered.measurement_requested();
  assert(!filtered.record_distance(NAN));
  assert(filtered.distance_cm() == 31.0f);
  assert(filtered.status(10.0f, 50.0f) == MeasurementStatus::STALE);
  filtered.measurement_requested();
  assert(filtered.record_distance(32.0f));
  assert(filtered.status(10.0f, 50.0f) == MeasurementStatus::VALID);
  assert(!filtered.record_distance(1.0f));
  assert(!filtered.record_distance(201.0f));
  assert(filtered.distance_cm() == 32.0f);

  // Event-driven readings do not become stale merely because time passes.
  ReservoirState long_lived;
  assert(long_lived.record_distance(30.0f));
  assert(long_lived.status(10.0f, 50.0f) == MeasurementStatus::VALID);

  ReservoirState failed_startup;
  failed_startup.measurement_requested();
  assert(!failed_startup.record_distance(NAN));
  assert(failed_startup.status(10.0f, 50.0f) == MeasurementStatus::UNAVAILABLE);
}

}  // namespace

int main() {
  esphome::time::ParsedTimezone timezone{};
  assert(esphome::time::parse_posix_tz("MST7MDT,M3.2.0,M11.1.0", timezone));
  esphome::time::set_global_tz(timezone);
  test_lighting();
  test_grow_cycle();
  test_chemistry();
  test_irrigation_and_pump();
  test_reservoir();
}
