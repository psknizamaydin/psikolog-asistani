import os, json, secrets, time, hashlib, smtplib, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from email.message import EmailMessage
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from threading import Thread, Event
import bcrypt, jwt
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, String, Integer, Text, ForeignKey, select, event, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
load_dotenv()
URL=os.getenv('DATABASE_URL','sqlite:///./randevu.db')
SECRET=os.getenv('JWT_SECRET','')
if len(SECRET)<32: raise RuntimeError('JWT_SECRET en az 32 karakter olmalı; .env dosyasını hazırlayın.')
engine=create_engine(URL,connect_args={'check_same_thread':False,'timeout':30} if URL.startswith('sqlite') else {},pool_pre_ping=True)
if URL.startswith('sqlite'):
 @event.listens_for(engine,'connect')
 def pragmas(dbapi, _): dbapi.execute('PRAGMA foreign_keys=ON'); dbapi.execute('PRAGMA journal_mode=WAL')
Session=sessionmaker(engine,expire_on_commit=False)
class Base(DeclarativeBase): pass
class User(Base):
 __tablename__='users'
 id:Mapped[int]=mapped_column(primary_key=True)
 email:Mapped[str]=mapped_column(String(254),unique=True)
 password:Mapped[str]=mapped_column(String(255))
 name:Mapped[str]=mapped_column(String(120))
 role:Mapped[str]=mapped_column(String(20),default='customer')
class Customer(Base):
 __tablename__='customers'
 id:Mapped[int]=mapped_column(primary_key=True)
 user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),unique=True)
 phone:Mapped[str]=mapped_column(String(30),default='')
 notes:Mapped[str]=mapped_column(Text,default='')
class Service(Base):
 __tablename__='services'
 id:Mapped[int]=mapped_column(primary_key=True)
 name:Mapped[str]=mapped_column(String(120))
 duration:Mapped[int]=mapped_column(Integer)
 price:Mapped[int]=mapped_column(Integer)
 active:Mapped[int]=mapped_column(default=1)
class Appointment(Base):
 __tablename__='appointments'
 id:Mapped[int]=mapped_column(primary_key=True)
 customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True)
 service_id:Mapped[int]=mapped_column(ForeignKey('services.id'))
 start:Mapped[str]=mapped_column(String(32),index=True)
 end:Mapped[str]=mapped_column(String(32))
 status:Mapped[str]=mapped_column(String(20),default='pending')
 price:Mapped[int]=mapped_column(Integer)
 version:Mapped[int]=mapped_column(default=1)
class WorkingHours(Base):
 __tablename__='working_hours'
 day:Mapped[int]=mapped_column(primary_key=True)
 start:Mapped[str]=mapped_column(String(5))
 end:Mapped[str]=mapped_column(String(5))
 break_start:Mapped[str]=mapped_column(String(5))
 break_end:Mapped[str]=mapped_column(String(5))
class Holiday(Base):
 __tablename__='holidays'
 date:Mapped[str]=mapped_column(String(10),primary_key=True)
 name:Mapped[str]=mapped_column(String(120))
class Reminder(Base):
 __tablename__='reminders'
 id:Mapped[int]=mapped_column(primary_key=True)
 appointment_id:Mapped[int]=mapped_column(ForeignKey('appointments.id'),index=True)
 due:Mapped[str]=mapped_column(String(32),index=True)
 kind:Mapped[str]=mapped_column(String(30))
 text:Mapped[str]=mapped_column(Text)
 state:Mapped[str]=mapped_column(String(20),default='pending',index=True)
 attempts:Mapped[int]=mapped_column(default=0)
class NotificationLog(Base):
 __tablename__='notification_logs'
 id:Mapped[int]=mapped_column(primary_key=True)
 reminder_id:Mapped[int]=mapped_column(ForeignKey('reminders.id'))
 recipient:Mapped[str]=mapped_column(String(254))
 channel:Mapped[str]=mapped_column(String(20))
 status:Mapped[str]=mapped_column(String(20))
 created:Mapped[str]=mapped_column(String(32))
 detail:Mapped[str]=mapped_column(Text,default='')
