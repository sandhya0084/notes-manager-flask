import py_compile
try:
    py_compile.compile(r'c:\Users\HP\Downloads\Notes_Manager-flask\notes-manager-flask\app.py', doraise=True)
    print('compiled OK')
except Exception as e:
    import traceback
    traceback.print_exc()
