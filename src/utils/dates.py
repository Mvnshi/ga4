"""
Date Utilities
==============
Comprehensive date handling for quarterly and custom period reports.
"""

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Tuple, Dict, List
from dataclasses import dataclass


@dataclass
class DatePeriod:
    """Represents a date period with metadata."""
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    label: str       # Human-readable label
    
    @property
    def start(self) -> date:
        return datetime.strptime(self.start_date, "%Y-%m-%d").date()
    
    @property
    def end(self) -> date:
        return datetime.strptime(self.end_date, "%Y-%m-%d").date()
    
    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1
    
    def __str__(self) -> str:
        return self.label


@dataclass
class ComparisonPeriods:
    """Holds current and comparison periods."""
    current: DatePeriod
    previous: DatePeriod
    comparison_type: str  # "yoy", "qoq", "mom", "custom"
    
    def __str__(self) -> str:
        return f"{self.current.label} vs {self.previous.label}"


def get_quarter_dates(quarter: str, year: int) -> Tuple[str, str]:
    """
    Get start and end dates for a quarter.
    
    Args:
        quarter: Q1, Q2, Q3, or Q4
        year: The year (e.g., 2024)
    
    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format
    """
    quarters = {
        "Q1": (f"{year}-01-01", f"{year}-03-31"),
        "Q2": (f"{year}-04-01", f"{year}-06-30"),
        "Q3": (f"{year}-07-01", f"{year}-09-30"),
        "Q4": (f"{year}-10-01", f"{year}-12-31"),
    }
    return quarters[quarter.upper()]


def get_quarter_from_date(dt: date) -> Tuple[str, int]:
    """Determine quarter and year from a date."""
    quarter_map = {1: "Q1", 2: "Q1", 3: "Q1", 4: "Q2", 5: "Q2", 6: "Q2",
                   7: "Q3", 8: "Q3", 9: "Q3", 10: "Q4", 11: "Q4", 12: "Q4"}
    return quarter_map[dt.month], dt.year


def get_current_quarter() -> Tuple[str, int]:
    """Get the current quarter and year."""
    return get_quarter_from_date(date.today())


def get_previous_quarter(quarter: str, year: int) -> Tuple[str, int]:
    """Get the previous quarter."""
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    idx = quarters.index(quarter.upper())
    if idx == 0:
        return "Q4", year - 1
    return quarters[idx - 1], year


def get_comparison_periods(
    quarter: str, 
    year: int, 
    comparison_type: str = "yoy"
) -> ComparisonPeriods:
    """
    Get comparison periods for analysis.
    
    Args:
        quarter: Q1, Q2, Q3, or Q4
        year: The year to report on
        comparison_type: 
            - "yoy": Year-over-year (same quarter last year)
            - "qoq": Quarter-over-quarter (previous quarter)
    
    Returns:
        ComparisonPeriods object with current and previous periods
    """
    current_start, current_end = get_quarter_dates(quarter, year)
    current_period = DatePeriod(
        start_date=current_start,
        end_date=current_end,
        label=f"{quarter} {year}"
    )
    
    if comparison_type == "yoy":
        prev_start, prev_end = get_quarter_dates(quarter, year - 1)
        previous_period = DatePeriod(
            start_date=prev_start,
            end_date=prev_end,
            label=f"{quarter} {year - 1}"
        )
    elif comparison_type == "qoq":
        prev_q, prev_y = get_previous_quarter(quarter, year)
        prev_start, prev_end = get_quarter_dates(prev_q, prev_y)
        previous_period = DatePeriod(
            start_date=prev_start,
            end_date=prev_end,
            label=f"{prev_q} {prev_y}"
        )
    else:
        raise ValueError(f"Unknown comparison type: {comparison_type}")
    
    return ComparisonPeriods(
        current=current_period,
        previous=previous_period,
        comparison_type=comparison_type
    )


def get_monthly_periods(quarter: str, year: int) -> List[DatePeriod]:
    """Get individual month periods within a quarter."""
    quarter_months = {
        "Q1": [(1, "January"), (2, "February"), (3, "March")],
        "Q2": [(4, "April"), (5, "May"), (6, "June")],
        "Q3": [(7, "July"), (8, "August"), (9, "September")],
        "Q4": [(10, "October"), (11, "November"), (12, "December")],
    }
    
    periods = []
    for month_num, month_name in quarter_months[quarter.upper()]:
        start = date(year, month_num, 1)
        # Get last day of month
        if month_num == 12:
            end = date(year, 12, 31)
        else:
            end = date(year, month_num + 1, 1) - timedelta(days=1)
        
        periods.append(DatePeriod(
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            label=f"{month_name} {year}"
        ))
    
    return periods


def get_ytd_period(year: int) -> DatePeriod:
    """Get year-to-date period."""
    today = date.today()
    end = min(today, date(year, 12, 31))
    
    return DatePeriod(
        start_date=f"{year}-01-01",
        end_date=end.strftime("%Y-%m-%d"),
        label=f"YTD {year}"
    )


def get_custom_period(
    start_date: str, 
    end_date: str, 
    label: str = None
) -> DatePeriod:
    """Create a custom date period."""
    if label is None:
        label = f"{start_date} to {end_date}"
    
    return DatePeriod(
        start_date=start_date,
        end_date=end_date,
        label=label
    )


def format_month_year(year_month: str) -> str:
    """Convert YYYYMM to 'Month Year' format."""
    year = year_month[:4]
    month = int(year_month[4:])
    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{month_names[month]} {year}"

