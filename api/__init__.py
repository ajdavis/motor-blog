import functools
import inspect
import xmlrpclib
from tornado.options import options as opts


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

    # For tornadorpc to think _auth has the same arguments as fn,
    # functools.wraps() isn't enough.
    # TODO: this is fun, blog about it. Inspired by Mock.
    formatted_args = inspect.formatargspec(*argspec)
    fndef = 'lambda %s: _auth%s' % (
        formatted_args.lstrip('(').rstrip(')'), formatted_args)

    fake_fn = eval(fndef, {'_auth': _auth})
    return functools.wraps(fn)(fake_fn)
