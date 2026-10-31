# Psikolog Asistanı · İlk Çalışan Prototip

Mobil ve masaüstü tarayıcıda çalışan, Türkçe React + Vite prototipi.

## Özellikler
- Kurgusal örnek danışan listesi ve yeni örnek danışan ekleme
- Seans notu ekleme/silme (yalnızca sayfa açıkken, bellekte)
- Birebir tekrar eden cümleleri sayma
- Kural tabanlı ifade kategorileri ve renkli vurgular
- Mobil uyumlu arayüz

**Önemli:** Bu sürüm gerçek yapay zekâ modeli kullanmaz. Tekrarlanan cümleler basit metin eşleştirmesiyle, temalar anahtar sözcüklerle belirlenir. Klinik tanı/karar üretmez.

## Çalıştırma
Bilgisayarda Node.js 20.19+ veya 22.12+ kurulu olmalıdır.

```bash
npm install
npm run dev
```

Tarayıcıda terminalde verilen adresi açın. Üretim derlemesi için `npm run build`.

## GitHub'a telefondan yükleme
1. GitHub deponuzda **Add file → Upload files** seçin.
2. ZIP'i telefonunuzda açın ve içindeki `index.html`, `package.json`, `README.md` ve `src` klasörünü (içindeki dosyalarla birlikte) yükleyin. Mobil GitHub çoklu klasör yüklemesini desteklemiyorsa bilgisayardan yükleyin veya tek tek **Create new file** ile `src/main.jsx` ve `src/style.css` yollarını oluşturun.
3. **Commit changes** ile kaydedin.

## Güvenlik ve sonraki aşama
Bu sürümde oturum açma, sunucu, kalıcı veritabanı, şifreleme, erişim kontrolü, yedekleme veya KVKK uyumlu işleme akışı **yoktur**. Gerçek danışan bilgisi girmeyin. Gerçek kullanımdan önce güvenli sunucu, kimlik doğrulama, yetkilendirme, denetim kayıtları, veri saklama/silme politikaları, hukuki değerlendirme ve yapay zekâ için özel veri koruma tasarımı gerekir.

Sonraki aşama: güvenli backend ve terapist onaylı, semantik benzerlik analizi.
