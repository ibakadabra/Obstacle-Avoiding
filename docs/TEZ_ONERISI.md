# Yüksek Lisans Tez Önerisi

**Öğrenci:** İbrahim Akpınar
**Tarih:** Temmuz 2026
**Durum:** Danışman görüşüne sunulan taslak (v1)

---

## 1. Tez Başlığı

**Türkçe:** Girdi-Kısıtlı Diferansiyel Sürüşlü Mobil Robotlarda Reaktif ve Öngörülü Kontrol Bariyer Fonksiyonu Tabanlı Güvenlik Filtrelerinin Uygulanabilirlik (Feasibility) Sınırının Analitik ve Deneysel Karakterizasyonu

**İngilizce:** Analytical and Experimental Characterization of the Feasibility Boundary for Reactive and Predictive Control Barrier Function Safety Filters on Input-Constrained Differential-Drive Mobile Robots

*(Kısa çalışma başlığı: "Güvenlik filtreleri ne zaman yetersiz kalır?")*

---

## 2. Özet

Kontrol Bariyer Fonksiyonu (CBF) tabanlı güvenlik filtreleri, nominal bir hareket planlayıcısının komutunu minimum müdahaleyle güvenli hale getiren, forward invariance garantisi sunan bir çerçevedir. Ancak bu garanti, kontrol girdisinin sınırsız olduğu varsayımına dayanır. Gerçek robotlarda girdi bir kutuyla sınırlıdır (TurtleBot3 Burger için v ≤ 0.22 m/s); engel yeterince hızlı veya yakın olduğunda, kısıtı sağlayan hiçbir girdi kalmaz ve kuadratik programlama (QP) problemi çözümsüz (infeasible) hale gelir. Literatürde bu durum çeşitli çalışmaların "kısıtlar" bölümünde bir dipnot olarak geçmekte, ancak **hangi fiziksel koşullarda ortaya çıktığı nicel olarak karakterize edilmemektedir.**

Bu tez, girdi-kısıtlı nonholonomik bir mobil robotta feasibility'nin çöktüğü sınırı (i) kapalı-form bir analitik ifadeyle öngörmeyi, (ii) bu sınırı (engel/robot hız oranı × sensör menzili × algı-aktüasyon gecikmesi × öngörü ufku) parametre uzayında benzetim ve gerçek donanımla haritalamayı, (iii) reaktif ve öngörülü filtre modları arasındaki geçişin nicel eşiğini belirlemeyi amaçlamaktadır. Ön çalışmada, kafa-kafaya karşılaşma senaryosu için türetilen kapalı-form sınır ifadesi sekiz farklı engel hızında benzetim sonuçlarıyla %0.5'in altında hatayla örtüşmüştür.

**Anahtar kelimeler:** Kontrol bariyer fonksiyonu, güvenlik filtresi, uygulanabilirlik, mobil robot, engel kaçınma, ROS 2

---

## 3. Giriş ve Problem Tanımı

Mobil robotların insanlı ortamlarda çalışması, hareketli engellerle güvenli etkileşimi zorunlu kılar. Yaygın kullanılan yerel planlayıcılar (DWA/DWB, TEB) engelin **anlık** konumuna göre karar verir ve engelin hızını hesaba katmaz. Engel robottan belirgin şekilde hızlıysa — TurtleBot3 Burger için maksimum 0.22 m/s'ye karşılık yürüyen insan yaklaşık 1.4 m/s, yani **~6× hız oranı** — robotun tepki verme kapasitesi geometrik olarak yetersiz kalabilir.

Bu soruna karşı önerilen mimari, nominal planlayıcının çıktısını bir **güvenlik filtresinden** geçirmektir:

```
Nominal planlayıcı (DWB)  →  u_nom  →  [CBF-QP Güvenlik Filtresi]  →  u_safe  →  Robot
                                              ↑
                                    Engel durumu (Lidar → EKF)
```

Filtre şu QP'yi çözer:

```
min   ‖u − u_nom‖²
s.t.  ḣ(x,u) ≥ −α·h(x)                 (güvenlik)
      u ∈ U = [0, v_max] × [−ω_max, ω_max]   (donanım)
```

CBF teorisinin merkezi teoremi, `h`'nin geçerli bir CBF olması için şu koşulu şart koşar:

```
sup_{u ∈ U} [ L_f h(x) + L_g h(x)·u ] ≥ −α(h(x))
```

**Problemin özü:** `U` sınırsız kabul edildiğinde bu koşul her zaman sağlanır ve güvenlik garantisi geçerlidir. Ancak `U` bir kutu olduğunda, belirli durumlarda koşul sağlanamaz — `h` geçerli bir CBF olmaktan çıkar, QP infeasible olur ve teorik garanti hükümsüz kalır. Bu tezin sorusu şudur:

