import traceback
path = r'c:\Users\HP\Downloads\Notes_Manager-flask\notes-manager-flask\app.py'
try:
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    compile(src, path, 'exec')
    print('OK')
except Exception:
    traceback.print_exc()