class Setting(Base):
 __tablename__='settings'
 id:Mapped[int]=mapped_column(primary_key=True,default=1)
 data:Mapped[str]=mapped_column(Text)
DEFAULT={'timezone':'Europe/Istanbul','cancel_hours':6,'reminder_minutes':[1440,60],'template':'Merhaba {name}, {service} randevunuz: {date}. Durum: {status}.','business_email':os.getenv('BUSINESS_EMAIL','owner@example.com')}
def now(): return datetime.now(timezone.utc)
def stamp(d): return d.astimezone(timezone.utc).isoformat(timespec='seconds')
def parse(s): return datetime.fromisoformat(s)
def cfg(s): return json.loads(s.get(Setting,1).data)
def row(o): return {c.name:getattr(o,c.name) for c in o.__table__.columns}
def lock(s):
 if URL.startswith('sqlite'): s.connection().exec_driver_sql('BEGIN IMMEDIATE')
 else: s.execute(select(Setting).where(Setting.id==1).with_for_update()).scalar_one()
def initialize():
 Base.metadata.create_all(engine)
 with Session.begin() as s:
  if not s.get(Setting,1):
   s.add(Setting(id=1,data=json.dumps(DEFAULT)))
   for d in range(5): s.add(WorkingHours(day=d,start='09:00',end='18:00',break_start='12:00',break_end='13:00'))
   s.add_all([Service(name='Danışmanlık',duration=50,price=150000),Service(name='Ön görüşme',duration=30,price=75000)])
  if os.getenv('ADMIN_PASSWORD') and not s.scalar(select(User).where(User.email==os.getenv('ADMIN_EMAIL','owner@example.com'))):
   s.add(User(email=os.getenv('ADMIN_EMAIL','owner@example.com'),name='İşletme Yöneticisi',role='owner',password=bcrypt.hashpw(os.environ['ADMIN_PASSWORD'].encode(),bcrypt.gensalt()).decode()))
def available(s,service,date,exclude=None):
 c=cfg(s); tz=ZoneInfo(c['timezone']); day=datetime.strptime(date,'%Y-%m-%d'); w=s.get(WorkingHours,day.weekday())
 if not w or s.get(Holiday,date): return []
 local=lambda t: datetime.fromisoformat(date+'T'+t).replace(tzinfo=tz)
 start,finish=local(w.start),local(w.end); out=[]
 busy=s.scalars(select(Appointment).where(Appointment.status.in_(['pending','confirmed']),Appointment.id!=exclude if exclude else True)).all()
 while start+timedelta(minutes=service.duration)<=finish:
  end=start+timedelta(minutes=service.duration)
  if start>now() and not (w.break_start and start<local(w.break_end) and end>local(w.break_start)) and not any(start<parse(a.end) and end>parse(a.start) for a in busy): out.append(stamp(start))
  start+=timedelta(minutes=15)
 return out
def enqueue(s,a,kind):
 s.execute(delete(Reminder).where(Reminder.appointment_id==a.id,Reminder.state=='pending'))
 c=cfg(s); customer=s.get(Customer,a.customer_id); u=s.get(User,customer.user_id); service=s.get(Service,a.service_id)
 text=c['template'].format(name=u.name,service=service.name,date=parse(a.start).astimezone(ZoneInfo(c['timezone'])).strftime('%d.%m.%Y %H:%M'),status={'pending':'Beklemede','confirmed':'Onaylandı','cancelled':'İptal edildi','completed':'Tamamlandı','no_show':'Gelmedi'}[a.status])
 s.add(Reminder(appointment_id=a.id,due=stamp(now()),kind=kind,text=text))
 if a.status in ['pending','confirmed']:
  for minutes in set(c['reminder_minutes']):
   due=parse(a.start)-timedelta(minutes=minutes)
   if due>now(): s.add(Reminder(appointment_id=a.id,due=stamp(due),kind='reminder',text=text))
