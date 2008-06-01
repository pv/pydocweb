#!/usr/bin/env python
import os, sys, compiler, doctest, traceback, tempfile, shutil, resource
from optparse import OptionParser
import matplotlib
matplotlib.use('Agg.png')
import matplotlib.pyplot

BAD_ATTRS = [r'_.*', r'im_.*', r'co_.*', '.*file.*',
             '.*save.*', 'test.*', 'rc', 'rcParamsDefault', 'rcdefaults',
             'pylab.*', 'memmap']
OK_MODULES = """
re
numpy numpy.fft numpy.linalg
scipy scipy.optimize scipy.integrate scipy.interpolate scipy.fftpack
matplotlib.pyplot
StringIO
""".split()

IMG_PREFIX = "image"
IMG_COUNTER = 1

MAX_RUN_TIME = 15 # sec
os.environ['openin_any'] = 'p' # for Latex (if ran by matplotlib)
os.environ['openout_any'] = 'p'
os.environ['shell_escape'] = 'f'
resource.setrlimit(resource.RLIMIT_CPU, (MAX_RUN_TIME, MAX_RUN_TIME))

def main():
    """
    %prog
    
    Execute doctest code in a sandbox.
    
    WARNING: 'sandboxing' DOES NOT MEAN THAT ALL WAYS OF MALICIOUS BEHAVIOUR
             ARE IMPOSSIBLE.
    
             It only means that we are using Zope's RestrictedPython
             framework. It disables many ways of escaping the sandbox,
             but it is possible, although unlikely, that some routes
             are unplugged.
    
    """
    global IMG_PREFIX
    p = OptionParser(usage=__doc__)
    p.add_option("--image-prefix", dest="image_prefix", action="store",
                 type="string", help="prefix for image files", default=None)
    options, args = p.parse_args()

    if options.image_prefix:
        IMG_PREFIX = options.image_prefix
    
    text = sys.stdin.read()

    # run
    verbose = 0
    optionflags = doctest.NORMALIZE_WHITESPACE
    parser = doctest.DocTestParser()
    globs = {}
    name = None
    filename = "<string>"
    report = True
    
    runner = RestrictedDocTestRunner(verbose=verbose, optionflags=optionflags)
    test = parser.get_doctest(text, globs, name, filename, 0)

    tmpdir = tempfile.mkdtemp()
    cwd = os.getcwd()
    try:
        import matplotlib
        os.chdir(tmpdir)
        runner.run(test)
    except (RestrictionError, SyntaxError), e:
        print "Sandbox error:", str(e)
        sys.exit(3)
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmpdir)
    
    if report:
        failed, total = runner.summarize()
        print "%d of %d tests passed" % (total-failed, total)

    if runner.failures > 0:
        sys.exit(2)
    else:
        sys.exit(0)

#------------------------------------------------------------------------------
# Guards
#------------------------------------------------------------------------------
import inspect

class RestrictionError(RuntimeError): pass

def _our_matplotlib_show():
    global IMG_COUNTER
    matplotlib.pyplot.savefig("%s-%s.png" % (IMG_PREFIX, IMG_COUNTER),
                              dpi=50)
    IMG_COUNTER += 1

matplotlib.pyplot.show = _our_matplotlib_show
matplotlib.show = _our_matplotlib_show

del matplotlib.pyplot.rcParamsDefault
del matplotlib.pyplot.rcdefaults

def _print_passthru():
    class PrintPassthru:
        def write(self, text): sys.stdout.write(text)
        def __call__(self): return ""
    return PrintPassthru()

def _write_guard(obj):
    raise RestrictionError("bad setattr: %s" % name)

def _restrict_getattr(obj, name):
    for attr_re in BAD_ATTRS:
        if re.match(attr_re, name):
            raise RestrictionError("bad getattr: %s" % name)
    res = getattr(obj, name)
    if inspect.ismodule(res):
        if res.__name__ not in OK_MODULES:
            raise RestrictionError("bad module getattr: %s" % name)
    if inspect.isclass(res) and not inspect.ismodule(obj):
        raise RestrictionError("bad obj -> class getattr: %s" % name)
    return res

