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

    def mab(self, name='test', connection='test', keyspace='test', arms=None,
            alpha=5, beta=5, pipe=None):

        return multiarmedbandit.MultiArmedBandit(name=name,
                                                 connection=connection,
                                                 keyspace=keyspace,
                                                 arms=arms,
                                                 alpha=alpha,
                                                 beta=beta
                                                 )


    def test(self):
        mab = self.mab(arms=['red', 'green', 'blue'], alpha=10, beta=10)
        self.assertEqual(mab.draw(), 'blue')
        self.assertEqual(mab.draw(), 'green')
        self.assertEqual(mab.draw(), 'red')
        self.assertEqual(mab.draw_multi(3), ['blue', 'green', 'red'])
        print(mab.stats())

        mab.update_sucess('red')
        mab.update_sucess('green', 2)
        self.assertEqual(mab.draw(), 'green')
        self.assertEqual(mab.draw(), 'green')
        self.assertEqual(mab.draw(), 'green')
        self.assertEqual(mab.draw(), 'red')
        self.assertEqual(mab.draw(), 'green')
        self.assertEqual(mab.draw(), 'red')
        mab.update_sucess('green', 1)
        self.assertEqual(mab.draw(), 'green')
        self.assertEqual(mab.draw(), 'green')
        self.assertEqual(mab.draw(), 'green')
        self.assertEqual(mab.draw(), 'red')


    def test_single_pass(self):
        with redpipe.pipeline(autoexec=True) as p:
            mab = self.mab(pipe=p, arms=['red', 'green', 'blue'])

        res = mab.draw()

        print(res)