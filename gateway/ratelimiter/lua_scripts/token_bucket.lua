-- KEYS[1] = bucket key, e.g. "ratelimit:token_bucket:{api_key}"
-- ARGV[1] = capacity (max tokens the bucket can hold)
-- ARGV[2] = refill_rate (tokens added per second)
-- ARGV[3] = now (current unix timestamp, passed in from Python — never trust
--           the Redis server's own clock across a cluster)
-- ARGV[4] = requested (tokens this request costs, normally 1)

local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

if tokens == nil then
  -- first request for this key — bucket starts full
  tokens = capacity
  last_refill = now
end

-- refill based on elapsed time since last check
local elapsed = math.max(now - last_refill, 0)
tokens = math.min(capacity, tokens + (elapsed * refill_rate))

local allowed = 0
if tokens >= requested then
  tokens = tokens - requested
  allowed = 1
end

redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
-- expire the key well after the bucket would naturally refill, so idle
-- keys don't sit in Redis forever
redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) * 2)

-- retry_after: seconds until enough tokens exist for one more request
local retry_after = 0
if allowed == 0 then
  retry_after = math.ceil((requested - tokens) / refill_rate)
end

return {allowed, tokens, retry_after}