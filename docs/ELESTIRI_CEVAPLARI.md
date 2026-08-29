# Eleştirilere Cevaplar

**Tarih:** 26 Ağustos 2026
**Kapsam:** S1.x (formülasyon), S2.x (deney tasarımı), S3.x (metrikler), S4.x (literatür) + 5 zorunlu soru

**Genel değerlendirme:** Eleştirilerin çoğu haklı ve kabul ediyorum. Üçünde
veriye/türetmeye dayalı itirazım var (S1.1, S1.2, S2.1b). Aşağıda her madde için
**KABUL / KISMEN / İTİRAZ** hükmü ve gerekçe var.

---

# 1. Formülasyon

## S1.1 — Lookahead mı, HOCBF mı? → KISMEN KABUL + teknik itiraz

**Kabul ettiğim kısım:** D1 kararı gerekçelendirilmemiş. "Daha basit ve unicycle
için standart" gerekçesi metne yazılmalı. Ve lookahead'in gövde garantisi kaybı
(d_safe'e +L eklemek zorunda kalmamız) **gerçekten lookahead'e özgü bir bedel** —
HOCBF bunu üretmezdi. Bu maddeyi kabul ediyorum.

**İtiraz ettiğim kısım:** "HOCBF bu iki problemin *hiçbirini* üretmezdi" ifadesi
kafa-kafaya dejenerasyon için **doğru değil.** Türetme:

```
e = p_robot − p_engel,   n = [cos θ, sin θ],   n⊥ = [−sin θ, cos θ]

h   = ‖e‖² − d²
h'  = 2e·(v·n − v_o)                          <- ω YOK (bağıl derece 2)
h'' = 2‖e'‖² + 2e·(v'·n + v·ω·n⊥ − v_o')
                          └────────┘
                  ω'nın TEK giriş yeri:  2·v·ω·(e·n⊥)
```

Kafa-kafaya durumda robot engele bakıyor, yani **e ∥ n** → `e·n⊥ = 0` →
**ω'nın katsayısı h''de de sıfır.** Yani HOCBF de aynı noktada dejenere olur.

Bizim lookahead formülasyonumuzda ω'nın katsayısı `2L(Δp·n⊥)` — aynı `(·n⊥)`
yapısı, aynı yerde sıfırlanıyor.

**Sonuç:** kafa-kafaya dejenerasyon **formülasyonun değil geometrinin** özelliği
(e ∥ n simetrisi). ω-kanalı `e·n⊥` üzerinden giren *her* formülasyon orada çöker.
Bu, tezin gözlemini zayıflatmıyor — **güçlendiriyor**: artık "bizim seçimimizin
kusuru" değil "yapısal bir tekillik" olarak savunulabilir.

**Yapılacak:** (a) D1 gerekçesini metne yaz, (b) yukarıdaki türetmeyi tez metnine
koy, (c) HOCBF'i 5. mod olarak ekleyip ölç — gövde-garantisi farkını göstermek için
(dejenerasyon farkı çıkmayacak; o da bir bulgu).

## S1.2 — Neden h = ‖e‖² − d²? → KABUL (test edilmedi) + türetme itirazı

Test etmedik, kabul. Ama "uzakta gevşek, yakında sert" yönü türetmeye göre **ters**:

```
Lineer  h1 = ‖e‖ − d     :  h1' = ê·e'          kısıt:  ê·e' ≥ −α(‖e‖−d)
Kare    h2 = ‖e‖² − d²   :  h2' = 2‖e‖(ê·e')    kısıt:  ê·e' ≥ −α(‖e‖²−d²)/(2‖e‖)

İzin verilen yaklaşma hızlarının oranı (kare / lineer) = (‖e‖+d) / (2‖e‖)

   ‖e‖ = d   (sınırda) -> 1.00   İKİSİ AYNI
   ‖e‖ = 2d            -> 0.75   kare DAHA KISITLAYICI
   ‖e‖ = 10d           -> 0.55   kare DAHA KISITLAYICI
```

Yani kare form **uzakta daha konservatif**, sınırda ikisi çakışıyor. Bu, α
duyarlılığımızı açıklıyor olabilir ama iddia edilen yönde değil.

**Yapılacak:** `h = ‖e‖ − d` varyantını bir mod olarak ekleyip aynı sınır takibiyle
ölç. Ucuz: tek fonksiyon değişikliği + 1 kampanya.

## S1.3 — Neden α(h) = γh? → TAM KABUL

Haklısınız. Sadece skaler γ tarandı, **fonksiyon formu hiç taranmadı.** "α=1.0
optimaldir" iddiası ancak **lineer aile içinde ve test edilen {0.3, 0.5, 1.0, 2.0}
kümesinde** geçerli.

**Yapılacak:** (a) metindeki iddiayı hemen bu şekilde nitele, (b) γh^p (p={0.5,1,2})
ve tanh-doygun formu ekle — bunlar tam da bizim gördüğümüz "küçük γ dondurur / büyük
γ doygunluğa sokar" ikilemi için önerilmiş.

## S1.4 — v_min = 0 kararı → TAM KABUL, ciddi bir tutarsızlık

Bu bir tutarsızlık ve kabul ediyorum:

| Aşama | Maliyet | v_min=−0.22 sonucu |
|---|---|---|
| İŞ 5.2 | normalize DEĞİL | çarpışma 0/10 → 10/10, "zararlı" |
| İŞ 5.4-A | normalize | çarpışma 0/10 → 0/10, **zararsız** |
| Ana kampanya | normalize | **yine de v_min=0 kullanıldı** |

Yani artefakt olduğu kanıtlanmış eski bulguya dayanan bir kısıtı taşımaya devam
ettik. Ve haklısınız: geri gitme, hızlı yaklaşan engele karşı en doğrudan kaçış —
kapatmak **ölçtüğümüz v_crit'i aşağı çekiyor olabilir.**

**Yapılacak:** v_min'i tasarım sabiti olmaktan çıkarıp **tarama ekseni** yap
({0, −0.11, −0.22}). Sonuç sınırı yukarı çekerse, mevcut tüm v_crit'ler
"v_min=0 koşullu" diye nitelenmeli.

## S1.5 — ρ nerede? → TAM KABUL, en somut açık

ρ = 500.0 (`params.py: slack_rho`). Raporda yazılmaması eksiklik, **taranmamış
olması daha büyük eksiklik.**

Mantık zinciriniz doğru: `delta_active_rate` → feasibility sınırı, δ ise doğrudan
ρ'nun fonksiyonu. Yani **üç sınır eğrimizden biri, ölçülmemiş bir parametreye
koşullu.** w_w'yi 4 noktada tarayıp ρ'yu hiç taramamak savunulamaz.

**Yapılacak:** ρ ∈ {50, 500, 5000} taraması, öncelikli. Ayrıca ρ→∞ limitinin hard
kısıta yakınsadığını göstermek iyi bir tutarlılık kontrolü olur.

## S1.6 — Tek engel → TAM KABUL, kapsam beyanı olacak

Doğru. İki kısıt satırının kesişimi boş olabilirken her biri tek başına
sağlanabilir — ölçtüğümüz sınır çok-engelli durumda **iyimser.**

**Yapılacak:** kapsam beyanı ilk sayfaya. Mümkünse 2-engelli küçük bir demo ile
iyimserliğin büyüklüğünü göster.

## S1.7 — Aktüatör dinamiği yok → TAM KABUL + bir nüans

Kabul: kutu kısıt (dikdörtgen, ivme sınırsız) gerçek kabiliyeti fazla tahmin
ediyor; v_crit'lerimiz **üst sınır**. Metne yazılacak.

**Nüans (aleyhimize):** İŞ 3'te ölçtük ki gerçek hız komutu bazen **AŞIYOR**
(stick-slip: komut ~0.08 m/s iken gerçek ~0.23 m/s). Yani sapma tek yönlü değil —
kutu ne temiz bir üst sınır ne de alt sınır. "v_crit üst sınırdır" ifadesini bu
nüansla yazmak gerekiyor.

---

# 2. Deney Tasarımı

## S2.1 — N=10 ile 0.5 oranı araması → KISMEN İTİRAZ (veriye dayalı)

En sert eleştiriniz. **Metodolojik sonucu kabul ediyorum** ama **öncül (b) veriye
göre yanlış.**

İddia: "oranlar hep 0/10 ya da 10/10, ara değer neredeyse yok" ve "N=10, bir
koşunun on tekrarı → N≈1".

**Ölçülen ara oranlar (mevcut veriden, sınır civarı hücreler):**

| Kampanya | Hücre | Çarpışma oranı |
|---|---|---|
| İŞ 7 T×α | T=0.5, α=0.3 | **0.75** |
| İŞ 7 T×L | T=0, L=0.10 / 0.30 | **0.72 / 0.78** |
| İŞ 7 T×L | T=0.5, her iki L | **0.50 / 0.50** |
| α–hız analizi | v=0.9 | 0.00 / **0.10** / 0.00 / **0.30** |
| α–hız analizi | v=1.2 | **0.50 / 0.50** / 0.00 / **0.50** |
| α–hız analizi | v=1.5 | **0.60 / 0.50 / 0.90** / 1.00 |
| Izgara boşluğu | y=0.35 | **0.58 / 0.17** |
| duration=30s | REACTIVE / DCBF | **0.62 / 0.33** |

Koşular birbirinin kopyası olsaydı **sadece 0.00 ve 1.00 görülürdü.** 0.75, 0.72,
0.58, 0.33, 0.10 gibi değerlerin varlığı, koşudan koşuya sonucu **çeviren** gerçek
bir değişkenlik olduğunu gösteriyor. Yani N≈1 değil.

**"0.9 mm" rakamı hakkında:** o ölçüm **statik engel + kaçınma manevrası olmayan**
bir tekrarlanabilirlik testinden geliyor. Sınır civarındaki hücrelerde sistem
doğrusal değil — milimetrik farklar çarpışma/çarpışmama şeklinde ayrışıyor. İki
rejimi karıştırmamak gerekiyor.

**Kabul ettiğim kısım (ve önemli):** değişkenliğin kaynağı **kontrolsüz** (Gazebo
determinizm kaçakları), **tasarlanmış** değil. Bu yüzden:
- güven aralığı için meşru bir olasılıksal model yok
- üçüncü ondalık basamak (1.313 gibi) savunulamaz
- öneriniz (başlangıç pozu / faz / gürültü rastgeleleştirmesi) **doğru çözüm**

**Yapılacak:** (a) rastgeleleştirme ekle (başlangıç x/y/θ jitter, engel faz kayması,
engel durumuna gürültü), (b) N≥20, (c) Wilson güven aralığı, (d) o zamana kadar
v_crit'ler **iki** ondalıkla ve "belirsizlik ölçülmedi" notuyla yazılacak.

## S2.2 — Tek başlangıç koşulu → TAM KABUL

Doğru, genelleme iddiamız yok. S2.1'in rastgeleleştirmesi bunu da çözer.

## S2.3 — Teorik olarak en önemli bölge, deneysel olarak çöp → TAM KABUL

En rahatsız edici boşluk bu, katılıyorum.

**Kararım — üçüncü seçenek + kısmi birinci:**

1. **Teorik analiz olarak sun:** S1.1'deki türetme (`e·n⊥ = 0` → ω katsayısı sıfır)
   bunu **kanıt düzeyinde** veriyor. HOCBF'in de aynı yerde çöktüğünü göstermek,
   gözlemi formülasyondan bağımsız kılıyor. Bu, deneyden **daha güçlü** bir sonuç.
2. **Fizik adımını küçültüp sınırlı doğrulama:** Gazebo `max_step_size` düşürülüp
   (örn. 1 ms) y=0 hücrelerinin bir altkümesi tekrarlanır, tünellemenin kaybolup
   kaybolmadığı gösterilir.
3. y=0'ı ana ızgara **istatistiklerinden çıkar**, ayrı bir "dejenere geometri"
   bölümünde ele al.

## S2.4 — Karşılaştırma grubu yok → TAM KABUL, zorunlu

Haklısınız; "garantisi bozulan yöntemin, garantisi olmayandan farkı ne?" sorusunun
şu an cevabı yok.

**Yapılacak:** Nav2/DWB zaten makinede kurulu — en ucuz baseline bu. Aynı
senaryolarda filtresiz DWB koşulup v_crit'i ölçülecek. İkinci tercih: basit bir
VO/ORCA implementasyonu.

## S2.5 — DCBF vs REACTIVE totolojisi → KISMEN KABUL

Kabul: ground-truth v_o ile DCBF'in REACTIVE'i **yenmesi** cebir. Metinde bunu
"beklenen doğrulama" diye sunmalıyız, "bulgu" diye değil.

**İtiraz:** cebirden çıkmayan üç şey var:
1. **Nerede** çöktüğü (v_crit sayısı)
2. **SHIFT (naif öngörü) REACTIVE'den DAHA KÖTÜ** çıktı — cebirden öngörülmezdi;
   "yanlış yapılmış öngörü, hiç öngörü yapmamaktan tehlikeli"
3. **DCBF'in de çöktüğü** nokta — asıl ilgi çeken bölge

---

# 3. Metrikler

## S3.1 — intervention_integral, w değişince karşılaştırılamaz → TAM KABUL

Keskin ve doğru. w_w tablosundaki müdahale karşılaştırmaları geçersiz — maliyet
fonksiyonunun kendisi değişiyor.

**Yapılacak:** w-bağımsız bedel ölçütlerine geç. Elimizde zaten var:
`v_intervention_integral` ve `w_intervention_integral` **ayrı ayrı**, ayrıca
`time_to_goal_s` ve `path_length_m`. w_w tablosunu bunlarla yeniden üret.

## S3.2 — Teoremi hiç doğrudan test etmediniz → TAM KABUL, en değerli öneri

Haklısınız ve bu **elimizdeki en ucuz yüksek-değerli iş.**

```
slack açık koşularda:  δ_max ≈ 0 olan koşuları filtrele
                       -> bu koşularda h_min < 0 oldu mu?

h_min < 0  ->  ayrık-zaman boşluğu ÖLÇÜLMÜŞ olur (tek başına raporlanabilir)
h_min ≥ 0  ->  teorem ampirik olarak doğrulanmış olur
```

Ve doğru öngörüyorsunuz: bu, control_rate taramasının (10/20/50 Hz) neden sonuçsuz
kaldığını da açıklayabilir.

**Durum:** Tailscale kesintisi nedeniyle henüz koşulamadı; bağlantı gelir gelmez
ilk iş bu.

## S3.3 — Titreşim / düzgünlük ölçülmüyor → TAM KABUL

Chattering metriği yok. `∫|u'| dt` ve komut varyansı mevcut bag'lerden **yeni koşu
olmadan** çıkarılabilir.

## S3.4 — margin_violation ile δ örtüşüyor → KABUL, netleştirme borcu

Kavramsal hiyerarşi metinde net kurulmalı:

| Metrik | Ne | Rol |
|---|---|---|
| δ (slack) | Filtrenin **komut ettiği** ihlal | Tasarım kararı (ρ'ya koşullu) |
| h_min | **Gerçekleşen** bariyer değeri | Sonuç (lookahead noktasına göre) |
| body_margin | **Gövde** referanslı ihlal | Sonuç (L'den bağımsız, fiziksel) |
| contact | Fiziksel temas | Sonuç (nihai) |

Slack açıkken `margin_violation` artık "garanti ihlali" değil "tasarım kararının
sonucu" — bu ayrım metinde açık yazılmalı.

---

# 4. Literatür

## S4.1 — "İki sınır" bulgusu gerçekten yeni mi? → KABUL

Haklısınız. "Girdi doygunluğu altında CBF garantisi bozulur" **bilinen** bir şey.

**Katkı yeniden ifade edilmeli:** "bu olur" değil, **"ne zaman, ne kadar, hangi
parametrelere nasıl bağlı olarak"**.

## S4.2 — C3BF sizden önce TB3'te yapıldı → KABUL (zaten iddia etmiyoruz)

C3BF bizde **gelecek çalışma** olarak geçiyor, katkı olarak değil. Eklersek katkı
ancak "C3BF de şu hız oranından sonra çöküyor" şeklinde bir **negatif sonuç**
olabilir.

## S4.3 — Eksik literatür hatları → TAM KABUL, altısı da eklenecek

Özellikle **Trautman & Krause "freezing robot problem"** — bizim `frozen`
gözlemlerimizin literatürdeki adı bu ve hiç atıf yapmamışız. Ciddi eksiklik.

Eklenecekler: HOCBF (Xiao & Belta), input-constrained / feasibility-guaranteed CBF,
CBF-MPC (Zeng/Zhang/Sreenath), freezing robot (Trautman & Krause), safety filter
unified view (Hsu/Hu/Fisac), robust / ISSf-CBF.

## S4.4 — Tek cümlelik iddia hangisi? → Şu an (a). Hedef (c).

Dürüst durum: bugün **(a)**'dayız, katılıyorum.

**(c)'ye geçiş için eksik olan tek şey:** (c) "kestirim belirsizliğine koşulluluk"
diyor; bizde **kestirim belirsizliği hiç yok** (ground truth, EKF bağlı değil).
T=2.0'daki "feasible ama çarpıyor" bulgumuz bir **model uyuşmazlığı** (manevra)
sonucu, kestirim gürültüsü sonucu değil.

**Plan:** (c)'yi hedefle, **belirsizlik eksenini ekleyerek**. Tam EKF gerekmiyor —
engel durumuna kontrollü gürültü/gecikme enjekte etmek yeter
(σ ∈ {0, 0.02, 0.05} m, τ ∈ {0, 100, 200} ms). O zaman iddia:

> "Öngörülü CBF'in avantajı, kestirim belirsizliği ve model uyuşmazlığına
> koşulludur; her iki eksende de **tersine dönme eşiği** vardır (T=2.0'da filtre
> doymaz ama çarpar)."

Bu, elimizdeki T-tersine-dönme bulgusunu merkeze koyup ölçülebilir bir eksenle
tamamlıyor.

---

# 5. Savunma Öncesi Zorunlu Beş Soru — Doğrudan Cevaplar

### 1. v_crit sayılarınızın belirsizliği nedir?

**Şu an ölçülmemiş.** Ara oranların varlığı (0.75, 0.72, 0.58, 0.33...) gerçek bir
koşu-içi değişkenlik olduğunu gösteriyor, ama kaynağı kontrolsüz olduğu için meşru
bir güven aralığı hesaplayamıyoruz. **Plan:** rastgeleleştirme + N≥20 + Wilson CI.
O zamana kadar iki ondalık + "belirsizlik ölçülmedi" notu.

### 2. Neden lookahead, neden HOCBF değil?

**Gerekçe:** unicycle için standart, tek QP'de kalıyor, gerçek-zamanlılığı koruyor.
**Kabul edilen bedel:** gövde garantisi kaybı (+L payı) — lookahead'e özgü.
**İtiraz:** kafa-kafaya dejenerasyon lookahead'e özgü **değil**; türetmeye göre
HOCBF'de de ω katsayısı `e·n⊥ = 0` yüzünden sıfırlanıyor.
**Plan:** HOCBF'i 5. mod olarak ekle ve ölç.

### 3. δ = 0 iken h hiç negatife düştü mü?

**Test edilmedi.** Mevcut veriden çıkar, bağlantı gelir gelmez ilk iş. İki sonuç da
değerli.

### 4. Dış baseline nerede?

**Yok.** Kabul. Nav2/DWB kurulu; aynı senaryolarda filtresiz koşulup v_crit'i
ölçülecek.

### 5. y = 0 bölgesi için planınız ne?

**Üçlü plan:** (i) `e·n⊥ = 0` türetmesiyle **teorik** analiz (HOCBF dahil her
formülasyonun orada çöktüğünü göster), (ii) fizik adımını küçültüp sınırlı deneysel
doğrulama, (iii) ana ızgara istatistiklerinden çıkarıp ayrı bölümde ele al.

---

# 6. Önerilen Öncelik Sırası

| # | İş | Maliyet | Neden bu sırada |
|---|---|---|---|
| 1 | δ=0 → h<0 testi | Analiz, koşu yok | En ucuz, en yüksek değer |
| 2 | Chattering metriği | Analiz, koşu yok | Mevcut bag'lerden |
| 3 | w-bağımsız bedel tablosu | Analiz, koşu yok | S3.1'i kapatır |
| 4 | Rastgeleleştirme + N≥20 | Kod + kampanya | Tüm sayıların güvenilirliği buna bağlı |
| 5 | ρ taraması | 1 kampanya | Feasibility eğrisi buna koşullu |
| 6 | DWB baseline | 1 kampanya | Savunmada zorunlu |
| 7 | v_min tarama ekseni | 1 kampanya | Sınırı yukarı çekebilir |
| 8 | HOCBF modu | Kod + kampanya | D1 borcunu kapatır |
| 9 | Belirsizlik ekseni (σ, τ) | Kod + kampanya | (a) → (c) geçişi için |
| 10 | y=0 teorik analiz + ince fizik adımı | Türetme + kampanya | Teorik boşluğu kapatır |

**1–3 arası yeni koşu gerektirmiyor**, bağlantı gelir gelmez yapılabilir.
