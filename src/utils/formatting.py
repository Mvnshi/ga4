"""
Formatting Utilities
====================
Professional formatting for numbers, percentages, and changes.
"""

from typing import Union, Dict, Any
from dataclasses import dataclass


@dataclass
class ChangeMetric:
    """Represents a metric with change information."""
    current: float
    previous: float
    change_pct: float
    change_abs: float
    direction: str  # "up", "down", "neutral"
    is_significant: bool
    is_anomaly: bool
    formatted_change: str
    formatted_current: str
    formatted_previous: str


def calculate_change(
    current: float, 
    previous: float,
    significant_threshold: float = 10.0,
    anomaly_threshold: float = 25.0,
    inverse: bool = False  # True for metrics where down is good (e.g., bounce rate)
) -> ChangeMetric:
    """
    Calculate percentage change with rich metadata.
    
    Args:
        current: Current period value
        previous: Previous period value
        significant_threshold: % change to flag as significant
        anomaly_threshold: % change to flag as anomaly
        inverse: If True, treats decrease as positive (for bounce rate, etc.)
    """
    if previous == 0:
        change_pct = 0.0 if current == 0 else 100.0
    else:
        change_pct = ((current - previous) / previous) * 100
    
    change_abs = current - previous
    
    # Determine direction
    if abs(change_pct) < 0.5:
        direction = "neutral"
    elif change_pct > 0:
        direction = "down" if inverse else "up"
    else:
        direction = "up" if inverse else "down"
    
    # Check thresholds
    is_significant = abs(change_pct) >= significant_threshold
    is_anomaly = abs(change_pct) >= anomaly_threshold
    
    # Format the change
    sign = "+" if change_pct > 0 else ""
    formatted_change = f"{sign}{change_pct:.1f}%"
    
    return ChangeMetric(
        current=current,
        previous=previous,
        change_pct=change_pct,
        change_abs=change_abs,
        direction=direction,
        is_significant=is_significant,
        is_anomaly=is_anomaly,
        formatted_change=formatted_change,
        formatted_current=format_number(current),
        formatted_previous=format_number(previous)
    )


def format_number(value: Union[int, float], decimal_places: int = 0) -> str:
    """Format a number with thousands separators."""
    if isinstance(value, float):
        if decimal_places == 0:
            return f"{int(value):,}"
        return f"{value:,.{decimal_places}f}"
    return f"{value:,}"


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """Format a percentage value."""
    return f"{value:.{decimal_places}f}%"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_ctr(ctr: float) -> str:
    """Format click-through rate."""
    return f"{ctr:.2f}%"


def format_position(position: float) -> str:
    """Format search position."""
    return f"{position:.1f}"


def get_trend_emoji(direction: str, is_anomaly: bool = False) -> str:
    """Get appropriate emoji for trend direction."""
    if is_anomaly:
        if direction == "up":
            return "🚀"
        elif direction == "down":
            return "⚠️"
    
    if direction == "up":
        return "↑"
    elif direction == "down":
        return "↓"
    return "→"


def get_trend_color(direction: str, inverse: bool = False) -> str:
    """Get color for trend visualization."""
    if direction == "neutral":
        return "#888888"
    
    positive = direction == "up"
    if inverse:
        positive = not positive
    
    return "#22C55E" if positive else "#EF4444"  # Green or Red


def format_metric_for_display(
    name: str,
    change_metric: ChangeMetric,
    unit: str = ""
) -> Dict[str, Any]:
    """Format a metric for dashboard display."""
    emoji = get_trend_emoji(change_metric.direction, change_metric.is_anomaly)
    
    return {
        "name": name,
        "current": change_metric.formatted_current + unit,
        "previous": change_metric.formatted_previous + unit,
        "change": change_metric.formatted_change,
        "trend_emoji": emoji,
        "direction": change_metric.direction,
        "is_significant": change_metric.is_significant,
        "is_anomaly": change_metric.is_anomaly
    }


def truncate_string(s: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate a string to max length."""
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as filename."""
    # Replace problematic characters
    replacements = {
        " ": "_",
        "/": "-",
        "\\": "-",
        ":": "-",
        "*": "",
        "?": "",
        '"': "",
        "<": "",
        ">": "",
        "|": "",
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    return name

