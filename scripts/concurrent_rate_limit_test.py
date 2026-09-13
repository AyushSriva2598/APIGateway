"""
Fires N requests at the gateway SIMULTANEOUSLY (not one-after-another like
the earlier sequential test) to prove Redis's atomic Lua scripts hold up
even when multiple gateway replicas receive requests at the exact same
instant — the actual race-condition case a sequential test can't catch.
"""
import argparse
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


def fire_request(url: str, api_key: str) -> int:
    try:
        resp = requests.get(url, headers={'X-API-Key': api_key}, timeout=5)
        return resp.status_code
    except requests.exceptions.RequestException:
        return -1  # connection-level failure, not an HTTP status


def run(url: str, api_key: str, total_requests: int, concurrency: int):
    print(f'Firing {total_requests} requests at {url}, concurrency={concurrency}, key={api_key}')

    start = time.time()
    results = []

    # ThreadPoolExecutor with max_workers=concurrency submits all requests
    # essentially at once — this is what makes it "concurrent" rather than
    # sequential like the earlier curl loop, which waited for each response
    # before sending the next.
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(fire_request, url, api_key) for _ in range(total_requests)]
        for future in as_completed(futures):
            results.append(future.result())

    elapsed = time.time() - start
    counts = Counter(results)

    print(f'\nCompleted in {elapsed:.2f}s')
    print(f'Status code breakdown: {dict(counts)}')

    allowed = counts.get(200, 0) + counts.get(404, 0)  # 404 = allowed through to dummy backend
    blocked = counts.get(429, 0)
    errors = counts.get(-1, 0) + counts.get(502, 0)

    print(f'\nAllowed:  {allowed}')
    print(f'Blocked (429): {blocked}')
    print(f'Errors (connection/502): {errors}')

    return allowed, blocked, errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://localhost:8080/api/users/anything')
    parser.add_argument('--key', default='concurrenttest')
    parser.add_argument('--total', type=int, default=15)
    parser.add_argument('--concurrency', type=int, default=15)
    parser.add_argument('--expected-limit', type=int, default=5,
                         help='Fails loudly if allowed count exceeds this — the actual correctness check')
    args = parser.parse_args()

    allowed, blocked, errors = run(args.url, args.key, args.total, args.concurrency)

    if allowed > args.expected_limit:
        print(f'\n❌ FAIL: {allowed} requests were allowed, expected at most {args.expected_limit}. '
              f'Redis-backed limit did NOT hold under concurrency — race condition present.')
        exit(1)
    else:
        print(f'\n✅ PASS: {allowed} allowed ≤ {args.expected_limit} limit, even under {args.concurrency} simultaneous requests.')