def deliver(recipient,text,key):
 if os.getenv('MAIL_MODE','console')=='console': return 'preview'
 msg=EmailMessage(); msg['From']=os.environ['SMTP_FROM']; msg['To']=recipient; msg['Subject']='Randevu bildirimi'; msg['Message-ID']=f'<{key}@randevu.local>'; msg.set_content(text)
 with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.getenv('SMTP_PORT','587')),timeout=20) as client:
  if os.getenv('SMTP_TLS','true')=='true': client.starttls()
  if os.getenv('SMTP_USER'): client.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD'])
  client.send_message(msg)
 return 'sent'
def run_jobs():
 # A database lock serializes job workers and booking mutations. SMTP is at-least-once.
 with Session() as s:
  lock(s)
  jobs=s.scalars(select(Reminder).where(Reminder.state=='pending',Reminder.due<=stamp(now())).limit(50)).all()
  for job in jobs:
   a=s.get(Appointment,job.appointment_id); customer=s.get(Customer,a.customer_id); u=s.get(User,customer.user_id)
   targets=set([u.email,cfg(s)['business_email']]); failed=False
   for email in targets:
    if s.scalar(select(NotificationLog).where(NotificationLog.reminder_id==job.id,NotificationLog.recipient==email,NotificationLog.status.in_(['sent','preview']))): continue
    try: status=deliver(email,job.text,hashlib.sha256(f'{job.id}:{email}'.encode()).hexdigest()); detail=job.text if status=='preview' else ''
    except Exception as e: status='failed'; detail=type(e).__name__; failed=True
    s.add(NotificationLog(reminder_id=job.id,recipient=email,channel='email',status=status,created=stamp(now()),detail=detail))
   job.attempts+=1; job.state=('failed' if job.attempts>=5 else 'pending') if failed else 'sent'
   if failed: job.due=stamp(now()+timedelta(minutes=2**job.attempts))
  s.commit()
 return len(jobs)
stop=Event()
def worker():
 while not stop.wait(30):
  try: run_jobs()
  except Exception: pass
@asynccontextmanager
async def lifespan(app):
 initialize(); stop.clear()
 if os.getenv('ENABLE_WORKER','true')=='true': Thread(target=worker,daemon=True).start()
 yield
 stop.set()
app=FastAPI(title='Randevu Sistemi',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[os.getenv('FRONTEND_URL','http://localhost:5173')],allow_methods=['GET','POST','PATCH','PUT','DELETE'],allow_headers=['Authorization','Content-Type'])
buckets=defaultdict(deque)
@app.middleware('http')
async def security(request:Request,call_next):
 key=(request.client.host,request.url.path.startswith('/auth')); q=buckets[key]; t=time.monotonic(); limit=20 if key[1] else 180
 while q and q[0]<t-60:q.popleft()
 if len(q)>=limit:return Response('Çok fazla istek',429)
 q.append(t)
 if len(buckets)>10000:
  for k in list(buckets):
   if not buckets[k] or buckets[k][-1]<t-60: del buckets[k]
 response=await call_next(request); response.headers['X-Content-Type-Options']='nosniff'; response.headers['Cache-Control']='no-store'; response.headers['Referrer-Policy']='same-origin'; return response
bearer=HTTPBearer()
def db():
 with Session() as s: yield s
def user(token=Depends(bearer),s=Depends(db)):
 try: payload=jwt.decode(token.credentials,SECRET,algorithms=['HS256']); u=s.get(User,int(payload['sub'])); assert u
 except Exception: raise HTTPException(401,'Oturum geçersiz')
 return u
def staff(u=Depends(user)):
 if u.role not in ['owner','staff']:raise HTTPException(403,'Yetki gerekli')
 return u
