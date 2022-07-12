from msilib.schema import Error
import io
import time
from lark import Lark
import tempfile
import os
from pebble import concurrent
from concurrent.futures import TimeoutError
from datetime import datetime as date
import matlab.engine
import csv


"""
This file gives  classes to use as "Oracles" in the Arvada algorithm.
"""
eng = matlab.engine.connect_matlab()
# eng.warning('off','all', nargout = 0)

def save_file(string, dir):
    """
    Save a file to the given directory.
    """
    with tempfile.NamedTemporaryFile(suffix='.mdl', dir=dir, delete=False) as fi:
        fi.write(bytes(string, 'utf-8'))
        fi.flush()
        return fi.name
load = set()
compile = set()
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
        
        # self.command = command
        self.cache_set = {}
        self.parse_calls = 0
        self.real_calls = 0
        self.time_spent = 0
    
    def close(self):
        eng.quit()

    @concurrent.process(timeout=20)
    def parse_internal(self, string):
        """
        Does the work of calling the subprocess.
        """
        global eng
        # FNULL = open(os.devnull, 'w')
        self.real_calls +=1
        f_name = save_file(string, 'Tmp/')
        
        # case 1: compiles and uncompiles fine
        # case 2: doesn't uncompile
        # case 3: doesn't compile
        try:
            # With check = True, throws a CalledProcessError if the exit code is non-zero
            # subprocess.run([self.command, f_name], stdout=FNULL, stderr=FNULL, timeout=timeout, check=True)
            out = io.StringIO()
            eng.load_system(f_name, stdout=out)
            x = out.getvalue()
            # check warning message
            # if x != '' and x not in load:
            #     load.add(x)
            #     with open('load_warnings.csv', 'a') as f:
            #         writer = csv.writer(f)
            #         writer.writerow([x, string])
            if 'expected' in x:
                raise Exception('Warning')
            model = eng.bdroot()

            try:
                eng.slreportgen.utils.compileModel(model, nargout = 0, stdout=out)
                x = out.getvalue()
                if "Unconnected" in x:
                    raise Exception('Warning')
                # if x != '' and x not in compile:
                #     compile.add(x)
                #     with open('compile_warnings.csv', 'a') as f:
                #         writer = csv.writer(f)
                #         writer.writerow([x, string])
                # print(f"compiled {f_name}: {date.now()}".ljust(80), end='')
                try:
                    eng.slreportgen.utils.uncompileModel(model, nargout = 0, stdout=out)
                except:
                    print(f"doesn't uncompile {date.now()}".ljust(50), end='\r')
                    save_file(string, './Crash/uncompile')
                    
                    return False
            except:
                print(f"doesn't compile {date.now()}".ljust(50), end='\r')
                mat = matlab.engine.find_matlab()
                if len(mat)==0:
                    save_file(string, './Crash/compiletime')
                    
                return False
            try:
                eng.close_system(f_name, nargout = 0)
                print(f"closed {date.now()}".ljust(50), end='\r')
            except:
                print(f"doesn't close {date.now()}".ljust(50), end='\r')
                save_file(string, './Crash/close')
                return True

            print(f"compile and close {date.now()}".ljust(50), end='\r')
            # FNULL.close()
            return True
        except Exception as e:
            print(f"doesn't load {date.now()}".ljust(50), end='\r')
            # print(e)
            return False

        finally:
            try:
                if os.path.exists(f_name):
                    os.remove(f_name)
            except:
                pass

            
            
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
            self.real_calls +=1
            mat = matlab.engine.find_matlab()
        
            if len(mat)==0:
                global eng
                eng = matlab.engine.connect_matlab()
                # eng.warning('off','all', nargout = 0)
                print(f"Created new engine {date.now()}".ljust(50), end='\r')
            s = time.time()
            future = self.parse_internal(string)
            try:
                res = future.result()
            except TimeoutError:
                res = False
                save_file(string, './Crash/timeout')
            except Exception as e:
                print(e)
                res = False
                save_file(string, './Crash/exception')
            
            # self._parse_internal(string, res)
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
