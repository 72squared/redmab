from __future__ import division
import redpipe
from . import luascripts


def create_storage(keysp='MAB', conn='test'):
    class storage(redpipe.Hash):
        keyspace = keysp
        connection = conn

    return storage


class ThompsonSamplingMultiArmedBandit(object):
    def __init__(self, name, arms, storage=None, alpha=5, beta=5,
                 expires=None):

        self.name = name
        self.alpha = alpha
        self.beta = beta
        self.arms = sorted(set(arms))
        self.expires = expires
        if storage is None:
            storage = create_storage()

        self.storage = storage

    @classmethod
    def _pipe(cls, pipe=None, autoexec=True):
        return redpipe.pipeline(pipe=pipe, autoexec=autoexec)

    def delete(self, pipe=None):
        with self._pipe(pipe=pipe) as p:
            s = self.storage(pipe=p)
            s.delete(self.name)

    def draw(self, pipe=None):
        with self._pipe(pipe=pipe) as p:
            s = self.storage(pipe=p)
            response = redpipe.Future()
            result = s.eval(luascripts.draw_lua, 1, self.name, self.alpha,
                            self.beta, *[a for a in self.arms])
            if self.expires:
                s.expire(self.name, self.expires)

            def cb():
                response.set(s.valueparse.decode(result))

            p.on_execute(cb)

            return response

    def draw_multi(self, times, pipe=None):
        with self._pipe(pipe=pipe) as p:
            return [self.draw(pipe=p) for _ in range(times)]

    def update_success(self, arm, reward=1.0, pipe=None):
        with self._pipe(pipe=pipe) as p:
            s = self.storage(pipe=p)
            s.eval(luascripts.update_success_lua, 1, self.name, arm, reward,
                   self.alpha, self.beta)
            if self.expires:
                s.expire(self.name, self.expires)

    def state(self, pipe=None):
        with self._pipe(pipe=pipe) as p:
            return self.storage(pipe=p).hgetall(self.name)
