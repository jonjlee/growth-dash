from .gc_stats import GC_TYPE, SEX, init, get_percentile_lines, percentile, zscore

# Call init to load data files
init()

__all__ = [GC_TYPE, SEX, get_percentile_lines, percentile, zscore]