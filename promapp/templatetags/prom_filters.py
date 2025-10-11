from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def abs_value(value):
    """Return absolute value"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divide value by arg"""
    try:
        divisor = float(arg)
        if divisor == 0:
            return 0
        return float(value) / divisor
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def get_latest_aggregated_stat(aggregated_statistics):
    """Get the latest (most recent time interval) aggregated statistic"""
    if not aggregated_statistics or not isinstance(aggregated_statistics, dict):
        return None
    
    # Get the maximum time interval key
    max_interval = max(aggregated_statistics.keys())
    return aggregated_statistics[max_interval]
