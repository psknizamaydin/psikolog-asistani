# Randevu Sistemi ve Hatırlatıcı

## 1. Mimari ve varsayımlar
React 19 + Tailwind 4 / Vite arayüz; FastAPI REST API; SQLAlchemy ORM; SQLite varsayılan, PostgreSQL seçeneği. JWT Bearer ile 8 saatlik oturum; bcrypt parola özeti. Veritabanında UTC ISO-8601 zamanları; arayüzde Europe/Istanbul.

Bu sürüm tek işletme ve tek ortak kaynak takvimidir. Birden çok personel aynı takvimi yönetir; bağımsız personel/oda takvimleri ve çok kiracılı SaaS kapsam dışıdır. Bekleyen ve onaylanan randevular saatleri kapatır. Saatler 15 dakikalık aralıklarla üretilir, hizmet süresi boyunca çakışma aranır. Ücretler kuruş cinsindedir ve randevuya anlık fiyat olarak kaydedilir. Müşteri iptal sınırı saat değiştirmede de uygulanır. Personel sınırdan muaftır. Reddedilen randevu cancelled olarak işaretlenir. Yeni hesaplar müşteridir. İşletme sahibi ortam değişkenlerinden ilk açılışta oluşturulur.

Bu teslim kaynak kod paketidir; internete yayınlanmamıştır. Üç adımlı rezervasyon akışı: hizmet → tarih/saat → onay. Günlük/haftalık/aylık takvim görünümleri seçilen dönemi ajanda kartlarıyla gösterir.

```
randevu/
  backend/
    app.py             # modeller, doğrulama, REST API ve worker
    channels.py        # opsiyonel SMS / WhatsApp webhook adaptörü
    cron.py            # tek seferlik job çalıştırma
    test_app.py        # eşzamanlılık ve uçtan uca API testi
    schema.sql         # PostgreSQL DDL
    openapi.json       # tüm istek/yanıt şemaları
    requirements.txt
    .env.example
  frontend/
    src/main.jsx       # Türkçe müşteri ve işletme panelleri
    src/style.css      # Tailwind + tasarım
    index.html
    vite.config.js
    package.json
    package-lock.json
    .env.example
  docker-compose.yml  # isteğe bağlı PostgreSQL ve Mailpit
  README.md
  SOURCE_CODE.md      # tüm metin kaynakları dosya dosya
```

## 2. Veritabanı şeması
Ayrıntılı PostgreSQL DDL: backend/schema.sql. SQLite tabloları aynı ORM modellerinden açılışta oluşturulur.

| Model | Temel alanlar | İlişki |
|---|---|---|
| User | id, email(unique), password(hash), name, role | Customer 1:1 |
| Customer | id, user_id(unique), phone, notes | Appointment 1:N |
| Service | id, name, duration, price, active | Appointment 1:N |
| Appointment | id, customer_id, service_id, start, end, status, price, version | Reminder 1:N |
| WorkingHours | day(PK, Pazartesi=0), start, end, break_start, break_end | İşletme takvimi |
| Holiday | date(PK), name | İşletme takvimi |
| Reminder | id, appointment_id, due, kind, text, state, attempts | NotificationLog 1:N |
| NotificationLog | id, reminder_id, recipient, channel, status, created, detail | Gönderim denemeleri |
| Setting | id=1, data(JSON metin) | Takvim/job kilitleme satırı |

Çakışma kontrolü ve yazma tek transaction içindedir: SQLite BEGIN IMMEDIATE; PostgreSQL ortak Setting satırı SELECT FOR UPDATE. Birden fazla API süreci aynı veritabanını kullanıyorsa da randevular sırayla doğrulanır. Doğrudan SQL ile randevu eklemek bu korumayı atlar; tüm yazmalar API üzerinden yapılmalıdır. SQLite tek sunucu/disk içindir.

## 3. API uç noktaları
Swagger: http://localhost:8000/docs. openapi.json ayrıntılı doğrulama ve yanıt şemalarını içerir.

