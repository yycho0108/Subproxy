#!/usr/bin/env python3

import inspect
import logging
import functools
import multiprocessing as mp

from typing import Callable, List, Dict, Tuple, Any


def _run_subproxy_instance(meta, *args, **kwargs):
    """
    Process target for running a class instance.
    """
    # Spawn class instance.
    (cls, p_client, p_server) = meta
    instance = cls(*args, **kwargs)

    # Get some information about routines
    methods = inspect.getmembers(instance, inspect.isroutine)
    p_server.send([m[0] for m in methods])

    # Listen to INCOMING data
    def on_data(data: Tuple[str, List, Dict]):
        # Unpack data.
        name, args, kwargs = data
        try:
            attr = getattr(instance, name)
        except AttributeError as e:
            p_server.send(e)
            return

        # Deal with functions.
        # syntax = (name, args, kwargs)
        if inspect.isroutine(attr):
            method = attr
            p_server.send(method(*args, **kwargs))
            return

        # Deal with properties.
        # here, not a routine but received args == setattr
        if args:
            # setattr syntax = (name, [value], {})
            setattr(instance, name, args[0])
            return

        # Not a routine & no args == getattr
        # getattr syntax = (name, [], {})
        p_server.send(attr)

    # listener.start()
    logging.debug('subproc/ Listening ...')
    while True:
        try:
            # NOTE(ycho): recv/send pair is executed on 1 thread,
            # thus no locking mechanism necessary here.
            data = p_server.recv()
            on_data(data)
        except Exception as e:
            logging.error(e)
            break


def subproxy(cls: Callable[[Any], object]):
    """
    Wrap a class inside a subprocess and act as a proxy.

    WARN(ycho): Does NOT support decorator(i.e. @subproxy) syntax due to pickling issues.
    Instead, the recommended usage is as follows:
        ProxyClass = subproxy(Class)

    Unlike multiprocessing.Proxy, supports attributes and the returned class
    is self-managed in its own process.
    """

    # NOTE(ycho): Avoid double underscore due to name mangling
    # and the difficulty to forward args as string in {get|set}attr.
    _reserved_subproc_keywords = (
        '_process', '_methods', '_p_client', '_p_server', '_lock')

    class Subproxy:
        def __init__(self, *args, **kwargs):

            # Create the subprocess.
            # Try to `spawn` first, but fallback to `fork`.
            # The advantage of `fork` is that it works for cases such as:
            # AttributeError: Can't pickle local object 'scope.<locals>.Class'
            # However, it may incur more memory if invoked late in the
            # application.
            self._process = None
            for ctx_mode in ['spawn', 'fork']:
                try:
                    ctx = mp.get_context(ctx_mode)
                    p_client, p_server = ctx.Pipe()

                    target = functools.partial(
                        _run_subproxy_instance, (cls, p_client, p_server))
                    process = ctx.Process(
                        target=target, args=args, kwargs=kwargs)
                    process.start()
                except AttributeError as e:
                    logging.warning(
                        'subproc/ Context {} failed : {} | Retry.'.format(ctx_mode, e))
                    continue
                self._process = process
                self._lock = ctx.Lock()  # be thread safe
                break

            if self._process is None:
                raise ValueError('Failed to open subprocess: aborting.')

            # Retrieve list of methods.
            methods = p_client.recv()
            self._methods = methods

            # Save pipes.
            self._p_server = p_server
            self._p_client = p_client

        def __getattribute__(self, name: str):
            # Overrides for reserved keywords.
            if name in _reserved_subproc_keywords:
                return super().__getattribute__(name)

            # Deal with methods.
            if name in self._methods:
                def caller(*args, **kwargs):
                    with self._lock:
                        self._p_client.send((name, args, kwargs))
                        return self._p_client.recv()
                return caller
            else:
                # Deal with attributes.
                with self._lock:
                    self._p_client.send((name, [], {}))
                    res = self._p_client.recv()
                if isinstance(res, AttributeError):
                    raise res
                return res

        def __setattr__(self, name: str, value: Any):
            # Overrides for reserved keywords.
            if name in _reserved_subproc_keywords:
                return super().__setattr__(name, value)
            with self._lock:
                self._p_client.send((name, [value], {}))

        def __getitem__(self, name: str):
            with self._lock:
                self._p_client.send(('__getitem__', [name], {}))
                return self._p_client.recv()

        def __setitem__(self, name: str, value: Any):
            with self._lock:
                self._p_client.send(('__setitem__', [name, value], {}))
                return self._p_client.recv()

        def __del__(self):
            if self._process and self._process.is_alive():
                self._process.terminate()
                self._process.join()
    return Subproxy
