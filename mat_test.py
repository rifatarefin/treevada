from cgitb import reset
from operator import le, length_hint
import os
import matlab.engine
import io, tempfile, shutil
import multiprocessing as mp
# from pebble import concurrent
from concurrent.futures import TimeoutError
warn = set()
warnings = {}    
# @concurrent.process(timeout=20)
def oracle(engs):
    
    try:
        err = io.StringIO()
        eng = matlab.engine.connect_matlab()
        # eng.warning('off','all', nargout = 0)
        eng.load_system('sample.mdl', stdout=err)
        x = err.getvalue()
        print(x)
        if x != '':
            print("kha")
            warn.add(x)
            warnings[x] = "sample.mdl"
        # if('Warning' in x):
        #     raise Exception('Warning')
        else:
            print('load')
        model = eng.bdroot()
        try:
            eng.slreportgen.utils.compileModel(model, nargout = 0)
            print("compile")
            try:
                eng.slreportgen.utils.uncompileModel(model, nargout = 0)
                print("uncomp")
            except:
                print("doesn't uncompile")
        except:
            print("doesn't compile")
        try:
            eng.close_system('sample.mdl', nargout = 0)
            print("close")
        except:
            print("doesn't close")
    except Exception as e:
        print("doesn't load")
        print(e)
    print(warnings)

if __name__ == "__main__":

    
    # comp = eng.sample([],[],[],'compile')
    # comp = eng.sample([],[],[],'term')

    # future = oracle()
    # try:
    #     reset = future.result()
    # except TimeoutError:
    #     print("timeout")
    FNULL = open(os.devnull, 'w')
    ERR = io.StringIO()
    eng = matlab.engine.start_matlab()

    try:
        model = eng.load_system('sample.mdl', stdout = ERR)
    except Exception as e:
        print("catch")
        print(e)
    
    # print(ERR.getvalue())
    # eng.quit()

