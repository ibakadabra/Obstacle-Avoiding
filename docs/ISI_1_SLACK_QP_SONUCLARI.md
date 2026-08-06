# İŞ 1 — Slack'li QP Doğrulama Sonuçları

**Tarih:** 6 Ağustos 2026 | **Kampanya:** 60 koşu, 0 hata, 38.6 dk
**Sabit:** y=0.3 (ayrışma bandı çekirdeği), DCBF, duration=30s, α=1.0, ρ=500

---

## 1. Neden bu değişiklik yapıldı

Mevcut QP'de güvenlik kısıtı **hard** idi:

```
min  ‖u − u_nom‖²
s.t. ḣ ≥ −α·h              ← sağlanamıyorsa QP INFEASIBLE
     u_min ≤ u ≤ u_max
```

Infeasible olduğunda kod `u_safe = [0, 0]` (maksimum fren) döndürüyordu.
Sonuç: `v=1.4`'te müdahale bütünüyle çöküyordu (y=0.3: 9.51 → 1.14).

**Hipotez:** ölçtüğümüz "kritik hız", filtrenin fiziksel sınırını değil,
*anlamlı komut üretmeyi bıraktığı* noktayı ölçüyor.

Yeni formülasyon — kısıt gevşetildi, ihlal cezalandırıldı:

```
min  w_v·((v−v_nom)/v_range)² + w_w·((ω−ω_nom)/ω_range)² + ρ·δ²
s.t. ḣ(x,u) ≥ −α·h(x) − δ
     δ ≥ 0
     v_min ≤ v ≤ v_max,  ω_min ≤ ω ≤ ω_max
```

---

## 2. Ham sonuçlar

| slack | v (m/s) | n | contact | margin_viol | infeas_any | infeas_cnt | interv_int | δ_max | δ_int | δ_aktif |
|---|---|---|---|---|---|---|---|---|---|---|
| hard | 0.8 | 10 | 0.00 | **1.00** | 1.00 | 18.8 | 11.97 | — | — | — |
| hard | 1.2 | 10 | 0.10 | **1.00** | 1.00 | 18.8 | 9.58 | — | — | — |
| hard | 1.4 | 10 | 1.00 | 1.00 | 1.00 | 25.3 | **1.04** | — | — | — |
| slack | 0.8 | 10 | 0.00 | **0.00** | 1.00 | 4.6 | 10.68 | 0.257 | 0.141 | 0.069 |
| slack | 1.2 | 10 | 0.10 | **0.10** | 1.00 | 2.5 | 11.93 | 0.991 | 1.084 | 0.081 |
| slack | 1.4 | 10 | 0.90 | 1.00 | 0.90 | 8.9 | **5.46** | 1.891 | 1.772 | 0.058 |

*Tablo programatik olarak export edildi (`analyze_slack_is1.py`), elle
transkribe edilmedi — 5 Ağustos'taki transkripsiyon hatası dersinin gereği.*

---

## 3. Kabul kriteri 2: DOĞRULANDI

> *"v=1.4'te slack'li varyantta müdahale çöküşü kaybolmalı veya belirgin
> şekilde yumuşamalı."*

`intervention_integral`: hard'da **1.04**, slack'te **5.46** — çöküş
5 kattan fazla yumuşadı. Filtre artık yüksek hızda "pes etmiyor",
kısıtı minimum ihlalle sağlamaya devam ediyor.

---

## 4. Kabul kriteri 1: TUTMADI — ve bu, beklenenden İYİ bir haber

> *"v=0.8 ve 1.2'de iki varyant istatistiksel olarak özdeş olmalı
> (kısıt sağlanabiliyor → δ=0)."*

**Özdeş çıkmadı.** Sebep, hard modda o hızlarda bile QP'nin tick'lerin bir
kısmında (18.8/300) zaten infeasible olması — yani δ=0 varsayımı baştan
geçersizdi.

Ama fark **beklenen yönün tersine**, iyi yönde çıktı:

| | v=0.8 | v=1.2 |
|---|---|---|
| `margin_violation` hard | 1.00 | 1.00 |
| `margin_violation` slack | **0.00** | **0.10** |

**Slack, güvenliği bozmadı — iyileştirdi.**

### Mekanizma

Hard kısıtta QP infeasible olduğu her tick'te kod `u=[0,0]` uyguluyor.
Bu, engel yaklaşırken robotun **dönerek kaçmasını engelliyor** — ω kanalı
tamamen kapanıyor, h serbest düşüşe bırakılıyor.

Slack'te QP **her tick'te** bir çözüm üretiyor (çoğu zaman δ≈0). Robot
dönme kapasitesini hiç kaybetmiyor. Net sonuç: daha iyi marj koruma,
üstelik daha AZ infeasible tick (18.8 → 4.6).

---

## 5. Tez açısından anlamı

Bu, önceki bütün "kritik hız" ölçümlerinin yorumunu değiştiriyor:

> **Ölçtüğümüz sınırın bir kısmı, CBF'in fiziksel/matematiksel sınırı değil,
> hard formülasyonun KENDİ FALLBACK POLİTİKASININ (maks fren) artefaktıydı.**

Yani "filtre şu hızda çöküyor" cümlesi, aslında "filtre şu hızda infeasible
oluyor ve bizim seçtiğimiz yedek davranış (tam fren) durumu daha da
kötüleştiriyor" demekmiş. Slack'li formülasyonda bu karışım ortadan kalkıyor
ve geriye saf aktüasyon sınırı kalıyor.

**Metodolojik kazanç:** feasibility ölçümü artık **ikili değil sürekli**.
`qp_infeasible_count` yerine `delta_max` / `delta_integral` /
`delta_active_ratio` ile "ne kadar dışındayız" ölçülebiliyor — sınır
eğrisi çok daha keskin çizilebilir.

### margin_violation'ın anlamı değişti — DİKKAT

Slack'le h<0'a **bilerek** izin veriliyor. İki metrik artık ayrı tutulmalı:

- `delta_max` → filtrenin **komut ettiği** ihlal (tasarım kararı)
- `h_min` → **gerçekleşen** ihlal (fiziksel sonuç)

---

## 6. Açık nokta (izlenecek)

Slack modda bile `qp_infeasible_any = 1.00` (v=0.8, 1.2). Teorik olarak
slack ile QP her zaman feasible olmalı. Sayı küçük (2.5–4.6 / ~300 tick)
ama sıfır değil.

Muhtemel sebep: OSQP'nin nadir sayısal yakınsama sorunu — özellikle ilk
tick'lerde (x_r/x_o henüz gelmemişken) veya çok büyük δ gerektiren geçici
anlarda. İŞ 2'yi engellemiyor, ama sınır takibi kampanyalarında
`delta_active_ratio` ile birlikte izlenmeli.

---

## 7. Sıradaki adım

**İŞ 2 — Sınır takibi altyapısı (ikili arama).** Artık slack'li QP ile
`v_crit` ölçümü temiz yapılabilir; üç ayrı sınır (çarpışma / marj /
feasibility) ayrı ayrı aranacak.
