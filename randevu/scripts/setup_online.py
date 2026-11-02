from pathlib import Path
import subprocess,sys,secrets
root=Path(__file__).resolve().parents[1]
def run(args,cwd): subprocess.run(args,cwd=cwd,check=True)
run([sys.executable,'-m','venv','.venv'],root/'backend')
python=root/'backend/.venv/bin/python'
run([str(python),'-m','pip','install','-r','requirements.txt'],root/'backend')
run(['npm','ci'],root/'frontend')
env=root/'backend/.env'
if not env.exists():
 env.write_text('JWT_SECRET='+secrets.token_urlsafe(48)+'\nADMIN_EMAIL=owner@example.com\nADMIN_PASSWORD='+secrets.token_urlsafe(16)+'\nMAIL_MODE=console\nENABLE_WORKER=true\nFRONTEND_URL=http://localhost:5173\n')
 env.chmod(0o600)
(root/'frontend/.env').write_text('VITE_API_URL=/api\n')
print('Kurulum tamamlandı. Uygulama otomatik başlatılacak.')
