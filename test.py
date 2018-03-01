#!/usr/bin/env python
import testenv  # noqa
import redpipe
import redislite
import unittest
import multiarmedbandit

test_conn = redislite.StrictRedis()

redpipe.connect_redis(test_conn, 'test')



def clean():
    test_conn.flushall()


class BasicTestCase(unittest.TestCase):
    def setUp(self):
        clean()

    def tearDown(self):
        clean()

    def mab(self, name='test', connection='test', keyspace='test', arms=None, options=None, pipe=None):

        return multiarmedbandit.MultiArmedBandit(name=name,
                                                 connection=connection,
                                                 keyspace=keyspace,
                                                 arms=arms,
                                                 options=options,
                                                 pipe=pipe
                                                 )


    def test(self):
        mab = self.mab()
        mab.create(['red', 'green', 'blue'])
        self.assertEqual(mab.draw(), 'blue')
        self.assertEqual(mab.draw(), 'green')
        self.assertEqual(mab.draw(), 'red')
        self.assertEqual(mab.draw_multi(3), ['blue', 'green', 'red'])
        print(mab.stats())

        mab.put('yellow', {'alpha': 5, 'beta': 5})
        self.assertEqual(mab.draw(), 'yellow')
        mab.update_sucess('red')
        mab.update_sucess('green', 2)
        self.assertEqual(mab.draw(), 'green')

        mab.remove('green')
        self.assertEqual(mab.draw(), 'red')
        mab.disable('red')
        self.assertEqual(mab.draw(), 'yellow')
        mab.enable('red')
        self.assertEqual(mab.draw(), 'red')


    def test_single_pass(self):
        with redpipe.pipeline(autoexec=True) as p:
            mab = self.mab(pipe=p, arms=['red', 'green', 'blue'])

        res = mab.draw()

        print(res)