import time
from lark import Lark
import tempfile
import subprocess
import os
import matlab.engine

"""
This file gives  classes to use as "Oracles" in the Arvada algorithm.
"""

class ParseException(Exception):
    pass

class ExternalOracle:
    """
    An ExternalOracle is a wrapper around an oracle that takes the form of a shell
    command accepting a file as input. We assume the oracle returns True if the
    exit code is 0 (no error). If the external oracle takes >3 seconds to execute,
    we conservatively assume the oracle returns True.
    """

    def __init__(self):
        """
        `command` is a string representing the oracle command, i.e. `command` = "readpng"
        in the oracle call:
            $ readpng <MY_FILE>
        """
        self.eng = matlab.engine.connect_matlab()
        self.eng.warning('off','all', nargout = 0)
        # self.command = command
        self.cache_set = {}
        self.parse_calls = 0
        self.real_calls = 0
        self.time_spent = 0
    
    def close(self):
        self.eng.quit()

    def _parse_internal(self, string, timeout = 3):
        """
        Does the work of calling the subprocess.
        """
        self.real_calls +=1
        # FNULL = open(os.devnull, 'w')
        f = tempfile.NamedTemporaryFile(suffix='.mdl', dir='./Tmp', delete=False)
        f.write(bytes(string, 'utf-8'))
        f_name = f.name
        f.flush()
        f.close()
        # x = open(f.name).read()
        
        # case 1: compiles and uncompiles fine
        # case 2: doesn't uncompile
        # case 3: doesn't compile
        try:
            # With check = True, throws a CalledProcessError if the exit code is non-zero
            # subprocess.run([self.command, f_name], stdout=FNULL, stderr=FNULL, timeout=timeout, check=True)
            self.eng.load_system(f_name)
            model = self.eng.bdroot()

            try:
                self.eng.slreportgen.utils.compileModel(model, nargout = 0)
                try:
                    self.eng.slreportgen.utils.uncompileModel(model, nargout = 0)
                except:
                    print("doesn't uncompile")
                    with tempfile.NamedTemporaryFile(suffix='.mdl', dir='./Crash', delete=False) as fi:
                        fi.write(bytes(string, 'utf-8'))
                        fi.flush()
                    
                    return True
            except:
                print("doesn't compile")
                mat = matlab.engine.find_matlab()
                if len(mat)==0:
                    with tempfile.NamedTemporaryFile(suffix='.mdl', dir='./Crash/compiletime', delete=False) as fi:
                        fi.write(bytes(string, 'utf-8'))
                        fi.flush()
                    # return True
                return False
            try:
                self.eng.close_system(f_name, nargout = 0)
                print("closed")
            except:
                print("doesn't close")

            
            # FNULL.close()
            return True
        except:
            print("doesn't load")
            return False

        finally:
            if os.path.exists(f_name):
                os.remove(f_name)
            mat = matlab.engine.find_matlab()
            print("Engine")
            print(mat)
            if len(mat)==0:
                print("Before")
                self.eng = matlab.engine.connect_matlab()
                self.eng.warning('off','all', nargout = 0)
                print("Created")
        # except subprocess.CalledProcessError as e:
        #     f.close()
        #     FNULL.close()
        #     return False
        # except subprocess.TimeoutExpired as e:
        #     print(f"Caused timeout: {string}")
        #     f.close()
        #     FNULL.close()
        #     return True

    def parse(self, string, timeout=3):
        """
        Caching wrapper around _parse_internal
        """
        self.parse_calls += 1
        if string in self.cache_set:
            if self.cache_set[string]:
                return True
            else:
                raise ParseException(f"doesn't parse: {string}")
        else:
            s = time.time()
            res = self._parse_internal(string, timeout)
            self.time_spent += time.time() - s
            self.cache_set[string] = res
            if res:
                return True
            else:
                raise ParseException(f"doesn't parse: {string}")

class CachingOracle:
    """
    Wraps a "Lark" parser object to provide caching of previous calls.
    """

    def __init__(self, oracle: Lark):
        self.oracle = oracle
        self.cache_set = {}
        self.parse_calls = 0

    def parse(self, string):
        self.parse_calls += 1
        if string in self.cache_set:
            if self.cache_set[string]:
                return True
            else:
                raise ParseException("doesn't parse")
        else:
            try:
                self.oracle.parse(string)
                self.cache_set[string] = True
            except Exception as e:
                self.cache_set[string] = False
                raise ParseException("doesn't parse")