class Register(BaseModel):
 email:EmailStr
 password:str=Field(min_length=10,max_length=72)
 name:str=Field(min_length=2,max_length=120)
 phone:str=Field(default='',max_length=30)
class Login(BaseModel):
 email:EmailStr
 password:str=Field(max_length=72)
@app.post('/auth/register')
def register(x:Register,s=Depends(db)):
 if len(x.password.encode())>72:raise HTTPException(422,'Şifre UTF-8 olarak en fazla 72 bayt olmalı')
 if s.scalar(select(User).where(User.email==x.email.lower())):raise HTTPException(409,'E-posta kayıtlı')
 u=User(email=x.email.lower(),name=x.name,password=bcrypt.hashpw(x.password.encode(),bcrypt.gensalt()).decode()); s.add(u); s.flush(); s.add(Customer(user_id=u.id,phone=x.phone)); s.commit(); return {'ok':True}
@app.post('/auth/login')
def login(x:Login,s=Depends(db)):
 u=s.scalar(select(User).where(User.email==x.email.lower()))
 if not u or len(x.password.encode())>72 or not bcrypt.checkpw(x.password.encode(),u.password.encode()):raise HTTPException(401,'E-posta veya şifre hatalı')
 return {'token':jwt.encode({'sub':str(u.id),'exp':now()+timedelta(hours=8)},SECRET,algorithm='HS256'),'user':{'name':u.name,'role':u.role}}
@app.get('/me')
def me(u=Depends(user)):return {'name':u.name,'role':u.role,'email':u.email}
@app.get('/services')
def services(s=Depends(db)):return [row(a) for a in s.scalars(select(Service).where(Service.active==1))]
class ServiceIn(BaseModel):
 name:str=Field(min_length=2,max_length=120)
 duration:int=Field(ge=15,le=480)
 price:int=Field(ge=0,le=100000000)
@app.post('/services')
def service_add(x:ServiceIn,u=Depends(staff),s=Depends(db)):
 a=Service(**x.model_dump());s.add(a);s.commit();return row(a)
@app.put('/services/{id}')
def service_edit(id:int,x:ServiceIn,u=Depends(staff),s=Depends(db)):
 a=s.get(Service,id)
 if not a:raise HTTPException(404,'Hizmet bulunamadı')
 for k,v in x.model_dump().items():setattr(a,k,v)
 s.commit();return row(a)
@app.delete('/services/{id}')
def service_delete(id:int,u=Depends(staff),s=Depends(db)):
 a=s.get(Service,id)
 if not a:raise HTTPException(404,'Hizmet bulunamadı')
 a.active=0;s.commit();return {'ok':True}
@app.get('/slots')
def slots(service_id:int,date:str,s=Depends(db)):
 service=s.get(Service,service_id)
 if not service or not service.active:raise HTTPException(404,'Hizmet bulunamadı')
 try:return available(s,service,date)
 except ValueError:raise HTTPException(422,'Tarih geçersiz')
class Booking(BaseModel):
 service_id:int
 start:datetime
@app.get('/appointments')
def appointments(u=Depends(user),s=Depends(db)):
 q=select(Appointment)
 if u.role=='customer':q=q.join(Customer).where(Customer.user_id==u.id)
 out=[]
 for a in s.scalars(q.order_by(Appointment.start.desc())):
  c=s.get(Customer,a.customer_id); person=s.get(User,c.user_id)
  out.append({**row(a),'customer':person.name,'email':person.email,'phone':c.phone,'service':s.get(Service,a.service_id).name})
 return out
@app.post('/appointments')
def book(x:Booking,u=Depends(user),s=Depends(db)):
 lock(s)
 c=s.scalar(select(Customer).where(Customer.user_id==u.id)); service=s.get(Service,x.service_id)
 if not c:raise HTTPException(400,'Randevu için müşteri hesabı kullanın')
 if not service or not service.active:raise HTTPException(404,'Hizmet bulunamadı')
 if not x.start.tzinfo:raise HTTPException(422,'Saat dilimi gerekli')
 start=stamp(x.start); date=x.start.astimezone(ZoneInfo(cfg(s)['timezone'])).date().isoformat()
 if start not in available(s,service,date):raise HTTPException(409,'Bu saat artık müsait değil')
 a=Appointment(customer_id=c.id,service_id=service.id,start=start,end=stamp(x.start+timedelta(minutes=service.duration)),price=service.price);s.add(a);s.flush();enqueue(s,a,'created');s.commit();return row(a)
