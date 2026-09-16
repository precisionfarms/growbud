#pragma once

#include <cstdint>
#include <ctime>

#include "esphome/core/component.h"
#include "esphome/core/time.h"

namespace esphome::growbud {

constexpr uint32_t CHEMISTRY_FRESHNESS_MS = 180000U;

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

class GrowBudComponent : public Component {
 public:
  ChemistryState &chemistry() { return this->chemistry_; }
  PumpState &pump() { return this->pump_; }

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
};

const char *measurement_status_string(MeasurementStatus status);

}  // namespace esphome::growbud
