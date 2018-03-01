from __future__ import division
import redpipe


# still in progress, do not use.
draw_lua="""
local name = KEYS[1]
local arms = ARGV
local max_mean = 0
local mean = 0
local count = 0
local arm = arms[1]
local bulk = redis.call('HGETALL', name)
local result = {}
local k, i, v

for i, v in ipairs(bulk) do
    if i % 2 == 1 then
        k = v
    else
        result[k] = v
    end
end

for i, a in ipairs(arms) do
    mean = tonumber(result["#{" .. a .. "}:mean"] or 0)
    if mean > max_mean then
        max_mean = mean
        arm = a
    end
end

redis.call('HINCRBY', name, "#{" .. arm .. "}:count", 1)
mean = tonumber(result["#{" .. arm .. "}:mean"])
local success = tonumber(result["#{" .. arm .. "}:success"] or 0)
local count = tonumber(result["#{" .. arm .. "}:count"] or 0) + 1
local alpha = tonumber(result["#{" .. arm .. "}:alpha"] or 0)
local beta = tonumber(result["#{" .. arm .. "}:beta"] or 0)

if alpha <= 0 then
    alpha = tonumber(result["alpha"])
end

if beta <= 0 then
    beta = tonumber(result["beta"])
end

mean = 1 / (1 + (count - success) + beta / (success + alpha))

redis.call('HSET', name, "#{" .. arm .. "}:mean", mean)
return arm
"""