def _restrict_getitem(obj, name):
    return obj[name]

def _restrict_import(name, globals={}, locals={}, fromlist=[], level=-1):
    for mod_name in OK_MODULES:
        if name == mod_name:
            return __import__(name, globals, locals, fromlist, level)
    raise RestrictionError("bad import: %s" % name)

#------------------------------------------------------------------------------
# Sandboxed doctest
#------------------------------------------------------------------------------
import pdb, re
import RestrictedPython
import RestrictedPython.Guards as Guards

class RestrictedDocTestRunner(doctest.DocTestRunner):
    def __init__(self, checker=None, verbose=None, optionflags=0):
        doctest.DocTestRunner.__init__(self,
                                       checker=checker,
                                       verbose=verbose,
                                       optionflags=optionflags)
        self.policy = {
            '__builtins__': Guards.safe_builtins,
            '_write_': _write_guard,
            '_getattr_': _restrict_getattr,
            '_getitem_': _restrict_getitem,
            '_print_': _print_passthru,
        }
        self.policy['__builtins__']['__import__'] = _restrict_import
    
    def run(self, test, compileflags=None, out=None, clear_globs=True):
        """
        Run the examples in `test`, and display the results using the
        writer function `out`.

        The examples are run in the namespace `test.globs`.  If
        `clear_globs` is true (the default), then this namespace will
        be cleared after the test runs, to help with garbage
        collection.  If you would like to examine the namespace after
        the test completes, then use `clear_globs=False`.

        `compileflags` gives the set of flags that should be used by
        the Python compiler when running the examples.  If not
        specified, then it will default to the set of future-import
        flags that apply to `globs`.

        The output of each example is checked using
        `DocTestRunner.check_output`, and the results are formatted by
        the `DocTestRunner.report_*` methods.
        """
        self.test = test

        if compileflags is None:
            compileflags = doctest._extract_future_flags(test.globs)

        save_stdout = sys.stdout
        if out is None:
            out = save_stdout.write
        sys.stdout = self._fakeout

        # Patch pdb.set_trace to restore sys.stdout during interactive
        # debugging (so it's not still redirected to self._fakeout).
        # Note that the interactive output will go to *our*
        # save_stdout, even if that's not the real sys.stdout; this
        # allows us to write test cases for the set_trace behavior.
        save_set_trace = pdb.set_trace
        self.debugger = doctest._OutputRedirectingPdb(save_stdout)
        self.debugger.reset()
        pdb.set_trace = self.debugger.set_trace

        # Patch linecache.getlines, so we can see the example's source
        # when we're inside the debugger.
        self.save_linecache_getlines = doctest.linecache.getlines
        doctest.linecache.getlines = self.__patched_linecache_getlines

        try:
            return self.__run(test, compileflags, out)
        finally:
            sys.stdout = save_stdout
            pdb.set_trace = save_set_trace
            doctest.linecache.getlines = self.save_linecache_getlines
            if clear_globs:
                test.globs.clear()

    def __run(self, test, compileflags, out):
        """
        Run the examples in `test`.  Write the outcome of each example
        with one of the `DocTestRunner.report_*` methods, using the
        writer function `out`.  `compileflags` is the set of compiler
        flags that should be used to execute examples.  Return a tuple
        `(f, t)`, where `t` is the number of examples tried, and `f`
        is the number of examples that failed.  The examples are run
        in the namespace `test.globs`.
        """
        # Keep track of the number of failures and tries.
        failures = tries = 0

        # Save the option flags (since option directives can be used
        # to modify them).
        original_optionflags = self.optionflags

        SUCCESS, FAILURE, BOOM = range(3) # `outcome` state

        check = self._checker.check_output

        # Process each example.
        for examplenum, example in enumerate(test.examples):

            # If REPORT_ONLY_FIRST_FAILURE is set, then supress
            # reporting after the first failure.
            quiet = (self.optionflags & doctest.REPORT_ONLY_FIRST_FAILURE and
                     failures > 0)

            # Merge in the example's options.
            self.optionflags = original_optionflags
            if example.options:
                for (optionflag, val) in example.options.items():
                    if val:
                        self.optionflags |= optionflag
                    else:
                        self.optionflags &= ~optionflag

            # If 'SKIP' is set, then skip this example.
            if self.optionflags & doctest.SKIP:
                continue

            # Record that we started this example.
            tries += 1
            if not quiet:
                self.report_start(out, test, example)

            # Use a special filename for compile(), so we can retrieve
            # the source code during interactive debugging (see
            # __patched_linecache_getlines).
            filename = '<doctest %s[%d]>' % (test.name, examplenum)

            # Run the example in the given context (globs), and record
            # any exception that gets raised.  (But don't intercept
            # keyboard interrupts.)
            try:
                # Don't blink!  This is where the user's code gets run.
                code = RestrictedPython.compile_restricted(
                    example.source, filename, "single")
                test.globs.update(self.policy)
                exec code in test.globs
                self.debugger.set_continue() # ==== Example Finished ====
                exception = None
            except (RestrictionError, SyntaxError):
                raise
            except KeyboardInterrupt:
                raise
            except:
                exception = sys.exc_info()
                self.debugger.set_continue() # ==== Example Finished ====

            got = self._fakeout.getvalue()  # the actual output
            self._fakeout.truncate(0)
            outcome = FAILURE   # guilty until proved innocent or insane

            # If the example executed without raising any exceptions,
            # verify its output.
            if exception is None:
                if check(example.want, got, self.optionflags) or example.source.startswith('plt.'):
                    outcome = SUCCESS

            # The example raised an exception:  check if it was expected.
            else:
                exc_info = sys.exc_info()
                exc_msg = traceback.format_exception_only(*exc_info[:2])[-1]
                if not quiet:
                    got += doctest._exception_traceback(exc_info)

                # If `example.exc_msg` is None, then we weren't expecting
                # an exception.
                if example.exc_msg is None:
                    outcome = BOOM

                # We expected an exception:  see whether it matches.
                elif check(example.exc_msg, exc_msg, self.optionflags):
                    outcome = SUCCESS

                # Another chance if they didn't care about the detail.
                elif self.optionflags & IGNORE_EXCEPTION_DETAIL:
                    m1 = re.match(r'[^:]*:', example.exc_msg)
                    m2 = re.match(r'[^:]*:', exc_msg)
                    if m1 and m2 and check(m1.group(0), m2.group(0),
                                           self.optionflags):
                        outcome = SUCCESS

            # Report the outcome.
            if outcome is SUCCESS:
                if not quiet:
                    self.report_success(out, test, example, got)
            elif outcome is FAILURE:
                if not quiet:
                    self.report_failure(out, test, example, got)
                failures += 1
            elif outcome is BOOM:
                if not quiet:
                    self.report_unexpected_exception(out, test, example,
                                                     exc_info)
                failures += 1
            else:
                assert False, ("unknown outcome", outcome)

        # Restore the option flags (in case they were modified)
        self.optionflags = original_optionflags

        # Record and return the number of failures and tries.
        self.__record_outcome(test, failures, tries)
        return failures, tries

    def __record_outcome(self, test, f, t):
        """
        Record the fact that the given DocTest (`test`) generated `f`
        failures out of `t` tried examples.
        """
        f2, t2 = self._name2ft.get(test.name, (0,0))
        self._name2ft[test.name] = (f+f2, t+t2)
        self.failures += f
        self.tries += t
    
    __LINECACHE_FILENAME_RE = re.compile(r'<doctest '
                                         r'(?P<name>[\w\.]+)'
                                         r'\[(?P<examplenum>\d+)\]>$')

    def __patched_linecache_getlines(self, filename, module_globals=None):
        m = self.__LINECACHE_FILENAME_RE.match(filename)
        if m and m.group('name') == self.test.name:
            example = self.test.examples[int(m.group('examplenum'))]
            return example.source.splitlines(True)
        else:
            return self.save_linecache_getlines(filename, module_globals)

#------------------------------------------------------------------------------

if __name__ == "__main__": main()
