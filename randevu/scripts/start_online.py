from pathlib import Path
import os,subprocess,socket
root=Path(__file__).resolve().parents[1]
def running(port):
 with socket.socket() as sock:return sock.connect_ex(('127.0.0.1',port))==0
for port,cmd,cwd in [(8000,[str(root/'backend/.venv/bin/python'),'-m','uvicorn','app:app','--host','127.0.0.1','--port','8000'],root/'backend'),(5173,['npm','run','dev','--','--port','5173'],root/'frontend')]:
 if not running(port):
  with (root/f'server-{port}.log').open('a') as log:subprocess.Popen(cmd,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print('Uygulama: http://localhost:5173 — Ports sekmesinden Open in Browser seçin.')
print('Giriş bilgileri için: python3 randevu/scripts/show_login.py')
