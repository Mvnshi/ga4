"""
Benchmark Analysis
==================
Compare client metrics against industry benchmarks.

Provides context for metrics by comparing against:
- Nonprofit sector averages
- Similar organization benchmarks
- Historical client data
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from config.settings import get_settings


@dataclass
class BenchmarkComparison:
    """Result of comparing a metric to benchmark."""
    metric_name: str
    current_value: float
    benchmark_value: float
    difference: float
    difference_pct: float
    performance: str  # "above", "below", "at"
    interpretation: str


class BenchmarkAnalyzer:
    """
    Compares metrics against industry benchmarks.
    
    Default benchmarks are for nonprofit organizations based on
    industry research and aggregated data.
    """
    
    # Nonprofit industry benchmarks (based on research)
    DEFAULT_BENCHMARKS = {
        # Traffic & Engagement
        'bounce_rate': {
            'value': 55.0,
            'unit': '%',
            'lower_is_better': True,
            'description': 'Nonprofit average bounce rate',
        },
        'avg_session_duration': {
            'value': 120.0,
            'unit': 'seconds',
            'lower_is_better': False,
            'description': 'Nonprofit average session duration',
        },
        'pages_per_session': {
            'value': 2.5,
            'unit': 'pages',
            'lower_is_better': False,
            'description': 'Nonprofit average pages per session',
        },
        
        # Acquisition
        'organic_traffic_share': {
            'value': 40.0,
            'unit': '%',
            'lower_is_better': False,
            'description': 'Typical organic search traffic share',
        },
        'direct_traffic_share': {
            'value': 25.0,
            'unit': '%',
            'lower_is_better': False,
            'description': 'Typical direct traffic share',
        },
        'referral_traffic_share': {
            'value': 15.0,
            'unit': '%',
            'lower_is_better': False,
            'description': 'Typical referral traffic share',
        },
        'social_traffic_share': {
            'value': 10.0,
            'unit': '%',
            'lower_is_better': False,
            'description': 'Typical social media traffic share',
        },
        
        # Audience
        'new_visitor_rate': {
            'value': 70.0,
            'unit': '%',
            'lower_is_better': False,
            'description': 'Typical new visitor percentage',
        },
        'mobile_traffic_share': {
            'value': 55.0,
            'unit': '%',
            'lower_is_better': False,
            'description': 'Typical mobile traffic share',
        },
        
        # Search Performance
        'avg_search_position': {
            'value': 15.0,
            'unit': 'position',
            'lower_is_better': True,
            'description': 'Typical average search position',
        },
        'search_ctr': {
            'value': 3.0,
            'unit': '%',
            'lower_is_better': False,
            'description': 'Typical search CTR',
        },
        
        # Engagement
        'engagement_rate': {
            'value': 55.0,
            'unit': '%',
            'lower_is_better': False,
            'description': 'GA4 engagement rate benchmark',
        },
    }
    
    def __init__(self, custom_benchmarks: Dict[str, Dict] = None):
        """
        Initialize benchmark analyzer.
        
        Args:
            custom_benchmarks: Override default benchmarks with custom values
        """
        self.benchmarks = self.DEFAULT_BENCHMARKS.copy()
        if custom_benchmarks:
            self.benchmarks.update(custom_benchmarks)
    
    def compare(
        self, 
        metric_name: str, 
        current_value: float,
        custom_benchmark: float = None
    ) -> Optional[BenchmarkComparison]:
        """
        Compare a metric value against its benchmark.
        
        Args:
            metric_name: Name of the metric
            current_value: Current value to compare
            custom_benchmark: Optional custom benchmark to use
        
        Returns:
            BenchmarkComparison object or None if no benchmark exists
        """
        if metric_name not in self.benchmarks and custom_benchmark is None:
            return None
        
        benchmark_data = self.benchmarks.get(metric_name, {})
        benchmark_value = custom_benchmark or benchmark_data.get('value', 0)
        lower_is_better = benchmark_data.get('lower_is_better', False)
        
        difference = current_value - benchmark_value
        difference_pct = (difference / benchmark_value * 100) if benchmark_value else 0
        
        # Determine performance
        if abs(difference_pct) < 5:
            performance = "at"
        elif lower_is_better:
            performance = "below" if difference < 0 else "above"
        else:
            performance = "above" if difference > 0 else "below"
        
        # Generate interpretation
        interpretation = self._interpret(
            metric_name, 
            current_value, 
            benchmark_value,
            difference_pct, 
            performance, 
            lower_is_better
        )
        
        return BenchmarkComparison(
            metric_name=metric_name,
            current_value=current_value,
            benchmark_value=benchmark_value,
            difference=difference,
            difference_pct=difference_pct,
            performance=performance,
            interpretation=interpretation
        )
    
    def _interpret(
        self,
        metric_name: str,
        current: float,
        benchmark: float,
        diff_pct: float,
        performance: str,
        lower_is_better: bool
    ) -> str:
        """Generate human-readable interpretation."""
        if performance == "at":
            return f"Performing at industry benchmark ({benchmark:.1f})"
        
        good_performance = (
            (performance == "below" and lower_is_better) or
            (performance == "above" and not lower_is_better)
        )
        
        if good_performance:
            return f"Outperforming benchmark by {abs(diff_pct):.1f}% ({current:.1f} vs {benchmark:.1f})"
        else:
            return f"Below benchmark by {abs(diff_pct):.1f}% ({current:.1f} vs {benchmark:.1f})"
    
    def analyze_all(self, metrics: Dict[str, float]) -> Dict[str, BenchmarkComparison]:
        """
        Compare multiple metrics against benchmarks.
        
        Args:
            metrics: Dictionary of metric_name: value pairs
        
        Returns:
            Dictionary of metric_name: BenchmarkComparison
        """
        results = {}
        for metric_name, value in metrics.items():
            comparison = self.compare(metric_name, value)
            if comparison:
                results[metric_name] = comparison
        return results
    
    def get_benchmark_summary(
        self, comparisons: Dict[str, BenchmarkComparison]
    ) -> Dict[str, Any]:
        """
        Generate summary statistics from benchmark comparisons.
        
        Returns counts and lists of metrics by performance.
        """
        above = []
        below = []
        at_benchmark = []
        
        for name, comp in comparisons.items():
            if comp.performance == "above":
                # Check if above is good or bad
                bench_data = self.benchmarks.get(name, {})
                lower_is_better = bench_data.get('lower_is_better', False)
                if lower_is_better:
                    below.append(name)  # Above but lower is better = bad
                else:
                    above.append(name)  # Above and higher is better = good
            elif comp.performance == "below":
                bench_data = self.benchmarks.get(name, {})
                lower_is_better = bench_data.get('lower_is_better', False)
                if lower_is_better:
                    above.append(name)  # Below but lower is better = good
                else:
                    below.append(name)  # Below and higher is better = bad
            else:
                at_benchmark.append(name)
        
        return {
            'outperforming': above,
            'underperforming': below,
            'at_benchmark': at_benchmark,
            'outperforming_count': len(above),
            'underperforming_count': len(below),
            'at_benchmark_count': len(at_benchmark),
            'total_compared': len(comparisons),
        }