> **Bu çöküş tam olarak nerede başlar, hangi parametrelere nasıl bağlıdır ve öngörü eklemek sınırı ne kadar geriletir?**

---

## 4. Literatür Özeti ve Tezin Özgün Değeri

### 4.1 Var olanlar

| Alan | Temsilci çalışmalar | Durum |
|---|---|---|
| CBF teorisi | Ames vd. (2017, 2019) | Olgun; forward invariance garantisi kanıtlanmış |
| Kaçınılmaz çarpışma durumları | Fraichard & Asama (2004) | Kavram 20 yıllık; ICS tanımı yerleşik |
| Yerel planlayıcılar | Fox vd. (1997, DWA) | Endüstri standardı; formel garanti yok |
| Öngörülü güvenlik filtreleri | Wabersich & Zeilinger | Çerçeve kurulu |
| Dinamik CBF + MPC | arXiv:2209.08539 | "Reaktif yetmez" nitel olarak gösterilmiş |
| CBF + yerel planlayıcı mimarisi | arXiv:2605.15782 (Spot robot) | Mimari olarak en yakın; farklı platform |
| Endüstriyel filtre katmanı | Nav2 Collision Monitor; 3Laws Supervisor | Sezgisel (poligon tabanlı) veya kapalı kaynak |

Görüldüğü üzere hem mimari hem yöntem literatürde mevcuttur. Bu tez **yeni bir filtre önermemektedir.**

### 4.2 Boşluk

Girdi kısıtı altında CBF-QP feasibility'sinin karakterizasyonu açık bir problem olarak işaretlenmektedir (arXiv:2604.04235). İlgili çalışmalarda infeasibility yalnızca bir kısıt olarak anılmakta, örneğin: *"robot bir engele çok yakın başlatıldığında tek zaman adımında kaçacak kontrol yetkisi olmayabilir ve CBF problemi infeasible hale gelir."* Ancak **bu durumun hangi hız oranında, hangi sensör menzilinde, hangi gecikmede ortaya çıktığına dair nicel bir çalışma bulunmamaktadır.**

Benzer şekilde, "öngörü (engel hızı bilgisi) faydalıdır" sonucu nitel olarak bilinmekte; ancak *ne kadar fayda sağladığı*, *hangi eşikte zorunlu hale geldiği* ve *tahmin hatasının faydayı ne zaman baskıladığı* nicelleştirilmemiştir.

### 4.3 Özgün değer

1. Kafa-kafaya karşılaşma için **kapalı-form feasibility sınırı** türetimi ve doğrulaması.
2. (hız oranı × menzil × gecikme × öngörü ufku) uzayında **deneysel sınır haritası**.
3. Reaktif → öngörülü geçişin **nicel eşiği** ve optimal öngörü ufku `T*`'ın karakterizasyonu.
4. Çöküşün **kestirim-kaynaklı** mı **aktüasyon-kaynaklı** mı olduğunu ayrıştıran ablasyon.
5. Türetilen sınırın çevrimiçi kullanımı: **sınır-farkındalıklı uyarlanabilir mod geçişi**.

---

## 5. Amaç ve Araştırma Soruları

**Genel amaç:** Girdi-kısıtlı nonholonomik bir mobil robotta CBF tabanlı güvenlik filtresinin çalışma zarfını analitik ve deneysel olarak belirlemek.

