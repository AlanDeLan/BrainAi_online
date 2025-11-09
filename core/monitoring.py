"""
Monitoring and metrics for Local Brain.
"""
import time
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from core.logger import logger

# Metrics storage
_metrics: Dict[str, List[Dict]] = defaultdict(list)
_counters: Dict[str, int] = defaultdict(int)
_timers: Dict[str, List[float]] = defaultdict(list)

def increment_counter(name: str, value: int = 1):
    """
    Increment a counter metric.
    
    Args:
        name: Counter name
        value: Value to increment by
    """
    _counters[name] += value
    logger.debug(f"Counter '{name}' incremented by {value}, current value: {_counters[name]}")

def record_timer(name: str, duration: float):
    """
    Record a timer metric.
    
    Args:
        name: Timer name
        duration: Duration in seconds
    """
    _timers[name].append(duration)
    # Keep only last 1000 measurements
    if len(_timers[name]) > 1000:
        _timers[name] = _timers[name][-1000:]
    logger.debug(f"Timer '{name}' recorded: {duration:.3f}s")

def record_metric(name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """
    Record a metric with value and optional tags.
    
    Args:
        name: Metric name
        value: Metric value
        tags: Optional tags
    """
    metric = {
        "name": name,
        "value": value,
        "timestamp": datetime.now().isoformat(),
        "tags": tags or {}
    }
    _metrics[name].append(metric)
    # Keep only last 1000 measurements
    if len(_metrics[name]) > 1000:
        _metrics[name] = _metrics[name][-1000:]
    logger.debug(f"Metric '{name}' recorded: {value}")

def get_counter(name: str) -> int:
    """
    Get counter value.
    
    Args:
        name: Counter name
    
    Returns:
        Counter value
    """
    return _counters.get(name, 0)

def get_timer_stats(name: str) -> Dict[str, float]:
    """
    Get timer statistics.
    
    Args:
        name: Timer name
    
    Returns:
        Dictionary with min, max, avg, count
    """
    if name not in _timers or len(_timers[name]) == 0:
        return {"min": 0, "max": 0, "avg": 0, "count": 0}
    
    values = _timers[name]
    return {
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
        "count": len(values)
    }

def get_metrics_summary() -> Dict:
    """
    Get summary of all metrics.
    
    Returns:
        Dictionary with counters, timers, and metrics
    """
    timer_summaries = {}
    for name in _timers:
        timer_summaries[name] = get_timer_stats(name)
    
    metric_summaries = {}
    for name in _metrics:
        if _metrics[name]:
            values = [m["value"] for m in _metrics[name]]
            metric_summaries[name] = {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "count": len(values)
            }
    
    return {
        "counters": dict(_counters),
        "timers": timer_summaries,
        "metrics": metric_summaries
    }

def reset_metrics():
    """Reset all metrics."""
    global _metrics, _counters, _timers
    _metrics.clear()
    _counters.clear()
    _timers.clear()
    logger.info("Metrics reset")

class TimerContext:
    """Context manager for timing operations."""
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            record_timer(self.name, duration)

