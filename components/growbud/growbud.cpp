#include "growbud.h"

#include <cmath>

namespace esphome::growbud {

bool ChemistryState::record_ph(float value, uint32_t now_ms) {
  if (!std::isfinite(value)) {
    this->ph_failed_ = true;
    return false;
  }
  this->last_ph_ = value;
  this->ph_last_success_ms_ = now_ms;
  this->ph_valid_ = true;
  this->ph_failed_ = false;
  return true;
}

bool ChemistryState::record_ec(float value, uint32_t now_ms) {
  if (!std::isfinite(value)) {
    this->ec_failed_ = true;
    return false;
  }
  this->last_ec_ = value;
  this->ec_last_success_ms_ = now_ms;
  this->ec_valid_ = true;
  this->ec_failed_ = false;
  return true;
}

MeasurementStatus ChemistryState::status_(bool valid, bool failed, uint32_t last_success_ms, uint32_t now_ms) {
  if (!valid || failed)
    return MeasurementStatus::UNAVAILABLE;
  if (static_cast<uint32_t>(now_ms - last_success_ms) > CHEMISTRY_FRESHNESS_MS)
    return MeasurementStatus::STALE;
  return MeasurementStatus::VALID;
}

MeasurementStatus ChemistryState::ph_status(uint32_t now_ms) const {
  return status_(this->ph_valid_, this->ph_failed_, this->ph_last_success_ms_, now_ms);
}

MeasurementStatus ChemistryState::ec_status(uint32_t now_ms) const {
  return status_(this->ec_valid_, this->ec_failed_, this->ec_last_success_ms_, now_ms);
}

bool ReservoirState::record_distance(float distance_cm, uint32_t now_ms) {
  if (!std::isfinite(distance_cm) || distance_cm < RESERVOIR_MIN_DISTANCE_CM ||
      distance_cm > RESERVOIR_MAX_DISTANCE_CM)
    return false;
  this->samples_[this->next_sample_] = distance_cm;
  this->next_sample_ = (this->next_sample_ + 1) % 3;
  if (this->sample_count_ < 3)
    this->sample_count_++;
  this->last_success_ms_ = now_ms;
  this->update_median_();
  return true;
}

void ReservoirState::update_median_() {
  float sorted[3];
  for (uint8_t i = 0; i < this->sample_count_; i++)
    sorted[i] = this->samples_[i];
  for (uint8_t i = 1; i < this->sample_count_; i++) {
    const float value = sorted[i];
    uint8_t position = i;
    while (position > 0 && sorted[position - 1] > value) {
      sorted[position] = sorted[position - 1];
      position--;
    }
    sorted[position] = value;
  }
  if (this->sample_count_ == 2)
    this->filtered_distance_cm_ = (sorted[0] + sorted[1]) / 2.0f;
  else
    this->filtered_distance_cm_ = sorted[this->sample_count_ / 2];
}

bool ReservoirState::valid_calibration_(float full_distance_cm, float empty_distance_cm) {
  return std::isfinite(full_distance_cm) && std::isfinite(empty_distance_cm) &&
         full_distance_cm < empty_distance_cm;
}

MeasurementStatus ReservoirState::status(uint32_t now_ms, float full_distance_cm, float empty_distance_cm) const {
  if (!this->has_accepted_distance() || !valid_calibration_(full_distance_cm, empty_distance_cm))
    return MeasurementStatus::UNAVAILABLE;
  if (static_cast<uint32_t>(now_ms - this->last_success_ms_) > RESERVOIR_FRESHNESS_MS)
    return MeasurementStatus::STALE;
  return MeasurementStatus::VALID;
}

float ReservoirState::level_fraction(float full_distance_cm, float empty_distance_cm) const {
  if (!this->has_accepted_distance() || !valid_calibration_(full_distance_cm, empty_distance_cm))
    return NAN;
  const float fraction = (empty_distance_cm - this->filtered_distance_cm_) /
                         (empty_distance_cm - full_distance_cm);
  if (fraction < 0.0f)
    return 0.0f;
  if (fraction > 1.0f)
    return 1.0f;
  return fraction;
}

float ReservoirState::volume_gallons(float full_distance_cm, float empty_distance_cm,
                                     float capacity_gallons) const {
  const float fraction = this->level_fraction(full_distance_cm, empty_distance_cm);
  if (!std::isfinite(fraction) || !std::isfinite(capacity_gallons) || capacity_gallons < 0.0f)
    return NAN;
  return fraction * capacity_gallons;
}

int PumpState::bounded_duration_seconds(int requested_seconds) {
  if (requested_seconds < 1)
    return 1;
  if (requested_seconds > 300)
    return 300;
  return requested_seconds;
}

bool PumpState::begin(int requested_seconds, uint32_t now_ms) {
  if (this->active_)
    return false;
  this->started_ms_ = now_ms;
  this->maximum_runtime_ms_ = static_cast<uint32_t>(bounded_duration_seconds(requested_seconds)) * 1000U;
  this->active_ = true;
  return true;
}

bool PumpState::watchdog_should_stop(bool relay_on, uint32_t now_ms) {
  if (!relay_on) {
    this->active_ = false;
    return false;
  }
  if (!this->active_ || static_cast<uint32_t>(now_ms - this->started_ms_) >= this->maximum_runtime_ms_) {
    this->active_ = false;
    return true;
  }
  return false;
}

ESPTime GrowBudComponent::previous_local_day(const ESPTime &date) {
  ESPTime result = date;
  if (result.day_of_month > 1) {
    result.day_of_month--;
  } else {
    if (result.month > 1) {
      result.month--;
    } else {
      result.month = 12;
      result.year--;
    }
    result.day_of_month = days_in_month(result.month, result.year);
  }
  result.recalc_timestamp_local();
  return ESPTime::from_epoch_local(result.timestamp);
}

LightingSchedule GrowBudComponent::calculate_lighting_schedule(const ESPTime &now, int start_hour,
                                                               float duration_hours) {
  const time_t duration_seconds = static_cast<time_t>(duration_hours * 3600.0f + 0.5f);
  ESPTime today_start_local = now;
  today_start_local.hour = start_hour;
  today_start_local.minute = 0;
  today_start_local.second = 0;
  today_start_local.recalc_timestamp_local();
  const time_t today_start = today_start_local.timestamp;
  const time_t today_off = today_start + duration_seconds;
  LightingSchedule result{today_start, today_off, now.timestamp >= today_start && now.timestamp < today_off};

  if (now.timestamp < today_start) {
    ESPTime previous_start_local = previous_local_day(today_start_local);
    previous_start_local.hour = start_hour;
    previous_start_local.minute = 0;
    previous_start_local.second = 0;
    previous_start_local.recalc_timestamp_local();
    const time_t previous_start = previous_start_local.timestamp;
    const time_t previous_off = previous_start + duration_seconds;
    if (now.timestamp >= previous_start && now.timestamp < previous_off)
      result = {previous_start, previous_off, true};
  }
  return result;
}

ESPTime GrowBudComponent::add_calendar_days(const ESPTime &date, int days) {
  ESPTime result = date;
  result.hour = result.minute = result.second = 0;
  result.recalc_timestamp_local();
  result = ESPTime::from_epoch_local(result.timestamp);
  for (int i = 0; i < days; i++)
    result.increment_day();
  result.hour = result.minute = result.second = 0;
  result.recalc_timestamp_local();
  return ESPTime::from_epoch_local(result.timestamp);
}

GrowCycleDates GrowBudComponent::calculate_grow_cycle(const ESPTime &start_date, int days_in_veg, int days_in_bloom) {
  const ESPTime bloom = add_calendar_days(start_date, days_in_veg);
  return {bloom, add_calendar_days(bloom, days_in_bloom)};
}

int GrowBudComponent::calendar_days_since(const ESPTime &today_value, const ESPTime &then_value) {
  ESPTime today = today_value;
  ESPTime then = then_value;
  today.hour = today.minute = today.second = 0;
  then.hour = then.minute = then.second = 0;
  today.recalc_timestamp_utc(false);
  then.recalc_timestamp_utc(false);
  return static_cast<int>((today.timestamp - then.timestamp) / 86400);
}

IrrigationEvaluation IrrigationSchedule::evaluate(time_t now, int interval_minutes, bool pump_relay_on) {
  const time_t interval_seconds = static_cast<time_t>(interval_minutes) * 60;
  const bool initialized = this->next_run_ == 0;
  if (initialized)
    this->next_run_ = now + interval_seconds;
  const bool due = now >= this->next_run_ && !pump_relay_on;
  if (due)
    this->next_run_ = now + interval_seconds;
  return {this->next_run_, due, initialized};
}

IrrigationEvaluation GrowBudComponent::evaluate_irrigation(time_t now, int interval_minutes, bool pump_relay_on) {
  return this->irrigation_.evaluate(now, interval_minutes, pump_relay_on);
}

const char *measurement_status_string(MeasurementStatus status) {
  switch (status) {
    case MeasurementStatus::VALID:
      return "Valid";
    case MeasurementStatus::STALE:
      return "Stale";
    default:
      return "Unavailable";
  }
}

}  // namespace esphome::growbud
