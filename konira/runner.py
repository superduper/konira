import re
import inspect
import sys
import types
from decimal          import Decimal
from konira.exc       import KoniraFirstFail, KoniraNoSkip
from konira.util      import StopWatch, get_class_name, get_let_attrs, set_let_attrs, pdb_post_postmortem
from konira.collector import globals_from_file
from konira.output    import TerminalWriter


class Runner(object):

    def __init__(self, paths, config):
        self.config         = config
        self.paths          = paths
        self.failures       = []
        self.errors         = []
        self.profiles       = []
        self.total_cases    = 0
        self.total_failures = 0
        self.total_errors   = 0
        self.total_skips    = 0
        self.class_name     = config.get('class_name')
        self.method_name    = config.get('method_name')
        self.write          = sys.__stdout__.write
        self.writer         = TerminalWriter(config.get('dotted'))


    def run(self):
        self.timer = StopWatch()
        for f in self.paths:
            try:
                classes = get_classes(f, self.class_name)
            except Exception, e:
                self.total_errors += 1
                self.errors.append(
                    dict(
                        failure   = sys.exc_info(),
                        exc_name  = e.__class__.__name__
                       )
                    )
                continue
            try:
                for case in classes:
                    self.run_suite(case)
            except KoniraFirstFail:
                break

        self.elapsed = self.timer.elapsed()


    def run_suite(self, case):
        # Initialize the test class
        suite = case()

        # check test environment setup
        environ = TestEnviron(suite)

        methods = get_methods(suite, self.method_name)
        if not methods: return

        # Name the class
        class_name = suite.__class__.__name__
        self.writer.out_case(class_name)

        # Are we skipping?
        if safe_skip_call(environ.set_skip_if):
            self.writer.skipping()
            return

        let_map = get_let_attrs(suite)

        # Set before all if any
        self.safe_environ_call(environ.set_before_all)

        for test in methods:
            test_start_time = StopWatch(raw=True)
            suite = set_let_attrs(suite, let_map)
            self.total_cases += 1

            # Set before each if any
            self.safe_environ_call(environ.set_before_each)

            try:
                getattr(suite, test)()
                test_elapsed_time = Decimal(str(test_start_time.elapsed()))
                self.writer.green_spec(test)

            except BaseException, e:
                test_elapsed_time = Decimal(str(test_start_time.elapsed()))
                trace = inspect.trace()[-1]
                self.total_failures += 1
                self.writer.red_spec(test)
                self.failures.append(
                    dict(
                        failure  = sys.exc_info(),
                        trace    = trace,
                        exc_name = e.__class__.__name__
                       )
                    )

                is_assert_error = isinstance(e, AssertionError)
                if is_assert_error and self.config.get('pdb_on_fail'):
                    pdb_post_postmortem()
                elif not is_assert_error and self.config.get('pdb'):
                    pdb_post_postmortem()

                if self.config.get('first_fail'):
                    raise KoniraFirstFail

            # Save profiling info
            self.profiles.append((test_elapsed_time,
                                  test,
                                  class_name))

            # Set after each if any
            self.safe_environ_call(environ.set_after_each)

        # Set after all if any
        self.safe_environ_call(environ.set_after_all)


    def safe_environ_call(self, env_call):
        try:
            env_call()
        except Exception, e:
            self.errors.append(
                dict(
                    failure   = sys.exc_info(),
                    exc_name  = e.__class__.__name__
                   )
                )



class TestEnviron(object):
    """
    Checks for all test setup calls and sets a boolean
    flag for each.
    This approach avoids the runner to be checking getattr
    for every time since we alredy did at the beginning.
    """


    def __init__(self, suite):
        self.suite           = suite
        self.has_skip_if     = self._skip_if
        self.has_before_all  = self._before_all
        self.has_before_each = self._before_each
        self.has_after_all   = self._after_all
        self.has_after_each  = self._after_each


    @property
    def _skip_if(self):
        if hasattr(self.suite, '_skip_if'):
            return True
        return False


    @property
    def _before_all(self):
        if hasattr(self.suite, '_before_all'):
            return True
        return False


    @property
    def _before_each(self):
        if hasattr(self.suite, '_before_each'):
            return True
        return False


    @property
    def _after_all(self):
        if hasattr(self.suite, '_after_all'):
            return True
        return False


    @property
    def _after_each(self):
        if hasattr(self.suite, '_after_each'):
            return True
        return False


    def set_skip_if(self):
        if self.has_skip_if:
            getattr(self.suite, '_skip_if')()
        else:
            raise KoniraNoSkip


    def set_before_all(self):
        if self.has_before_all:
            getattr(self.suite, '_before_all')()


    def set_before_each(self):
        if self.has_before_each:
            return getattr(self.suite, '_before_each')()


    def set_after_all(self):
        if self.has_after_all:
            return getattr(self.suite, '_after_all')()


    def set_after_each(self):
        if self.has_after_each:
            return getattr(self.suite, '_after_each')()

#
# Runner helpers
#

def get_classes(filename, class_name):
    if class_name:
        return  [i for i in _collect_classes(filename)
                    if class_name == get_class_name(i)]
    else:
        return _collect_classes(filename)



def get_methods(suite, method_name):
    if method_name:
        methods = [i for i in _collect_methods(suite)
                    if i == method_name]
    else:
        methods = _collect_methods(suite)
    return methods


def _collect_classes(path):
    # parse and compile file
    global_modules, source_txt = globals_from_file(path)
    # will be used later for sorting methods
    attach_source = lambda cls: setattr(cls, '__source__', source_txt)
    # filters
    has_case_class_name = lambda s: s.__name__.startswith('Case_')
    is_a_class = lambda s: isinstance(s, (types.ClassType, types.TypeType))
    is_a_case_class = lambda s: is_a_class(s) and has_case_class_name(s)
    # sort key extractor
    cls_pos = lambda cls: source_txt.index(cls.__name__)
    # build the case class list
    case_cls_list = filter(is_a_case_class, global_modules.values())
    case_cls_list.sort(cls_pos)
    # modify classes, attaching source code
    map(attach_source, case_cls_list)
    return case_cls_list


def _collect_methods(module):
    valid_method_name = re.compile(r'it_[_a-z]\w*$', re.IGNORECASE)
    def method_lineno(s): 
        return module.__source__.index(s)
    methods = [i for i in dir(module) if valid_method_name.match(i)]
    methods.sort(key=method_lineno)
    return methods




def safe_skip_call(env_call):
    try:
        env_call()
        return True
    except KoniraNoSkip:
        return False
    except Exception:
        return False