| Metot | Yol | Yetki / işlev |
|---|---|---|
| POST | /auth/register | Müşteri kaydı |
| POST | /auth/login | JWT al |
| GET | /me | Oturum bilgisi |
| GET | /services | Aktif hizmetler, herkese açık |
| POST | /services | Personel/sahip: hizmet ekle |
| PUT, DELETE | /services/{id} | Düzenle / pasifleştir |
| GET | /slots?service_id=1&date=2026-12-01 | Müsait UTC saatler |
| GET | /appointments | Müşteri: kendi; personel: tümü |
| POST | /appointments | Müşteri: rezervasyon |
| PATCH | /appointments/{id} | Saat veya durum değiştir |
| GET | /appointments/{id}/calendar | Yetkili kullanıcı: .ics indir |
| GET | /customers | Personel: müşteri kayıtları |
| PUT | /customers/{id} | Personel: telefon / not düzenle |
| GET, PUT | /settings | Personel: çalışma saatleri, mola, tatil, şablon, süreler |
| GET | /logs | Personel: son 300 gönderim denemesi |
| POST | /jobs/run | Personel: vadesi gelen işleri işle |
| GET | /reports | Personel: günlük adet, iptal oranı, hizmet tercih sayısı |
| POST | /staff | Yalnız sahip: personel oluştur |
| GET | /me/export | Kendi verilerini JSON olarak al |

Personel eklemek için /docs üzerinden işletme hesabıyla giriş yapıp tokenı Authorize alanına girin. POST /staff e-posta, şifre, ad ve isteğe bağlı telefon alır. Halka açık kayıt endpoint'i personel rolü kabul etmez.

## 4. Kurulum
Python 3.11+ ve Node.js 22 önerilir. İki terminal açın. Windows'ta python yerine py kullanılabilir.

### Backend (birinci terminal)
```
cd randevu/backend
python -m venv .venv
```
Windows PowerShell:
```
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```
macOS/Linux:
```
source .venv/bin/activate
cp .env.example .env
```
.env içindeki JWT_SECRET değerini rastgele en az 32 karakterle, ADMIN_PASSWORD ve ADMIN_EMAIL değerlerini kendi bilgilerinizle değiştirin. Rastgele anahtar için:
```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Ardından:
```
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

### Frontend (ikinci terminal)
```
cd randevu/frontend
npm ci
npm run dev
```
http://localhost:5173 adresini açın. İşletme paneli için .env'deki yönetici bilgileriyle giriş yapın. Müşteri akışı için çıkış yapıp yeni hesap oluşturun. Örnek hizmetler otomatik yüklenir. frontend/.env.example, API adresi farklıysa frontend/.env olarak kopyalanmalıdır. VITE değişkenleri build sırasında gömülür ve sır içermemelidir.

### PostgreSQL (isteğe bağlı)
Kök dizinde POSTGRES_PASSWORD ortam değişkenini belirleyip:
```
docker compose up -d postgres
```
backend/.env içinde:
```
DATABASE_URL=postgresql+psycopg://randevu:PAROLANIZ@localhost:5432/randevu
```
API'yi yeniden başlatın. SQLite'taki kayıtlar otomatik taşınmaz. Üretim şema değişikliklerinde sürümlü migration ve yedekleme uygulanmalıdır; create_all mevcut sütunları migrate etmez.

## 5. Hatırlatıcılar ve test
Varsayılan süreler 1440 ve 60 dakika. Ayarlar panelinde değiştirilebilir. Oluşturma, güncelleme ve iptal ayrı anlık iş üretir. Bekleyen eski işler değişiklikte silinir ve yeni saat için yeniden planlanır. Gönderilmiş loglar korunur. İşletme ve müşteriye e-posta gider. SMTP alıcı tarafından okundu bilgisini sağlamaz; sent yalnız SMTP sunucusuna teslimi gösterir.

Gömülü worker 30 saniyede bir vadesi gelen işleri işler. Sürekli API işlemi gerekir. Alternatif gerçek cron kullanımı: ENABLE_WORKER=false yapın ve sunucuda cron tanımlayın:
```
* * * * * cd /absolute/path/randevu/backend && /absolute/path/randevu/backend/.venv/bin/python cron.py
```
Windows'ta Task Scheduler ile aynı komutu dakikada bir çalıştırın. Başarısız işler 2, 4, 8, 16 dakika sonra tekrar denenir; beşinci başarısız denemede failed olur. Bir iş için başarılı alıcı tekrar gönderilmez. SMTP ile gönderim en az bir kez garantisi hedefler; gönderim sonrası süreç çökmesi nadiren tekrar mesaja yol açabilir. SMTP exactly-once garantisi vermez. Worker veritabanı kilidini gönderim boyunca tutar: küçük işletme ölçeği için basit ve güvenli tercih; yoğun hacimde bağımsız kuyruk/outbox dispatcher gerekir.

