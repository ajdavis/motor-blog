import functools
import inspect
import logging
import xmlrpclib

import tornadorpc
from tornado import gen
from tornado.options import options as opts


def superwraps(wrapped):
    """Replaces wrapper's arg spec with wrapped function's.

    For when functools.wraps() just isn't enough.
    """
    def wrap(wrapper):
        argspec = inspect.getargspec(wrapped)
        formatted_args = inspect.formatargspec(*argspec)
        fndef = 'lambda %s: wrapper%s' % (
            formatted_args.lstrip('(').rstrip(')'), formatted_args)

        fake_fn = eval(fndef, {'wrapper': wrapper})
        return functools.wraps(wrapped)(fake_fn)

    return wrap


def auth(fn):
    """Verify an XML-RPC method is authorized.

    Check the 'user' and 'password' arguments against those in conf file
    or command line options. If unmatched, return an XML-RPC Fault, else
    call wrapped method.
    """
    argspec = inspect.getargspec(fn)
    assert 'user' in argspec.args
    assert 'password' in argspec.args

    @superwraps(fn)
    @gen.coroutine
    def _auth(*args, **kwargs):
        self = args[0]
        user = args[argspec.args.index('user')]
        password = args[argspec.args.index('password')]
        if user != opts.user or password != opts.password:
            self.result(xmlrpclib.Fault(403, 'Bad login/pass combination.'))
        else:
            raise gen.Return((yield fn(*args, **kwargs)))

    return _auth


def fault(fn):
    """Convert exceptions thrown by coroutine to XML-RPC Faults."""
    @superwraps(fn)
    @gen.coroutine
    def _fault(self, *args, **kwargs):
        try:
            result = yield fn(self, *args, **kwargs)
        except Exception, e:
            logging.exception('XML-RPC call "%s"' % fn.__name__)
            self.result(xmlrpclib.Fault(500, str(e)))
        else:
            raise gen.Return(result)

    return _fault


def return_none(fn):
    """Ensure a coroutine method returns None, not a Future.

    tornadorpc logs a warning if an async method returns non-None.
    """
    @superwraps(fn)
    def _return_none(*args, **kwargs):
        fn(*args, **kwargs)

    return _return_none


def coroutine(f):
    """Like gen.coroutine, but copy method signature."""
    return superwraps(f)(gen.coroutine(f))


def rpc(f):
    """Decorate function with tornadorpc.async, return_none, auth, fault."""
    return tornadorpc.async(return_none(auth(fault(f))))
