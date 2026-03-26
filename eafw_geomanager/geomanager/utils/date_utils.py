# Date utilities for handling periodic dates (dekadal, pentadal, weekly, monthly, seasonal) and timezone operations.

import logging
from datetime import date, timedelta
import pytz
from django.conf import settings

logger = logging.getLogger("geomanager.date_utils")

DEKAD_DAYS = [1, 11, 21]
PENTAD_DAYS = [1, 6, 11, 16, 21, 26]


class PeriodDateUtil:
    # Base class for periodic date utilities.
    PERIOD_DAYS = []
    PERIOD_NAME = "period"

    @classmethod
    def is_valid_period_day(cls, day):
        return day in cls.PERIOD_DAYS

    @classmethod
    def generate_dates(cls, start_year, end_year, end_month, end_day):
        # Generate periodic dates between start_year and end_year.
        dates = []

        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                for period_day in cls.PERIOD_DAYS:
                    if (year == end_year and month > end_month) or (
                        year == end_year and month == end_month and period_day > end_day
                    ):
                        return dates

                    try:
                        d = date(year, month, period_day)
                        dates.append(d)
                    except ValueError:
                        # Skip invalid dates (e.g., February 30)
                        continue

        return dates

    @classmethod
    def calculate_next_period_date(cls, current_date):
        # Calculate the next period date after the given date.
        day = current_date.day
        month = current_date.month
        year = current_date.year

        # Find current position in period days
        try:
            current_index = cls.PERIOD_DAYS.index(day)
            # If not the last period of the month, return next period
            if current_index < len(cls.PERIOD_DAYS) - 1:
                return date(year, month, cls.PERIOD_DAYS[current_index + 1])
            else:
                # Move to next month, first period
                if month == 12:
                    return date(year + 1, 1, cls.PERIOD_DAYS[0])
                else:
                    return date(year, month + 1, cls.PERIOD_DAYS[0])

        except ValueError:
            # Invalid period day, return current date
            return current_date


class DekadDateUtil(PeriodDateUtil):
    PERIOD_DAYS = DEKAD_DAYS
    PERIOD_NAME = "dekad"


class PentadDateUtil(PeriodDateUtil):
    PERIOD_DAYS = PENTAD_DAYS
    PERIOD_NAME = "pentad"


class MonthlyDateUtil(PeriodDateUtil):
    """Day 1 of every month."""

    PERIOD_DAYS = [1]
    PERIOD_NAME = "monthly"
    # Base class generate_dates with PERIOD_DAYS=[1] already produces day 1 of every month.
    # Base class calculate_next_period_date with PERIOD_DAYS=[1] already advances to next month day 1.


class WeeklyDateUtil(PeriodDateUtil):
    """Every 7 days from an anchor date.

    The day of week is NOT fixed — it depends on the dataset's own cadence
    (e.g. Thu-Thu, Wed-Wed). Use generate_from_anchor() when the exact start
    date is known. generate_dates() falls back to anchoring on Jan 1 of
    start_year when only the year is available.
    """

    PERIOD_NAME = "weekly"

    @classmethod
    def is_valid_period_day(cls, day):
        return True  # not day-of-month based

    @classmethod
    def generate_from_anchor(cls, anchor_date, end_date):
        """Generate dates every 7 days starting from anchor_date up to end_date."""
        dates = []
        current = anchor_date
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=7)
        return dates

    @classmethod
    def generate_dates(cls, start_year, end_year, end_month, end_day):
        """Fallback: anchor to Jan 1 of start_year when exact start date is unavailable."""
        return cls.generate_from_anchor(
            anchor_date=date(start_year, 1, 1),
            end_date=date(end_year, end_month, end_day),
        )

    @classmethod
    def calculate_next_period_date(cls, current_date):
        return current_date + timedelta(days=7)


class PeriodUtilFactory:
    """Factory for getting the appropriate period utility."""

    _utilities = {
        "dekadal": DekadDateUtil,
        "pentadal": PentadDateUtil,
        "monthly": MonthlyDateUtil,
        "weekly": WeeklyDateUtil,
    }

    @classmethod
    def get_util(cls, period_type):
        # Get the appropriate period utility.
        util = cls._utilities.get(period_type)
        if not util:
            raise ValueError(f"Unsupported period type: {period_type}. Supported types: {list(cls._utilities.keys())}")
        return util

    @classmethod
    def register_util(cls, period_type, util_class):
        """Register a custom period utility."""
        cls._utilities[period_type] = util_class


def ensure_timezone_aware(dt, timezone_str=None):
    if timezone_str is None:
        timezone_str = settings.TIME_ZONE

    local_tz = pytz.timezone(timezone_str)

    # If already timezone-aware, return as-is
    if dt.tzinfo is not None:
        return dt

    # If naive, localize to the specified timezone
    return local_tz.localize(dt)


# Utility functions
def generate_dekadal_dates(start_year, end_year, end_month, end_dekad):
    return DekadDateUtil.generate_dates(start_year, end_year, end_month, end_dekad)


def generate_pentadal_dates(start_year, end_year, end_month, end_pentad):
    return PentadDateUtil.generate_dates(start_year, end_year, end_month, end_pentad)


def calculate_next_dekad_date(current_date):
    return DekadDateUtil.calculate_next_period_date(current_date)


def calculate_next_pentad_date(current_date):
    return PentadDateUtil.calculate_next_period_date(current_date)