class Change(BaseModel):
 start:datetime|None=None
 status:str|None=None
@app.patch('/appointments/{id}')
def change(id:int,x:Change,u=Depends(user),s=Depends(db)):
 lock(s); a=s.get(Appointment,id)
 if not a:raise HTTPException(404,'Randevu bulunamadı')
 owner=s.get(Customer,a.customer_id).user_id==u.id
 if u.role=='customer':
  if not owner:raise HTTPException(403,'Yetki yok')
  if a.status not in ['pending','confirmed'] or parse(a.start)-now()<timedelta(hours=cfg(s)['cancel_hours']):raise HTTPException(400,'İptal/değişiklik süresi doldu')
  if x.status and x.status!='cancelled':raise HTTPException(403,'Durum değiştirilemez')
 if x.start:
  if a.status not in ['pending','confirmed'] or not x.start.tzinfo:raise HTTPException(400,'Randevu taşınamaz')
  service=s.get(Service,a.service_id); date=x.start.astimezone(ZoneInfo(cfg(s)['timezone'])).date().isoformat()
  if stamp(x.start) not in available(s,service,date,a.id):raise HTTPException(409,'Saat müsait değil')
  a.start=stamp(x.start);a.end=stamp(x.start+timedelta(minutes=service.duration));a.status='pending'
 if x.status:
  transitions={'pending':['confirmed','cancelled'],'confirmed':['completed','no_show','cancelled'],'cancelled':[],'completed':[],'no_show':[]}
  if x.status not in transitions[a.status]:raise HTTPException(400,'Geçersiz durum geçişi')
  a.status=x.status
 a.version+=1;enqueue(s,a,'updated');s.commit();return row(a)
@app.get('/appointments/{id}/calendar')
def calendar(id:int,u=Depends(user),s=Depends(db)):
 a=s.get(Appointment,id)
 if not a:raise HTTPException(404,'Bulunamadı')
 if u.role=='customer' and s.get(Customer,a.customer_id).user_id!=u.id:raise HTTPException(403,'Yetki yok')
 fmt=lambda x:parse(x).strftime('%Y%m%dT%H%M%SZ')
 content='\r\n'.join(['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Randevu//TR','BEGIN:VEVENT',f'UID:appointment-{a.id}@randevu',f'DTSTAMP:{now().strftime("%Y%m%dT%H%M%SZ")}',f'SEQUENCE:{a.version}',f'DTSTART:{fmt(a.start)}',f'DTEND:{fmt(a.end)}','SUMMARY:Randevu',f'STATUS:{"CANCELLED" if a.status=="cancelled" else "CONFIRMED"}','END:VEVENT','END:VCALENDAR',''])
 return Response(content,media_type='text/calendar',headers={'Content-Disposition':f'attachment; filename="randevu-{id}.ics"'})
@app.get('/customers')
def customers(u=Depends(staff),s=Depends(db)):
 return [{**row(c),'name':s.get(User,c.user_id).name,'email':s.get(User,c.user_id).email} for c in s.scalars(select(Customer))]
class CustomerEdit(BaseModel):
 phone:str=Field(max_length=30)
 notes:str=Field(max_length=5000)
@app.put('/customers/{id}')
def customer_edit(id:int,x:CustomerEdit,u=Depends(staff),s=Depends(db)):
 c=s.get(Customer,id)
 if not c:raise HTTPException(404,'Bulunamadı')
 c.phone=x.phone;c.notes=x.notes;s.commit();return row(c)
