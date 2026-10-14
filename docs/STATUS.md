# ISOSentinel v0.1 Durumu

## Hedef

YKS çalışma oturumunu başlatıp yönetmek, oturum sırasında Process Guard ile süreç ihlallerini kaydetmek ve temel oturum/soru verisini SQLite'ta saklamak.

## Doğrulanmış mevcut durum

- PyQt dashboard, oturum yaşam döngüsü, recovery akışı ve Process Guard kaynak kodda mevcut.
- Uygulama girişinde `DashboardWindow` artık oluşturulup gösteriliyor.
- Normal pencere kapanışı, aktif oturumu `INTERRUPTED` olarak kapatır; zamanlayıcıları durdurur ve recovery kaydını temizler.
- Oturumun normal bitişi/iptali, recovery stale-kayıt temizliği ve Event Bus üzerinden Process Guard taraması otomatik testlerle doğrulandı.
- Guard/policy/cache davranışı için kaynakta testler bulunuyor.

## Test durumu

- `.venv\\Scripts\\python.exe -m pytest -q` sonucu: `28 passed`.
- `python -m compileall -q main.py core database restrictions ui tests` ve `git diff --check` başarılı.
- Bu ortamda gerçek PyQt widget örneğiyle çalışan headless test `-1073740791` ile çöktüğü için UI metot bağları event loop oluşturmadan mock'larla sınanıyor. Gerçek masaüstü UI ve gerçek süreç sonlandırma davranışı manuel doğrulama gerektirir.

## Sıradaki tek iş

Windows masaüstünde uygulamayı açıp bir oturum başlatma, iptal etme ve kontrollü bir test süreciyle Process Guard davranışını manuel doğrulamak.
