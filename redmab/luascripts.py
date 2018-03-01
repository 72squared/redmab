draw_lua = """
local name = KEYS[1]
local alpha = tonumber(ARGV[1])
local beta = tonumber(ARGV[2])

local arms = {}

for i=3,#ARGV do
    arms[#arms + 1] = ARGV[i]
end

local max_mean = 0
local mean = 0
local count = 0
local arm = arms[1]
local bulk = redis.call('HGETALL', name)
local result = {}
local k, i, v

local beta_mean = function(success, count, alpha, beta)
    return 1 / (1 + (count - success + beta) / (success + alpha))
end

local init_mean = beta_mean(0, 0, alpha, beta)

for i, v in ipairs(bulk) do
    if i % 2 == 1 then
        k = v
    else
        result[k] = v
    end
end

for i, a in ipairs(arms) do
    mean = tonumber(result["#{" .. a .. "}:mean"] or init_mean)
    if mean > max_mean then
        max_mean = mean
        arm = a
    end
end

local count = tonumber(result["#{" .. arm .. "}:count"] or 0) + 1
local success = tonumber(result["#{" .. arm .. "}:success"] or 0)
redis.call('HSET', name, "#{" .. arm .. "}:count", count)
mean = beta_mean(success, count, alpha, beta)
redis.call('HSET', name, "#{" .. arm .. "}:mean", mean)
return arm
"""

update_success_lua = """
local name = KEYS[1]
local arm = ARGV[1]
local reward = tonumber(ARGV[2])
local alpha = tonumber(ARGV[3])
local beta = tonumber(ARGV[4])
local success = tonumber(
    redis.call('HINCRBYFLOAT', name, "#{" .. arm .. "}:success", reward))
local count = tonumber(redis.call('HGET', name, "#{" .. arm .. "}:count"))
local mean = 1 / (1 + (count - success + beta) / (success + alpha))
redis.call('HSET', name, "#{" .. arm .. "}:mean", mean)
"""
