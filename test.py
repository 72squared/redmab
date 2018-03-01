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

    def mab(self, arms, name='test', connection='test', keyspace='test',
            alpha=5, beta=5, pipe=None, klass=multiarmedbandit.MultiArmedBandit):

        storage = multiarmedbandit.create_storage(keyspace, connection)
        return klass(
            name=name,
            storage=storage,
            arms=arms,
            alpha=alpha,
            beta=beta
        )

    def test_thompson(self):
        mab = self.mab(
            arms=['red', 'green', 'blue'],
            alpha=10, beta=10,
            klass=multiarmedbandit.thompson.ThompsonMultiArmedBandit)

        self.assertEqual(mab.draw(), 'blue')
        self.assertEqual(mab.draw(), 'green')
        self.assertEqual(mab.draw(), 'red')
        self.assertEqual(mab.draw_multi(3), ['blue', 'green', 'red'])

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

        mab.update_sucess('red', 4)

        for i in range(10):
            mab.draw()

        self.assertEqual(mab.draw(), 'green')

        res = mab.state()
        #print(res)

        self.assertEqual(int(res['#{red}:count']), 14)
        self.assertEqual(int(res['#{red}:success']), 5)
        self.assertAlmostEqual(float(res['#{red}:mean']), 0.44117647058823528, delta=0.00000000001)

        self.assertEqual(int(res['#{green}:count']), 10)
        self.assertEqual(int(res['#{green}:success']), 3)
        self.assertAlmostEqual(float(res['#{green}:mean']), 0.43333333333333335, delta=0.00000000001)

        self.assertEqual(int(res['#{blue}:count']), 3)
        self.assertNotIn('#{blue}:success', res)
        self.assertAlmostEqual(float(res['#{blue}:mean']), 0.43478260869565222, delta=0.00000000001)
