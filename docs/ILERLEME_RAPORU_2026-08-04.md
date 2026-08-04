# İlerleme Raporu — Deney Koşucusu Altyapısı ve İlk Tanılama Kampanyaları

**Tarih:** 4 Ağustos 2026
**Kapsam:** Bir önceki raporun (WhatsApp üzerinden, "reaktif filtre Gazebo'da simüle ediliyor" özeti) ardından yapılan çalışmalar.

## 1. Bağlam ve motivasyon

Önceki raporda bildirilen manuel test yöntemi (iki ayrı terminalden `ros2 topic pub` ile robot ve engelin elle tetiklenmesi) sürdürülemez hale gelmişti: iki komut arasındaki SSH gecikmesi saniyelerden dakikalara kadar değişiyordu, bu da robot ile engelin senaryo başlangıcında senkron olmasını garanti etmiyordu. Planlanan ~600+ koşuluk deney kampanyası için bu yöntem kullanılamaz olduğundan, uçtan uca otomatik bir **Deney Koşucusu** altyapısı tasarlanıp inşa edildi.

## 2. Deney Koşucusu — 6 bileşen

Belirlenen öncelik sırasıyla (atlanmadan) tamamlandı:

| # | Bileşen | İşlev |
|---|---|---|
| 1 | `scenario_node` | Robot ve engel komutlarını AYNI timer callback'inden yayınlayarak gerçek t0 senkronu sağlar |
| 2 | Teşhis topic'leri | Filtre node'u artık `h_value`, `qp_status`, `qp_solve_time_ms`, `cmd_vel_nominal`'i canlı yayınlıyor |
| 3 | rosbag2 kaydı | Her koşu otomatik kaydediliyor, tmux ile SSH bağlantısından bağımsız çalışıyor |
| 4 | `metrics_extractor` | Bag klasörlerini tarayıp tek bir `metrics.csv`'ye indirger (idempotent, tekrar çalıştırılabilir) |
| 5 | Durum sıfırlama | Her koşu öncesi dünya + filtre iç durumu temiz duruma döner |
| 6 | `sweep_runner` | Tek bir YAML'dan tam parametre matrisi (kartezyen çarpım × tekrar sayısı) koşturur, yarıda kesilirse devam ettirilebilir |

Sonuç: `ros2 run cbf_filter_pkg sweep_runner <config.yaml>` tek komutuyla, insan müdahalesi olmadan onlarca koşuluk bir kampanya çalışıp CSV üretebiliyor.

## 3. Karşılaşılan ve çözülen kritik hatalar

Bu altyapıyı kurarken üç gerçek, tekrarlanabilir hata teşhis edilip düzeltildi:

**a) `scenario_node` süreç sonlanma hatası.** Koşu bittiğini gösteren log mesajları ("SENARYO BITTI") yazdırılmasına rağmen süreç saatlerce hayalet (zombie) olarak kalıyordu. Kök neden: `rclpy.shutdown()`'ın, `spin_once()`'un çalıştırdığı bir timer callback'inin **içinden** çağrılması executor'ın kendi kendini beklemesine (deadlock) yol açıyor. Üç yanlış teşhisten sonra (`spin`/`spin_once` farkı, `os._exit`, `destroy_node` kaldırma) debug print'leriyle kesinleştirildi. Düzeltme: callback yalnızca bir bayrak set ediyor, gerçek `shutdown()` çağrısı ana döngüde (callback'in dışında) yapılıyor.

**b) Koşular arası kirlenme.** İlk metrics.csv çıktısı, ardışık koşularda `d_min` değerinin 0.36 m'den 16.5 m'ye **monoton arttığını** gösterdi — robot koşular arası hiç sıfırlanmadığı için her koşu bir öncekinin bittiği yerden başlıyor, engelden gitgide uzaklaşıyordu. İlk çözüm denemesi (her koşuda Gazebo'yu tamamen öldürüp yeniden başlatmak) hem pahalı (~10-30 sn/koşu) hem de tehlikeli çıktı: `pkill -f turtlebot3_gazebo` komutu tmux sunucusunun kendi komut satırıyla eşleşip **tüm düzeneği** (Gazebo + filtre node'u + çalışan senaryo) tek seferde öldürdü. Bunun yerine önceden fark edilmemiş `/reset_world` servisi bulunup kullanıldı: 0.37 saniyede, ~0.05 mm hassasiyetle sıfırlama sağlıyor. İki ardışık koşuda ölçülen d_min farkı 0.9 mm'ye indi.

