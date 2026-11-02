import os,tempfile
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db')
os.environ['JWT_SECRET']='test-secret-'*5
os.environ['ADMIN_PASSWORD']='Admin123456!'
os.environ['ENABLE_WORKER']='false'
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from datetime import timedelta
from app import app,Session,Reminder,now,stamp,select

def test_flow():
 with TestClient(app) as c:
  def login(email,password):return {'Authorization':'Bearer '+c.post('/auth/login',json={'email':email,'password':password}).json()['token']}
  admin=login('owner@example.com','Admin123456!')
  for name in ['alice','bob']:
   assert c.post('/auth/register',json={'email':name+'@example.com','password':'Password123!','name':name}).status_code==200
  alice=login('alice@example.com','Password123!');bob=login('bob@example.com','Password123!')
  assert c.get('/settings',headers=alice).status_code==403
  service=c.get('/services').json()[0]
  for i in range(2,10):
   date=(now()+timedelta(days=i)).date().isoformat();slots=c.get('/slots',params={'service_id':service['id'],'date':date}).json()
   if slots:break
  payload={'service_id':service['id'],'start':slots[0]}
  def book(h):return c.post('/appointments',headers=h,json=payload)
  with ThreadPoolExecutor(2) as pool:results=list(pool.map(book,[alice,bob]))
  assert sorted(r.status_code for r in results)==[200,409]
  winner=alice if results[0].status_code==200 else bob;loser=bob if winner==alice else alice
  a=next(r.json() for r in results if r.status_code==200)
  assert c.patch('/appointments/'+str(a['id']),headers=loser,json={'status':'cancelled'}).status_code==403
  assert c.patch('/appointments/'+str(a['id']),headers=admin,json={'status':'confirmed'}).status_code==200
  assert c.get(f"/appointments/{a['id']}/calendar",headers=winner).text.startswith('BEGIN:VCALENDAR')
  remaining=c.get('/slots',params={'service_id':service['id'],'date':date}).json()
  assert slots[0] not in remaining
  assert c.patch('/appointments/'+str(a['id']),headers=winner,json={'start':remaining[-1]}).status_code==200
  with Session.begin() as s:
   for job in s.scalars(select(Reminder).where(Reminder.state=='pending')):job.due=stamp(now()-timedelta(seconds=1))
  assert c.post('/jobs/run',headers=admin).status_code==200
  logs=c.get('/logs',headers=admin).json();assert logs and all(l['status']=='preview' for l in logs)
  c.post('/jobs/run',headers=admin);assert len(c.get('/logs',headers=admin).json())==len(logs)
  assert c.patch('/appointments/'+str(a['id']),headers=winner,json={'status':'cancelled'}).status_code==200
  settings=c.get('/settings',headers=admin).json(); body={**settings['config'],'hours':settings['hours'],'holidays':[{'date':date,'name':'Tatil'}]}
  assert c.put('/settings',headers=admin,json=body).status_code==200
  assert c.get('/slots',params={'service_id':service['id'],'date':date}).json()==[]
  assert c.get('/reports',headers=admin).json()['cancel_rate']==100
  assert c.get('/me/export',headers=winner).status_code==200
