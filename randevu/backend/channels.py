"""Optional provider adapters. Not enabled by default; obtain consent before activation."""
from typing import Protocol
import json, urllib.request
class NotificationChannel(Protocol):
 def send(self, recipient: str, text: str, idempotency_key: str) -> None: ...
class WebhookChannel:
 """For an SMS/WhatsApp provider gateway you control. URL and token are server secrets."""
 def __init__(self, url: str, token: str):
  if not url.startswith('https://'): raise ValueError('HTTPS required')
  self.url, self.token = url, token
 def send(self, recipient: str, text: str, idempotency_key: str) -> None:
  req=urllib.request.Request(self.url,data=json.dumps({'recipient':recipient,'text':text}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.token,'Idempotency-Key':idempotency_key},method='POST')
  with urllib.request.urlopen(req,timeout=20) as response:
   if response.status>=300: raise RuntimeError('Provider rejected notification')
