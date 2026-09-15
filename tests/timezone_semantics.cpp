#include <cassert>
#include <cstdlib>
#include <ctime>
#include <string>

#include "esphome/core/time.h"

namespace {

constexpr const char *DENVER_TZ = "MST7MDT,M3.2.0,M11.1.0";

time_t local_epoch(int year, int month, int day, int hour, int minute = 0) {
  std::tm local{};
  local.tm_year = year - 1900;
  local.tm_mon = month - 1;
  local.tm_mday = day;
  local.tm_hour = hour;
  local.tm_min = minute;
  local.tm_isdst = -1;
  return std::mktime(&local);
}

std::string local_string(time_t epoch) {
  return esphome::ESPTime::from_epoch_local(epoch).strftime("%Y-%m-%d %I:%M%p");
}

}  // namespace

int main() {
  setenv("TZ", DENVER_TZ, 1);
  tzset();

  const time_t summer_five = local_epoch(2026, 9, 15, 5);
  assert(summer_five == 1789470000);
  assert(local_string(summer_five) == "2026-09-15 05:00AM");
  const time_t summer_eleven = local_epoch(2026, 9, 15, 23);
  assert(local_string(summer_eleven) == "2026-09-15 11:00PM");
  assert(local_string(summer_five + 13 * 60 * 60) == "2026-09-15 06:00PM");
  assert(local_string(summer_eleven + 13 * 60 * 60) == "2026-09-16 12:00PM");

  const time_t winter_five = local_epoch(2026, 1, 15, 5);
  assert(winter_five == 1768478400);
  assert(local_string(winter_five) == "2026-01-15 05:00AM");

  const time_t fractional_start = local_epoch(2026, 9, 15, 5);
  assert(local_string(fractional_start + 18 * 60 * 60 + 30 * 60) == "2026-09-15 11:30PM");

  // Reproduce the regression: mktime runs as UTC, then the epoch is displayed
  // after Denver local-time conversion. The result is six hours early in summer.
  setenv("TZ", "UTC0", 1);
  tzset();
  const time_t wrong_epoch = local_epoch(2026, 9, 15, 5);
  setenv("TZ", DENVER_TZ, 1);
  tzset();
  assert(local_string(wrong_epoch) == "2026-09-14 11:00PM");
}
