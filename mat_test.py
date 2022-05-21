from cgitb import reset
from os import error
from sys import stderr, stdout
import matlab.engine
import io
from pebble import concurrent
from concurrent.futures import TimeoutError
warn = set()
warnings = {}    
@concurrent.process(timeout=20)
def oracle():
    
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

    future = oracle()
    try:
        reset = future.result()
    except TimeoutError:
        print("timeout")

    mat = matlab.engine.find_matlab()
    print("Engine")
    print(mat)
    
    print(warnings)
    # eng.quit()


