from pathlib import Path
p=Path(__file__).resolve().parents[1]/'backend/.env'
for line in p.read_text().splitlines():
 if line.startswith(('ADMIN_EMAIL=','ADMIN_PASSWORD=')):print(line)
