-- KEYS[1] = log key, e.g. "ratelimit:sliding_log:{api_key}"
-- ARGV[1] = limit (max requests allowed within the window)
-- ARGV[2] = window_seconds (e.g. 60)
-- ARGV[3] = now (unix timestamp in milliseconds, passed from Python —
--           same reasoning as token bucket: never trust redis.call('TIME')
--           for determinism across replication)
-- ARGV[4] = member (unique id for this request, e.g. now + a random suffix,
--           since ZADD needs unique members — two requests at the identical
--           millisecond would otherwise collide and only count as one)

local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window_seconds = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local member = ARGV[4]

local window_start = now - (window_seconds * 1000)

-- drop every entry older than the window — this is what makes it "sliding"
-- rather than fixed: the window boundary moves with every single request,
-- not just at fixed clock intervals like Day 2's fixed window counter
redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

local count = redis.call('ZCARD', key)

local allowed = 0
if count < limit then
  allowed = 1
  -- score = now, so ZREMRANGEBYSCORE above can correctly expire it later
  redis.call('ZADD', key, now, member)
  count = count + 1
end

redis.call('EXPIRE', key, window_seconds)

local retry_after = 0
if allowed == 0 then
  -- time until the oldest entry ages out of the window and frees a slot
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  if oldest[2] then
    retry_after = math.ceil((tonumber(oldest[2]) + (window_seconds * 1000) - now) / 1000)
  else
    retry_after = window_seconds
  end
end

return {allowed, count, retry_after}