- **AS1:** Kafa-kafaya karşılaşmada infeasibility'nin başladığı kritik mesafe, sistem parametrelerinin (engel hızı, sınıf-K katsayısı α, emniyet mesafesi, gecikme) kapalı-form bir fonksiyonu olarak ifade edilebilir mi? Bu ifade benzetim ve donanımla doğrulanır mı?
- **AS2:** Reaktif mod (engel hızı ihmal), dinamik CBF (engel hızı ḣ'ye dahil) ve ufuk-kaydırmalı öngörülü mod arasında feasibility sınırı nasıl kayar? Reaktif modun yetersiz kaldığı eşik hız oranı nedir?
- **AS3:** Öngörü ufku `T` arttıkça güvenlik payı hangi noktaya kadar artar, tahmin hatası hangi noktadan sonra baskın hale gelir? Optimal `T*` kapanma hızına nasıl bağlıdır?
- **AS4:** Gözlenen başarısızlıkların ne kadarı durum kestiriminden (EKF), ne kadarı aktüasyon sınırından kaynaklanır?
- **AS5:** Türetilen sınır çevrimiçi hesaplanarak, robot feasibility sınırına yaklaştığında mod geçişi yapabilir mi? Bu, çarpışma oranını düşürür mü?

---

## 6. Yöntem

### 6.1 Sistem modeli

Robot: unicycle kinematiği, durum `x_r = [p_x, p_y, θ]`, girdi `u = [v, ω]`, kısıt `v ∈ [0, 0.22]`, `|ω| ≤ 2.84` (TurtleBot3 Burger).
Engel: sabit hız modeli, durum `x_o = [o_x, o_y, v_x, v_y]`.

### 6.2 Güvenlik filtresi

Bağıl derece sorunu nedeniyle (merkeze yazılan `h`'de `ω` görünmez) `h`, robot merkezinin `l` kadar önündeki lookahead noktasına yazılır:

```
h = ‖p_l − p_o‖² − d_safe²,    ṗ_l = G(θ)·u
```

Üç mod, yalnızca `ḣ`'nin kurulumunda farklılaşır:
- **REACTIVE:** `∂h/∂t = 0` (engel statik varsayımı)
- **DCBF:** `ḣ`'ye engel hız terimi (`−2Δpᵀv_o`) eklenir
- **SHIFT:** engel konumu `T` saniye ileri kaydırılır (`p_o + v_o·T`)

### 6.3 Kestirim

Lidar kümeleme çıktısından engelin konum ve hızı, sabit-hız modelli Kalman filtresiyle kestirilir. Filtre tutarlılığı, yenilik (innovation) istatistiği ile denetlenir.

### 6.4 Deney tasarımı

**Senaryolar:** (i) kafa-kafaya, (ii) dik kesişme — literatürdeki standart yerel planlayıcı test senaryolarıyla uyumlu.

**Bağımsız değişkenler:**

| Değişken | Değerler |
|---|---|
| Engel hızı | 0.22, 0.44, 0.88, 1.32 m/s (1×–6×) |
| Filtre modu | REACTIVE, DCBF, SHIFT (T = 0.5, 1.0, 2.0 s) |
| Gecikme τ | 0–400 ms (enjeksiyon düğümüyle) |
| Nominal kaynak | DWB, (imkân dahilinde) MPPI |
| Karşılaştırma | Filtresiz, Nav2 Collision Monitor, önerilen filtre |

Her hücre için N = 20 tekrar.

**Bağımlı değişkenler (metrikler):** çarpışma oranı, QP infeasibility oranı ve ilk infeasibility anı, minimum engel mesafesi, hedefe ulaşma başarısı/süresi, müdahale büyüklüğü ‖u_safe − u_nom‖ (integral ve tepe).

Bu üç olayın (infeasibility, çarpışma, mesafe ihlali) **ayrı** raporlanması esastır; ön bulgularda reaktif modun infeasibility bildirmeden çarpıştığı ("sessiz çöküş") gözlenmiştir.

**Ablasyon:** Filtre bir kolda engelin gerçek (ground-truth) durumuyla, diğer kolda EKF kestirimiyle beslenir; böylece kestirim-kaynaklı ve aktüasyon-kaynaklı başarısızlıklar ayrıştırılır.

### 6.5 Ortam ve doğrulama

- **Benzetim:** ROS 2 Humble + Gazebo Classic 11 + Nav2; tüm hız oranları.
- **Donanım:** TurtleBot3 Burger; yer gerçeği için tavan kamerası + ArUco işaretçiler; hareketli engel düzeneği (RC araç veya ray üzerinde çekilen platform). Donanımda düşük–orta hız oranları doğrulanır, yüksek oranlar doğrulanmış model üzerinden ekstrapole edilir.

---

## 7. Ön Bulgular

Öneri aşamasında aşağıdaki çalışmalar tamamlanmıştır.

**(a) Analitik sınır türetildi ve doğrulandı.** Kafa-kafaya senaryoda, tam frenlemenin dahi kısıtı sağlayamadığı kritik mesafe:

```
d* = v_o/α + √( (v_o/α)² + d_safe² )
```

Sekiz farklı engel hızında (0.11–1.32 m/s), benzetimde ölçülen ilk infeasibility mesafesi ile bu ifade **%0.5'in altında** hatayla örtüşmüştür. Hiçbir serbest parametre uydurulmamıştır (eğri uydurma yapılmamıştır).

**(b) Optimal öngörü ufku gözlendi.** SHIFT modunda `T` süpürüldüğünde minimum engel mesafesi ters-V karakteri göstermiş; `T` küçükken öngörü yetersiz, büyükken sabit-hız tahmininin hatası baskın hale gelmiştir. Tepe noktası (`T*`) kapanma hızıyla kaymaktadır.

**(c) Sessiz çöküş gösterildi.** Dik kesişme senaryosunda reaktif mod, infeasibility oranı 0.000 iken çarpışmıştır; aynı koşulda dinamik CBF çarpışmayı önlemiştir. Bu, infeasibility'nin tek başına güvenlik göstergesi olmadığını doğrulamaktadır.

**(d) Kestirim ablasyonu yapıldı.** Gerçek durum bilgisi ile EKF kestirimi karşılaştırıldığında, test edilen hız aralığında filtre performansı pratik olarak bozulmamıştır (yenilik tutarlılık testi: ortalama NIS ≈ 1.95, beklenen ≈ 2.0).

**(e) ROS 2 uygulaması çalışmaktadır.** Güvenlik filtresi bir ROS 2 düğümü olarak gerçeklenmiş; Gazebo ortamında gerçek TurtleBot3 modeli ve hareketli engelle uçtan uca doğrulanmıştır. Ayrıca lookahead formülasyonunun tam simetrik kafa-kafaya durumda dönüş serbestliğini kaybettiği (kısıtta `ω` katsayısının sıfırlandığı) deneysel olarak gözlenmiştir; bu, collision-cone formülasyonunun gelecek çalışma olarak değerlendirilmesini motive etmektedir.

---

## 8. İş-Zaman Çizelgesi

| Aşama | İş | Süre |
|---|---|---|
| **Faz 0** ✔ | numpy benzetimi, analitik türetme, ön doğrulama | tamamlandı |
| **Faz 1** | ROS 2/Gazebo hattı: filtre düğümü, hareketli engel, EKF düğümü, gecikme enjeksiyonu, DWB entegrasyonu | 3 hafta |
| **Faz 2** | Toplu deney kampanyası, sınır haritası v1, ablasyon, τ süpürmesi | 3 hafta |
| **Faz 3** | Donanım doğrulaması: TB3 bring-up, ArUco yer gerçeği, engel düzeneği, düşük–orta hız oranları | 4 hafta |
| **Faz 4** | Bildiri ve tez yazımı | 3 hafta |

Donanım tedariki gecikirse Faz 3 yerine MPPI karşılaştırması ve çoklu engel genişletmesi yapılır; donanım doğrulaması sonraki döneme aktarılır ve bildiri benzetim sonuçlarıyla çıkarılır.

---

## 9. Beklenen Çıktılar

1. **Bilimsel:** Feasibility sınırının analitik ifadesi ve deneysel haritası; ulusal/uluslararası bir konferans bildirisi (TOK / IFAC MED / ECC) ve devamında dergi makalesi (IEEE Access, Mechatronics, JIRS).
2. **Teknik:** Açık kaynak ROS 2 paketi (güvenlik filtresi + engel kestirimi + deney altyapısı), tekrarlanabilir deney protokolü.
3. **Uygulamaya dönük:** Verilen bir robot–ortam çifti için "bu güvenlik filtresi hangi engel hızına kadar yeterlidir" sorusuna sayısal cevap veren tasarım aracı.

---

## 10. Kaynakça (seçilmiş)

1. A. D. Ames, X. Xu, J. W. Grizzle, P. Tabuada, "Control Barrier Function Based Quadratic Programs for Safety Critical Systems," *IEEE TAC*, 2017.
2. A. D. Ames vd., "Control Barrier Functions: Theory and Applications," *ECC*, 2019.
3. T. Fraichard, H. Asama, "Inevitable Collision States — A Step Towards Safer Robots?," *Advanced Robotics*, 2004.
4. D. Fox, W. Burgard, S. Thrun, "The Dynamic Window Approach to Collision Avoidance," *IEEE RAM*, 1997.
5. K. P. Wabersich, M. N. Zeilinger, "Predictive Safety Filter" çalışmaları.
6. J. Zeng, B. Zhang, K. Sreenath, "Safety-Critical Model Predictive Control with Discrete-Time Control Barrier Function," *ACC*, 2021.
7. "Dynamic Control Barrier Function-based Model Predictive Control to Safety-Critical Obstacle-Avoidance of Mobile Robot," arXiv:2209.08539.
8. "Structure, Feasibility, and Explicit Safety Filters for Linear Systems," arXiv:2604.04235.
9. "Reactive Robot-Centric Safety for Autonomous Navigation in Constrained and Dynamic Environments," arXiv:2605.15782.
10. S. Macenski vd., "The Marathon 2: A Navigation System" (Nav2), *IROS*, 2020.
11. Nav2 Collision Monitor dokümantasyonu, docs.nav2.org.

---

*Bu belge danışman görüşüne sunulan taslaktır; enstitü resmi tez öneri formu, danışman onayından sonra bu içerikten türetilecektir.*