**c) YAML parametrelerinin filtreyi gerçekte etkilememesi.** Senaryo YAML'larındaki `filter:` bloğu (mode, alpha, d_safe) yalnızca metrik kaydı için metadata olarak kullanılıyordu; filtre node'unda mod `Mode.REACTIVE` ve α=1.0 koda gömülüydü. Standart ROS 2 `set_parameters` servisi üzerinden gerçek bağlantı kuruldu; tek bir DCBF test koşusuyla parametrenin fiilen uygulandığı doğrulandı.

## 4. Üç tanılama kampanyası ve bulgular

Altyapı tamamlandıktan sonra, önceki raporda bahsedilen "engel yakınında hafif marj ihlali" bulgusunun kaynağını ayrıştırmak için üç kampanya koşuldu (her biri N=10 tekrar, 0 hata):

**Kampanya 1 — Kontrol hızı taraması (ZOH hipotezi):** 10/20/50 Hz'de α=1.0 sabit tutularak koşuldu.

| rate | h_min ort ± std | marj ihlali |
|---|---|---|
| 10 Hz | −0.0285 ± 0.0008 | 10/10 |
| 20 Hz | −0.0284 ± 0.0011 | 10/10 |
| 50 Hz | −0.0290 ± 0.0003 | 10/10 |

5 kat hız artışı ihlal derinliğini değiştirmedi → **ayrıklaştırma/ZOH artefaktı hipotezi elendi.**

**Kampanya 2 — Mod taraması, hareketli engel (0.3 m/s):**

| mode | h_min ort ± std | marj ihlali |
|---|---|---|
| REACTIVE | −0.0292 ± 0.0006 | 10/10 |
| **DCBF** | **+0.2495 ± 0.0239** | **0/10** |
| SHIFT | −0.0280 ± 0.0013 | 10/10 |

DCBF ihlali 10 koşunun tamamında ortadan kaldırdı. SHIFT, REACTIVE'den istatistiksel olarak ayırt edilemedi.

**Kampanya 3 — Mod taraması, statik engel (kontrol grubu, v=0):**

| mode | h_min ort ± std |
|---|---|
| REACTIVE | −0.0015 ± 0.00027 |
| DCBF | −0.0014 ± 0.00018 |
| SHIFT | −0.0015 ± 0.00024 |

Engel duruyorken üç mod istatistiksel olarak özdeş — beklenen sonuç, çünkü DCBF'nin `−2Δp·v_o` terimi ve SHIFT'in `p_o+v_o·T` kayması, `v_o=0` olduğunda REACTIVE'e indirgeniyor.

## 5. Sonuç

Kanıt zinciri kapandı: sorun ayrıklaştırma değil, REACTIVE modun engel hızını (`v_o`) kısıta hiç katmamasıydı. SHIFT bunu **konum tahmini** ile telafi etmeye çalışıyor ama kısıtın kendisine hız terimi eklemediği için işe yaramıyor; DCBF ise doğrudan hız terimini kısıta koyduğu için tam çözüm sağlıyor. Statik-engel kontrol testi, bu farkın mod seçiminden değil gerçekten engel hızından geldiğini doğruluyor.

**Sıradaki adımlar (öneri, onay bekliyor):** (a) bu bulguların tez metnine ve figürlere işlenmesi, (b) DCBF modu sabitken bir α taraması, (c) `d_safe`'in de YAML'dan gerçek parametre olarak bağlanması (şu an hâlâ koddaki sabitlerden hesaplanıyor).
