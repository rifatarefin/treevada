# from os import error
# import matlab.engine
# eng = matlab.engine.start_matlab()
# # eng.warning('off','all', nargout = 0)
# try:
#     eng.load_system('sample.mdl')
#     model = eng.bdroot()
#     comp = eng.slreportgen.utils.compileModel(model, nargout = 0)
#     # comp = eng.sample([],[],[],'compile')
#     # comp = eng.sample([],[],[],'term')
#     print(comp)
#     # if comp:
#     eng.slreportgen.utils.uncompileModel(model, nargout = 0)
#     eng.close_system('sample.mdl', nargout = 0)
#     print("True")

# except error:
#     print(error)
#     print("Error")
# eng.quit()

with open("file.txt", "w") as f:
    f.write("kse")