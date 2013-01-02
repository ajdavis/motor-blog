import functools
import inspect
import xmlrpclib

import tornadorpc
from tornado import stack_context, gen
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
        return fake_fn
        return functools.wraps(wrapper)(fake_fn)

    return wrap


def auth(fn):
    argspec = inspect.getargspec(fn)
    assert 'user' in argspec.args
    assert 'password' in argspec.args

    def _auth(*args, **kwargs):
        self = args[0]
        user = args[argspec.args.index('user')]
        password = args[argspec.args.index('password')]
        if user != opts.user or password != opts.password:
            self.result(xmlrpclib.Fault(403, 'Bad login/pass combination.'))
        else:
            return fn(*args, **kwargs)

    return superwraps(fn)(_auth)


def fault(f):
    @superwraps(f)
    def _f(self, *args, **kwargs):
        def fault_exception_handler(type, value, traceback):
            self.result(xmlrpclib.Fault(500, str(value)))
            return False # Propagate the exception up

        with stack_context.ExceptionStackContext(fault_exception_handler):
            f(self, *args, **kwargs)

    return _f


def engine(f):
    """Like gen.engine, but copy method signature
    """
    return superwraps(f)(gen.engine(f))


def rpc(f):
    """Decorate a function with tornadorpc.async, auth, and fault.
    """
    return tornadorpc.async(auth(fault(f)))
