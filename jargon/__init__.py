from cStringIO import StringIO
import sys
import os
from jargon                 import tokenizer
from jargon.collector       import FileCollector
from jargon.runner          import Runner
from jargon.exc             import DontReadFromInput
from jargon.util            import runner_options



class JargonCommands(object):

    jargon_help = """
Jargon: A test runner and DSL testing framework for writing readable, 
descriptive tests.

Run tests:
    jargon [PATH] 

Options:
    -s, no-capture      Avoids capturing stderr and stdout
    -x, fail            Stops at first fail
    --tb, traceback     Shows tracebacks with errors/fails
"""

    def __init__(self, argv=None, parse=True, test=False):
        self.test             = test
        self.config           = runner_options
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._original_stdin  = sys.stdin
        self._stderr_buffer   = StringIO()
        self._stdout_buffer   = StringIO()
        
        if argv is None:
            argv = sys.argv
        if parse:
            self.parseArgs(argv)


    def msg(self, msg, stdout=True):
        if stdout:
            sys.stdout.write(msg)
        else:
            sys.stderr.write(msg)
        if not self.test:
            sys.exit(1)


    def path_from_argument(self, argv):
        # Get rid of the executable
        argv.pop(0)
        valid_path = [path for path in argv if os.path.exists(os.path.abspath(path))]
        if valid_path:
            return valid_path[0]
        else:
            return os.getcwd()


    def capture(self):
        if self.config['capturing'] is True:
            sys.stdout = self._stdout_buffer
            sys.stdin  = DontReadFromInput()


    def end_capture(self):
        if self.config['capturing'] is True:
            sys.stdout = self._original_stdout
            sys.stdin  = self._original_stdin


    def parseArgs(self, argv):
        # No options for now
        options      = ['no-capture', '-s', 'fail', '-x', '--tb',
                        'traceback', 'tracebacks']
        help_options = ['-h', '--h', '--help', 'help']

        # Catch help before anything
        if [i for i in argv if i in help_options]:
            self.msg(self.jargon_help)

        # Get a valid path
        search_path = self.path_from_argument(argv)

        match = [i for i in argv if i in options]

        if match:
            arg_count = {}
            count_arg = {}
            
            for count, argument in enumerate(argv):
                arg_count[argument] = count 
                count_arg[count] = argument

            if [opt for opt in ['--tb', 'traceback'] if opt in match]:
                self.config['traceback'] = True

            if [opt for opt in ['-x', 'fail'] if opt in match]:
                self.config['first_fail'] = True

            if [opt for opt in ['-s', 'no-capture'] if opt in match]:
                self.config['capturing'] = False
                

        test_files = FileCollector(search_path)
        if not test_files:
            self.msg("No cases found to test.")

        try:
            self.capture()
            test_runner = Runner(test_files, self.config)
            test_runner.run()
            self.end_capture()

            test_runner.report()
        except KeyboardInterrupt:
            self.msg("Exiting from jargon.\n")



