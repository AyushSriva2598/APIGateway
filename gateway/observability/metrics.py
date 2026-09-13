from prometheus_client import Counter, Histogram

rate_limit_decisions_total = Counter(
    'gateway_rate_limit_decisions_total',
    'Count of rate limit allow/reject decisions',
    ['algorithm', 'decision'],  # decision: 'allowed' | 'rejected'
)

rate_limit_check_duration_seconds = Histogram(
    'gateway_rate_limit_check_duration_seconds',
    'Time spent checking the rate limit against Redis',
    ['algorithm'],
)