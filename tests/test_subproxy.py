#!/usr/bin/env python3

import time
import random
import multiprocessing.pool
import pytest
import inspect
from typing import Dict

from subproxy import subproxy


class SampleClass(object):
    """ Sample class to be wrapped. """

    def __init__(self, x: int = 0, y: int = 1,
                 z: Dict[str, int] = {'a': 2, 'b': 3}):
        self.x = x
        self.y = y
        self.z = z

    def get_y(self):
        return self.y

    def set_y(self, value):
        self.y = value

    def __getitem__(self, key):
        return self.__dict__.__getitem__(key, value)

    def __setitem__(self, key, value):
        return self.__dict__.__setitem__(key, value)


SampleProxy = subproxy(SampleClass)


class WaitAndEcho(object):
    """
    Echo a message after the specified wait time.
    """

    def __init__(self):
        pass

    def echo(self, message, wait: float = 1.0):
        time.sleep(wait)
        return message


def test_race():
    """
    Test thread safety under race-condition scenario if not locked.
    """
    WaitAndEchoProxy = subproxy(WaitAndEcho)
    o = WaitAndEchoProxy()

    def check_echo(arg):
        dt = random.uniform(0.0, 0.001)
        dt2 = o.echo(dt, dt)
        assert(dt == dt2)

    t0 = time.time()
    with multiprocessing.pool.ThreadPool(8) as pool:
        r = pool.map(check_echo, range(1000))
    t1 = time.time()


def test_init():
    """
    Test initializer args are propagated correctly.
    """
    x = random.randint(0, 65536)
    y = random.randint(0, 65536)
    z = {'a': random.randint(0, 65536), 'b': random.randint(0, 65536)}
    o = SampleProxy(x=x, y=y, z=z)
    assert(o.x == x)
    assert(o.y == y)
    assert(o.z == z)


def test_attr():
    """
    Validate all attrs are represented in the proxy.
    """
    o = SampleProxy()
    for k, _ in inspect.getmembers(SampleClass()):
        assert(hasattr(o, k))


def test_scoped_class():
    """
    Test creating a proxy class within a scope.
    Due to pickling issues, typically the `spawn` context will not work.
    """
    #NOTE(ycho): Scoped classes work, but only within a fork.
    class ScopedClass(SampleClass):
        pass
    ScopedProxy = subproxy(ScopedClass)
    o = ScopedProxy()


def test_nested_proxy():
    o = SampleProxy()

    # Single level getattr does work.
    z = {'a': 1, 'b': 2}
    o.z = z
    assert(o.z == z)

    # Nested proxy does not work.
    # TODO(ycho): Consider optionally enabling this feature.
    # i.e. either subproc(cls, deep=True)
    # or subproc(cls, nest=['a','b'])
    o.z['a'] = 2
    assert(o.z == z)


def test_simple_usage():
    # Validate against default construction.
    o = SampleProxy(x=6)
    o0 = SampleClass()
    assert(o.x == 6)
    assert(o.y == o0.y)
    assert(o.z == o0.z)

    # Validate after modifying properties.
    o.x = 7
    o.set_y(15)
    o['z'] = {'a': 3, 'b': 4}  # works
    o.z['a'] = 5  # does not work
    assert(o.x == 7)
    assert(o.y == 15)
    assert(o.z == {'a': 3, 'b': 4})
