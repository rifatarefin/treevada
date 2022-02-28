from os import error
import matlab.engine
eng = matlab.engine.connect_matlab()
# eng.warning('off','all', nargout = 0)

try:
    
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
# comp = eng.sample([],[],[],'compile')
# comp = eng.sample([],[],[],'term')
print("comp")
# if comp:

print("True")

print("last")



mat = matlab.engine.find_matlab()
print("Engine")
print(mat)
eng.quit()

