#pragma once

#include <cstdint>
#include <ctime>

#include "esphome/core/component.h"
#include "esphome/core/time.h"

namespace esphome::growbud {

constexpr uint32_t CHEMISTRY_FRESHNESS_MS = 180000U;
constexpr uint32_t RESERVOIR_FRESHNESS_MS = 120000U;
constexpr float RESERVOIR_MIN_DISTANCE_CM = 2.0f;
constexpr float RESERVOIR_MAX_DISTANCE_CM = 200.0f;

enum class MeasurementStatus : uint8_t { UNAVAILABLE, STALE, VALID };

struct LightingSchedule {
  time_t window_start;
  time_t window_off;
  bool lights_should_be_on;
};

struct GrowCycleDates {
  ESPTime bloom;
  ESPTime harvest;
};

struct IrrigationEvaluation {
  time_t next_run;
  bool run_due;
  bool initialized;
};

class ChemistryState {
 public:
  bool record_ph(float value, uint32_t now_ms);
  bool record_ec(float value, uint32_t now_ms);
  void mark_ph_failed() { this->ph_failed_ = true; }
  void mark_ec_failed() { this->ec_failed_ = true; }
  MeasurementStatus ph_status(uint32_t now_ms) const;
  MeasurementStatus ec_status(uint32_t now_ms) const;
  bool has_valid_ph() const { return this->ph_valid_; }
  float last_ph() const { return this->last_ph_; }

 protected:
  static MeasurementStatus status_(bool valid, bool failed, uint32_t last_success_ms, uint32_t now_ms);
  float last_ph_{0.0f};
  float last_ec_{0.0f};
  uint32_t ph_last_success_ms_{0};
  uint32_t ec_last_success_ms_{0};
  bool ph_valid_{false};
  bool ec_valid_{false};
  bool ph_failed_{false};
  bool ec_failed_{false};
};

class PumpState {
 public:
  bool begin(int requested_seconds, uint32_t now_ms);
  void complete() { this->active_ = false; }
  bool watchdog_should_stop(bool relay_on, uint32_t now_ms);
  uint32_t maximum_runtime_ms() const { return this->maximum_runtime_ms_; }
  static int bounded_duration_seconds(int requested_seconds);

 protected:
  bool active_{false};
  uint32_t started_ms_{0};
  uint32_t maximum_runtime_ms_{0};
};

class IrrigationSchedule {
 public:
  IrrigationEvaluation evaluate(time_t now, int interval_minutes, bool pump_relay_on);
  void reset() { this->next_run_ = 0; }
  time_t next_run() const { return this->next_run_; }

 protected:
  time_t next_run_{0};
};

class ReservoirState {
 public:
  bool record_distance(float distance_cm, uint32_t now_ms);
  MeasurementStatus status(uint32_t now_ms, float full_distance_cm, float empty_distance_cm) const;
  float distance_cm() const { return this->filtered_distance_cm_; }
  float level_fraction(float full_distance_cm, float empty_distance_cm) const;
  float volume_gallons(float full_distance_cm, float empty_distance_cm, float capacity_gallons) const;
  bool has_accepted_distance() const { return this->sample_count_ != 0; }

 protected:
  static bool valid_calibration_(float full_distance_cm, float empty_distance_cm);
  void update_median_();

  float samples_[3]{0.0f, 0.0f, 0.0f};
  float filtered_distance_cm_{0.0f};
  uint32_t last_success_ms_{0};
  uint8_t sample_count_{0};
  uint8_t next_sample_{0};
};

class GrowBudComponent : public Component {
 public:
  ChemistryState &chemistry() { return this->chemistry_; }
  PumpState &pump() { return this->pump_; }
  ReservoirState &reservoir() { return this->reservoir_; }

  static LightingSchedule calculate_lighting_schedule(const ESPTime &now, int start_hour, float duration_hours);
  static ESPTime previous_local_day(const ESPTime &date);
  static ESPTime add_calendar_days(const ESPTime &date, int days);
  static GrowCycleDates calculate_grow_cycle(const ESPTime &start_date, int days_in_veg, int days_in_bloom);
  static int calendar_days_since(const ESPTime &today, const ESPTime &then);

  IrrigationEvaluation evaluate_irrigation(time_t now, int interval_minutes, bool pump_relay_on);
  void reset_irrigation_schedule() { this->irrigation_.reset(); }
  time_t next_pump_run() const { return this->irrigation_.next_run(); }

 protected:
  ChemistryState chemistry_{};
  PumpState pump_{};
  IrrigationSchedule irrigation_{};
  ReservoirState reservoir_{};
};

const char *measurement_status_string(MeasurementStatus status);

}  // namespace esphome::growbud
