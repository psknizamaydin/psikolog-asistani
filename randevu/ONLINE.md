# Bilgisayara kurulum yapmadan çalıştırma
1. https://github.com/codespaces/new?repo=psknizamaydin%2Fpsikolog-asistani&ref=randevu-online adresini açın.
2. Branch: randevu-online. Dev container configuration: Randevu Sistemi — Online. Create codespace seçin.
3. İlk kurulumun tamamlanmasını bekleyin. Uygulama otomatik başlar.
4. Ports sekmesinde 5173 / Randevu Uygulaması satırındaki Open in Browser (küre) düğmesini kullanın. Portu private bırakın.
5. Terminalde `python3 randevu/scripts/show_login.py` çalıştırın. Bu Codespace için rastgele üretilen işletme giriş bilgilerinizi gösterir. Şifrenizi paylaşmayın.
6. Bu bilgilerle giriş yapın. Müşteri denemesi için çıkış yapıp yeni hesap oluşturun.

Otomatik başlatma olmazsa: `python3 randevu/scripts/start_online.py`
Kurulum yarım kalırsa: `python3 randevu/scripts/setup_online.py` ardından başlatma komutu.

Frontend ve API aynı porttan /api proxy ile çalışır; yalnızca 5173 yönlendirilir. API portunu herkese açmayın. Parolalar ve .env dosyaları Git'e eklenmez. Veritabanı Codespace diskinde kalır; Codespace silinirse kayıtlar da silinir. Ortam durduğunda uygulama ve hatırlatıcılar durur. Burası test/geliştirme ortamıdır; sürekli müşteri erişimi için üretim hosting gerekir. Codespaces kota ve hesap koşulları GitHub'a tabidir; ücretli seçenek açmadan önce hesabınızın kullanım durumunu inceleyin.