### Sağlayıcısız test
1. MAIL_MODE=console bırakın.
2. Müşteri hesabından gelecekte bir randevu alın.
3. İşletme hesabıyla Hatırlatmalar → Bekleyen işleri çalıştır düğmesine basın.
4. İki alıcı için preview kaydı ve mesaj metni görünür. Bu gerçek e-posta değildir.
5. Hatırlatma sürelerini 2,1 dakika yapıp birkaç gün sonraki bir saate rezervasyon alın; süreleri beklemek yerine aşağıdaki otomatik testle job vadeleri öne çekilir.

```
cd backend
python -m pytest -q
```
Test geçici bir SQLite dosyası ve iki eşzamanlı istemci kullanır; gerçek veritabanını değiştirmez. Çakışma, yetkilendirme, onay, taşıma, iptal, tatil, rapor, .ics ve yinelenmeyen job işlemesini doğrular; reminder vadelerini test veritabanında geçmişe çeker.

### Gerçek SMTP testi
Kök dizinde:
```
docker compose up -d mailpit
```
.env: MAIL_MODE=smtp, SMTP_HOST=localhost, SMTP_PORT=1025, SMTP_TLS=false, SMTP_FROM=randevu@example.com; SMTP_USER ve SMTP_PASSWORD boş. API'yi yeniden başlatıp randevu oluşturun. http://localhost:8025 gelen e-postaları gösterir. Gerçek hizmette sağlayıcınızın SMTP bilgilerini ve TLS=true/587 yapılandırmasını kullanın. 465 örtük SSL bu adaptörde desteklenmez.

SMS/WhatsApp için channels.py HTTPS webhook adaptörü teslim edilmiştir; aktif gönderim/sağlayıcı hesabı ve panel seçeneği yoktur. Sağlayıcı bağlanırken telefon doğrulama, kanal tercihi ve izin kaydı eklenmeli; worker'a ayrı kanal/alıcı loglarıyla bağlanmalıdır. Google Calendar bağlantısı ve .ics dışa aktarımı çalışır; çift yönlü Google OAuth senkronizasyonu kapsam dışıdır.

## 6. Güvenlik, veri saklama ve üretim
Parolalar bcrypt, sorgular ORM parametreleriyle, yetki denetimleri backend'de, rate limit IP başına süreç belleğinde (giriş/kayıt 20/dk, diğer 180/dk). JWT sessionStorage'da tutulur, 8 saatte biter; yenileme/şifre sıfırlama/hesap doğrulama yoktur. Birden fazla süreçli üretimde Redis tabanlı dağıtık limit gerekir; ters proxy'de gerçek IP güvenini yapılandırın.

KVKK için veri minimizasyonu ve kullanıcı veri dışa aktarımı sağlanır; hukuki uygunluk sertifikası verilmez. İşletme kendi aydınlatma metnini, saklama süresini, silme/anonimleştirme sürecini, veri işleyen sözleşmelerini ve başvuru kanalını belirlemelidir. Otomatik süreli silme bu sürümde yoktur. Console modunda bildirim metinleri kişisel veri içerebilir; test verisi kullanın. Hassas sağlık notlarını bu genel amaçlı sisteme girmeyin. Veritabanı/backup için disk şifreleme ve erişim yetkisi sunucu sorumluluğundadır. Üretimde console modu yerine SMTP kullanın.

Üretim: frontend `npm run build` çıktısı dist/ dizinini HTTPS ile yayınlayın; API'yi servis yöneticisi altında uvicorn ile çalıştırın; FRONTEND_URL değerini tam alan adıyla güncelleyin; sırları paylaşmayın; veritabanını yedekleyin; örnek parolaları kaldırın. Aynı origin reverse proxy ve CSP önerilir. Dışarıya DB veya Mailpit portlarını açmayın. İnternete açık sunucu, alan adı ve SMTP hesabı bu pakete dahil değildir.

## 7. Doğrulama sınırları
API entegrasyon testi SQLite ile çalıştırılmıştır. Frontend üretim derlemesi kontrol edilmiştir. PostgreSQL, gerçek SMTP ve tarayıcı üzerinden görsel/etkileşim testi bu teslim ortamında yapılmamıştır. Kaynak kodlar paket içinde dosya dosya bulunur; tek belge olarak okumak için SOURCE_CODE.md dosyasını açın.