@app.get('/settings')
def settings(u=Depends(staff),s=Depends(db)):return {'config':cfg(s),'hours':[row(x) for x in s.scalars(select(WorkingHours))],'holidays':[row(x) for x in s.scalars(select(Holiday))]}
class Hours(BaseModel):
 day:int=Field(ge=0,le=6)
 start:str
 end:str
 break_start:str=''
 break_end:str=''
class SettingsIn(BaseModel):
 timezone:str='Europe/Istanbul'
 cancel_hours:int=Field(ge=0,le=720)
 reminder_minutes:list[int]=Field(max_length=10)
 template:str=Field(min_length=10,max_length=2000)
 business_email:EmailStr
 hours:list[Hours]
 holidays:list[dict[str,str]]
@app.put('/settings')
def set_settings(x:SettingsIn,u=Depends(staff),s=Depends(db)):
 try:
  ZoneInfo(x.timezone)
  if any(v<1 or v>43200 for v in x.reminder_minutes):raise ValueError()
  x.template.format(name='a',service='b',date='c',status='d')
  if len({w.day for w in x.hours})!=len(x.hours):raise ValueError()
  for w in x.hours:
   for t in [w.start,w.end]+([w.break_start,w.break_end] if w.break_start or w.break_end else []):datetime.strptime(t,'%H:%M')
   if w.start>=w.end or (w.break_start and not w.start<=w.break_start<w.break_end<=w.end):raise ValueError()
  for h in x.holidays:datetime.strptime(h['date'],'%Y-%m-%d');assert len(h['name'])<=120
 except Exception:raise HTTPException(422,'Ayarları, saatleri veya şablon alanlarını kontrol edin')
 lock(s);s.get(Setting,1).data=json.dumps(x.model_dump(exclude={'hours','holidays'}));s.execute(delete(WorkingHours));s.execute(delete(Holiday))
 s.add_all([WorkingHours(**w.model_dump()) for w in x.hours]);s.add_all([Holiday(date=h['date'],name=h['name']) for h in x.holidays]);s.commit();return {'ok':True}
@app.get('/logs')
def logs(u=Depends(staff),s=Depends(db)):return [row(l) for l in s.scalars(select(NotificationLog).order_by(NotificationLog.id.desc()).limit(300))]
@app.post('/jobs/run')
def jobs(u=Depends(staff)):return {'processed':run_jobs()}
@app.get('/reports')
def reports(u=Depends(staff),s=Depends(db)):
 a=s.scalars(select(Appointment)).all(); daily=defaultdict(int); popular=defaultdict(int)
 for x in a:daily[parse(x.start).astimezone(ZoneInfo(cfg(s)['timezone'])).date().isoformat()]+=1;popular[s.get(Service,x.service_id).name]+=1
 return {'total':len(a),'cancel_rate':round(sum(x.status=='cancelled' for x in a)/len(a)*100,1) if a else 0,'daily':dict(daily),'popular':dict(popular)}
@app.get('/me/export')
def export(u=Depends(user),s=Depends(db)):
 c=s.scalar(select(Customer).where(Customer.user_id==u.id));return {'user':{'name':u.name,'email':u.email},'customer':row(c) if c else None,'appointments':appointments(u,s)}
@app.post('/staff')
def add_staff(x:Register,u=Depends(staff),s=Depends(db)):
 if u.role!='owner':raise HTTPException(403,'Yalnızca işletme sahibi personel ekleyebilir')
 if len(x.password.encode())>72:raise HTTPException(422,'Şifre UTF-8 olarak en fazla 72 bayt olmalı')
 if s.scalar(select(User).where(User.email==x.email.lower())):raise HTTPException(409,'E-posta kayıtlı')
 person=User(email=x.email.lower(),name=x.name,role='staff',password=bcrypt.hashpw(x.password.encode(),bcrypt.gensalt()).decode());s.add(person);s.commit();return {'id':person.id,'name':person.name,'role':person.role}
