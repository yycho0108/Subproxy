#!/usr/bin/env python3

import logging
import inspect
import time
from subproxy import subproxy
import multiprocessing as mp
import multiprocessing.pool as mp_pool
import random


class SimpleRunner(object):
    """ Sample class to be wrapped. """

    def __init__(self, x=5, y=4):
        self.x = x
        self.y = y
        self.z = {'a': 1, 'b': 2}

    def get_y(self):
        return self.y

    def set_y(self, value):
        self.y = value

    def __getitem__(self, key):
        return self.__dict__.__getitem__(key, value)

    def __setitem__(self, key, value):
        return self.__dict__.__setitem__(key, value)


SubprocRunner = subproxy(SimpleRunner)


class WaitAndEcho(object):
    def __init__(self):
        pass

    def echo(self, message, wait: float = 1.0):
        # print('echo = {} {}'.format(message, wait))
        time.sleep(wait)
        return message


def test_race():
    logging.basicConfig(level=logging.INFO)
    SubprocWaitAndEcho = subproxy(WaitAndEcho)
    o = SubprocWaitAndEcho()
    # o = WaitAndEcho()

    def check_echo(arg):
        dt = random.uniform(0.0, 0.001)
        dt2 = o.echo(dt, dt)
        assert(dt == dt2)

    print('start ... ')
    t0 = time.time()
    with mp_pool.ThreadPool(8) as pool:
        r = pool.map(check_echo, range(1000))
    t1 = time.time()
    print('Took {} seconds'.format(t1 - t0))


def main():
    logging.basicConfig(level=logging.DEBUG)

    # Also try local one
    print('2')
    SubprocRunner2 = subproxy(SimpleRunner)

    for SR in [SubprocRunner, SubprocRunner2]:
        print('SR= {}'.format(SR))
        runner = SR(x=6)  # nok
        runner2 = SR(x=6)  # nok
        runner2 = SR(x=6)  # nok
        runner2 = SR(x=6)  # nok
        runner2 = SR(x=6)  # nok
        runner2 = SR(x=6)  # nok

        print('runner type', type(runner))
        print('hmm')

        print(' == initial == ')
        print(runner.x)
        print(runner.get_y())
        print(runner.z)

        # set
        runner.x = 7
        print(runner.set_y(15))
        runner['z'] = {'a': 3, 'b': 4}  # works
        runner.z['a'] = 5  # does not work

        print(' == post-set == ')
        print(runner.x)
        print(runner.get_y())
        print(runner.z)

        print(' == unaffected == ')
        print(runner2.x)
        print(runner2.get_y())
        print(runner2.z)

    #try:
    #    import psutil
    #    cp = psutil.Process()
    #    print('#proc = {}'.format(len(cp.children())))
    #except ImportError as e:
    #    print('skip psutil check : {}'.format(e))


if __name__ == '__main__':
    main()
    # test_race()