class ThompsonMultiArmedBandit(object):
    USE_LUA = True

    @classmethod
    def beta_mean(cls, success, count, alpha, beta):
        fail_count = count - success
        return 1 / (1 + float(fail_count + beta) / (success + alpha))

    @classmethod
    def klass(cls, conn, keysp):
        class storage(redpipe.Hash):
            keyspace = conn
            connection = keysp

        return storage

    def __init__(self, name, connection=None, keyspace='TMAB', arms = None, options=None, pipe=None):

        self.name = name
        self.alpha = 5
        self.beta = 5
        self.arms = set()
        self.storage = self.klass(connection, keyspace)

        if arms is not None:
            self.create(arms=arms, options=options, pipe=pipe)

    def _pipe(self, pipe=None, autoexec=False):
        return redpipe.pipeline(pipe=pipe, autoexec=autoexec)

    def _means_k(self, arm):
        return '#{%s}:mean' % arm

    def _success_k(self, arm):
        return '#{%s}:success' % arm

    def _count_k(self, arm):
        return '#{%s}:count' % arm

    def _alpha_k(self, arm):
        return '#{%s}:alpha' % arm

    def _beta_k(self, arm):
        return '#{%s}:beta' % arm

    def create(self, arms, options=None, pipe=None):
        arms = set(arms)
        if options is None:
            options = {}
        ts = {'alpha': self.alpha, 'beta': self.beta, 'arms': ','.join(arms)}

        for arm in arms:
            ts[self._count_k(arm)] = 0
            ts[self._success_k(arm)] = 0
            ts[self._alpha_k(arm)] = 0
            ts[self._beta_k(arm)] = 0

        ts.update(options)

        for arm in arms:
            mean = self.beta_mean(
                0,
                0,
                ts['alpha'],
                ts['beta']
            )
            ts[self._means_k(arm)] = mean

        with self._pipe(pipe=pipe, autoexec=True) as p:
            s = self.storage(pipe=p)
            for k, v in ts.items():
                s.hsetnx(self.name, k, str(v))
            self.load(pipe=p)

    def load(self, pipe=None):
        with self._pipe(pipe=pipe, autoexec=True) as p:
            s = self.storage(pipe=p)
            arms = s.hget(self.name, 'arms')
            alpha = s.hget(self.name, 'alpha')
            beta = s.hget(self.name, 'beta')

            def cb():
                self.arms = set([k for k in arms.split(',') if len(k) > 0])
                self.alpha = float(alpha)
                self.beta = float(beta)

            p.on_execute(cb)

    def delete(self, pipe=None):
        with self._pipe(pipe=pipe, autoexec=True) as p:
            s = self.storage(pipe=p)
            s.delete(self.name)

    def put(self, arm, options=None, pipe=None):
        if options is None:
            options = {}
        ts = {self._count_k(arm): 0, self._success_k(arm): 0.0}
        ts.update(options)

        self.arms.add(arm)
        with self._pipe(pipe=pipe, autoexec=True) as p:
            s = self.storage(pipe=p)
            for k, v in ts.items():
                s.hsetnx(self.name, k, str(v))
            s.hset(self.name, 'arms', ','.join(self.arms))
            mean = self.mean(arm=arm, pipe=p)

            def cb():
                with self._pipe(autoexec=True) as pp:
                    self.update_mean(arm, mean=mean, pipe=pp)
                    self.load(pipe=pp)

            p.on_execute(cb)

    def remove(self, arm, pipe=None):
        with self._pipe(pipe=pipe, autoexec=True) as p:
            self.arms.remove(arm)
            s = self.storage(pipe=p)
            s.hset(self.name, 'arms', ','.join(self.arms))
            s.hdel(self.name, self._success_k(arm))
            s.hdel(self.name, self._count_k(arm))
            s.hdel(self.name, self._alpha_k(arm))
            s.hdel(self.name, self._beta_k(arm))

    def disable(self, arm, pipe=None):
        with self._pipe(pipe=pipe, autoexec=True) as p:
            s = self.storage(pipe=p)
            s.hdel(self.name, self._means_k(arm))

    def draw(self, pipe=None):
        if self.USE_LUA:
            return self.storage(pipe=pipe).eval(self.name, draw_lua, *[a for a in self.arms])

        arm_means = {k: 0 for k in self.arms}
        with self._pipe(autoexec=True) as p:
            s = self.storage(pipe=p)
            arm_means = {k: s.hget(self.name, self._means_k(k)) for k in self.arms}

        max_arm = max(arm_means.keys(), key=lambda k: float(arm_means[k]) if arm_means[k] else 0)

        with self._pipe(autoexec=True) as p:
            s = self.storage(pipe=p)
            s.hincrby(self.name, self._count_k(max_arm), 1)


            def cb():
                mean = self.mean(max_arm)
                self.update_mean(arm=max_arm, mean=mean)

            p.on_execute(cb)

        return max_arm

    def draw_multi(self, times):
        return [self.draw() for _ in range(times)]



    def update_sucess(self, arm, reward=1.0):
        with self._pipe(autoexec=True) as p:
            s = self.storage(pipe=p)
            s.hincrbyfloat(self.name, self._success_k(arm), reward)
            mean = self.mean(arm=arm, pipe=p)

            def cb():
                self.update_mean(arm=arm, mean=mean)

            p.on_execute(cb)

    def update_mean(self, arm, mean, pipe=None):
        with self._pipe(pipe=pipe, autoexec=True) as p:
            s = self.storage(pipe=p)
            s.hset(self.name, self._means_k(arm), str(float(mean)))

    def enable(self, arm):
        self.update_mean(arm, self.mean(arm))

    def mean(self, arm, pipe=None):
        with self._pipe(pipe=pipe, autoexec=True) as p:
            s = self.storage(pipe=p)
            success = s.hget(self.name, self._success_k(arm))
            count = s.hget(self.name, self._count_k(arm))
            alpha = s.hget(self.name, self._alpha_k(arm))
            beta = s.hget(self.name, self._beta_k(arm))

            future = redpipe.Future()

            def cb():
                s = float(success)
                c = float(count)
                a = float(alpha or 0) or self.alpha
                b = float(beta or 0) or self.beta

                future.set(self.beta_mean(success=s, count=c, alpha=a, beta=b))

            p.on_execute(cb)

        return future

    def stats(self, pipe=None):
        with self._pipe(pipe=pipe, autoexec=True) as p:
            s = self.storage(pipe=p)
            state = s.hgetall(self.name)

        return state
