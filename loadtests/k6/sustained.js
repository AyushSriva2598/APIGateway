import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';

const rateLimited = new Counter('rate_limited_responses');
const upstreamErrors = new Counter('upstream_errors');

export const options = {
  stages: [
    { duration: '30s', target: 20 },
    { duration: '2m', target: 20 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    // don't use http_req_failed here — 404 and 429 are both "non-2xx" to
    // k6 but neither is an actual gateway failure for this test
  },
};

export default function () {
  // unique key per REQUEST, not per VU — this is what "sustained load,
  // not hitting rate limits" actually requires
  const apiKey = `sustained-${__VU}-${__ITER}`;

  const res = http.get('http://localhost:8080/api/users/anything', {
    headers: { 'X-API-Key': apiKey },
  });

  check(res, {
    'proxied through (not an upstream error)': (r) => r.status === 404 || r.status === 200,
  });

  if (res.status === 429) rateLimited.add(1);
  if (res.status === 502 || res.status === 504) upstreamErrors.add(1);

  sleep(1);
}