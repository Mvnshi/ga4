"""
Trend Analysis
==============
Identify patterns, trends, and anomalies in time-series data.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class TrendResult:
    """Result of trend analysis."""
    direction: str  # "increasing", "decreasing", "stable", "volatile"
    strength: float  # 0-1 scale
    slope: float  # Rate of change
    description: str
    significant: bool


@dataclass
class AnomalyResult:
    """Detected anomaly in data."""
    date: str
    metric: str
    value: float
    expected_range: Tuple[float, float]
    deviation_pct: float
    type: str  # "spike", "drop"


class TrendAnalyzer:
    """
    Analyzes time-series data to identify trends and anomalies.
    """
    
    def __init__(self, sensitivity: float = 2.0):
        """
        Initialize trend analyzer.
        
        Args:
            sensitivity: Standard deviations for anomaly detection (default 2.0)
        """
        self.sensitivity = sensitivity
    
    def analyze_trend(
        self,
        data: pd.DataFrame,
        date_col: str,
        value_col: str
    ) -> TrendResult:
        """
        Analyze trend in time-series data.
        
        Args:
            data: DataFrame with date and value columns
            date_col: Name of date column
            value_col: Name of value column
        
        Returns:
            TrendResult with trend characteristics
        """
        if data.empty or len(data) < 3:
            return TrendResult(
                direction="stable",
                strength=0,
                slope=0,
                description="Insufficient data for trend analysis",
                significant=False
            )
        
        # Convert to numeric index for regression
        values = data[value_col].values
        x = np.arange(len(values))
        
        # Calculate linear regression
        try:
            slope, intercept = np.polyfit(x, values, 1)
        except Exception:
            return TrendResult(
                direction="stable",
                strength=0,
                slope=0,
                description="Unable to calculate trend",
                significant=False
            )
        
        # Calculate R-squared for strength
        y_pred = slope * x + intercept
        ss_res = np.sum((values - y_pred) ** 2)
        ss_tot = np.sum((values - np.mean(values)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Determine direction and significance
        mean_value = np.mean(values)
        relative_slope = (slope / mean_value * 100) if mean_value != 0 else 0
        
        if abs(relative_slope) < 1:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        # Check for volatility
        cv = np.std(values) / mean_value if mean_value != 0 else 0
        if cv > 0.5:
            direction = "volatile"
        
        significant = abs(relative_slope) > 5 and r_squared > 0.3
        
        # Generate description
        if direction == "stable":
            description = f"Metric remained relatively stable around {mean_value:,.0f}"
        elif direction == "volatile":
            description = f"High volatility detected (CV: {cv:.1%})"
        else:
            direction_word = "increased" if direction == "increasing" else "decreased"
            description = f"Metric {direction_word} by approximately {abs(relative_slope):.1f}% over the period"
        
        return TrendResult(
            direction=direction,
            strength=r_squared,
            slope=relative_slope,
            description=description,
            significant=significant
        )
    
    def detect_anomalies(
        self,
        data: pd.DataFrame,
        date_col: str,
        value_col: str,
        min_deviation: float = None
    ) -> List[AnomalyResult]:
        """
        Detect anomalies in time-series data.
        
        Args:
            data: DataFrame with date and value columns
            date_col: Name of date column
            value_col: Name of value column
            min_deviation: Minimum % deviation to flag (default uses sensitivity)
        
        Returns:
            List of detected anomalies
        """
        if data.empty or len(data) < 5:
            return []
        
        values = data[value_col].values
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        if std_val == 0:
            return []
        
        anomalies = []
        threshold = self.sensitivity * std_val
        min_deviation = min_deviation or (self.sensitivity * 50)  # Default 100% deviation
        
        for idx, row in data.iterrows():
            value = row[value_col]
            deviation = abs(value - mean_val)
            
            if deviation > threshold:
                deviation_pct = (value - mean_val) / mean_val * 100 if mean_val != 0 else 0
                
                if abs(deviation_pct) >= min_deviation:
                    anomalies.append(AnomalyResult(
                        date=str(row[date_col]),
                        metric=value_col,
                        value=value,
                        expected_range=(mean_val - std_val, mean_val + std_val),
                        deviation_pct=deviation_pct,
                        type="spike" if value > mean_val else "drop"
                    ))
        
        return anomalies
    
    def compare_periods(
        self,
        current: pd.DataFrame,
        previous: pd.DataFrame,
        value_col: str
    ) -> Dict[str, Any]:
        """
        Compare metrics between two periods.
        
        Returns statistics on the comparison.
        """
        if current.empty or previous.empty:
            return {}
        
        curr_values = current[value_col].values
        prev_values = previous[value_col].values
        
        curr_mean = np.mean(curr_values)
        prev_mean = np.mean(prev_values)
        curr_total = np.sum(curr_values)
        prev_total = np.sum(prev_values)
        
        mean_change = ((curr_mean - prev_mean) / prev_mean * 100) if prev_mean else 0
        total_change = ((curr_total - prev_total) / prev_total * 100) if prev_total else 0
        
        return {
            'current_mean': curr_mean,
            'previous_mean': prev_mean,
            'mean_change_pct': mean_change,
            'current_total': curr_total,
            'previous_total': prev_total,
            'total_change_pct': total_change,
            'current_min': np.min(curr_values),
            'current_max': np.max(curr_values),
            'previous_min': np.min(prev_values),
            'previous_max': np.max(prev_values),
        }
    
    def get_period_summary(
        self,
        data: pd.DataFrame,
        date_col: str,
        value_col: str
    ) -> Dict[str, Any]:
        """
        Generate statistical summary for a period.
        """
        if data.empty:
            return {}
        
        values = data[value_col].values
        
        return {
            'count': len(values),
            'sum': float(np.sum(values)),
            'mean': float(np.mean(values)),
            'median': float(np.median(values)),
            'std': float(np.std(values)),
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'range': float(np.max(values) - np.min(values)),
        }

