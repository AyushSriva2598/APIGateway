import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';

const allowed = new Counter('burst_allowed');
const blocked = new Counter('burst_blocked');

export const options = {
  scenarios: {
    burst: {
      executor: 'shared-iterations',
      vus: 15,               // mirrors the earlier concurrent_rate_limit_test.py concurrency
      iterations: 15,
      maxDuration: '10s',
    },
  },
};

export default function () {
  // SAME key across all VUs, on purpose — this is the point of a burst
  // test: prove the shared limit holds when many instances hit one key
  // at once, same intent as Day 3's concurrent_rate_limit_test.py, just
  // via k6 instead of a hand-rolled thread pool
  const apiKey = 'burst-test-key';

  const res = http.get('http://localhost:8080/api/users/anything', {
    headers: { 'X-API-Key': apiKey },
  });

  const wasAllowed = res.status === 404;  // 404 = proxied through (dummy backend)
  const wasBlocked = res.status === 429;

  check(res, {
    'response is either allowed or rate-limited, not an error': (r) =>
      r.status === 404 || r.status === 429,
  });

  if (wasAllowed) allowed.add(1);
  if (wasBlocked) blocked.add(1);
}