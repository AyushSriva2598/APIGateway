local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window_seconds = tonumber(ARGV[2])
local requested = tonumber(ARGV[3])

local count = redis.call('INCRBY', key, requested)

if count == requested then
  redis.call('EXPIRE', key, window_seconds)
end

local allowed = 0
if count <= limit then
  allowed = 1
end

local ttl = redis.call('TTL', key)
if ttl < 0 then
  ttl = window_seconds
end

return {allowed, count, ttl}