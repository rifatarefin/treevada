from cgitb import reset
from os import error
import matlab.engine
import multiprocessing
from pebble import concurrent
from concurrent.futures import TimeoutError
# eng.warning('off','all', nargout = 0)
@concurrent.process(timeout=10)
def oracle():
    try:
        
        eng = matlab.engine.connect_matlab()
        eng.load_system('sample.mdl')
        print("load")
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
    except:
        print("doesn't load")

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
    # eng.quit()

