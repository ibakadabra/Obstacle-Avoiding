# TurtleBot3 CBF Güvenlik Filtresi — Proje Planı (1 dönem, ~16 hafta)

**Tez:** Diferansiyel sürüşlü mobil robotta reaktif ve öngörülü güvenlik filtreleri —
feasibility sınırının analizi ve deneysel doğrulaması
**Çıktılar:** sınır haritası + analitik sınır + (mümkünse) donanım doğrulaması → bildiri; tez metni bunun üstüne yazılır.
**Plan tarihi:** Temmuz 2026 · Ortam: Ubuntu 22.04 + ROS 2 Humble + Gazebo Classic 11

## Sabit kararlar

- Baseline: Nav2 **DWB** (+ vakit kalırsa MPPI). TEB elendi (ROS 2 portu bakımsız).
- Filtre modları: (i) reaktif (∂h/∂t=0), (ii) D-CBF (ṗ_o terimi ḣ'de), (iii) ufuk-kaydırmalı (T).
- QP: prototipte cvxpy, döngüde OSQP doğrudan. Infeasible → maks fren + logla.
- Engel EKF custom yazılacak (robot_localization engel takamaz).
- İş bölümü: çekirdek kodu İbrahim yazar; Claude spek, kod incelemesi, deney altyapısı, dokümantasyon.

## Takvim

| Hafta | İş | Çıktı / kapı |
|---|---|---|
| **1–2** | **Faz 0:** numpy unicycle sim (iskelet hazır: `sim/`) + 1D kapalı-form sınır türetmesi. D1 kararı (lookahead vs C3BF) burada verilir | Sayısal sınır ↔ analitik eğri figürü |
| **3–5** | **Faz 1:** TB3 Gazebo Classic + Nav2 DWB bringup; CBF filtre node'u (cmd_vel remap); hareketli engel; gecikme enjeksiyonu | Uçtan uca tek senaryo çalışıyor |
| **6** | Engel EKF node'u (lidar kümeleme + sabit-hız EKF) | EKF vs ground truth karşılaştırması |
| **7–9** | **Faz 2:** batch koşucu + tam süpürme (4 hız × modlar × N=20) + ablasyon (mükemmel durum vs EKF) + τ süpürmesi | Sınır haritası v1 |
| **10–13** | **Faz 3 (donanım gelirse):** TB3 bring-up, τ ölçümü, tavan kamerası + ArUco, engel düzeneği (RC araba/ray), oran 1×–2× doğrulama | Donanım noktaları haritada |
| **14–16** | Yazım: bildiri/tez bölümleri (metot + bulgular) | Taslak teslim |

**Donanım gecikirse:** Hafta 10–13 → MPPI baseline + çoklu engel genişletmesi; donanım doğrulaması ayrı döneme kayar, bildiri benzetimle çıkar.

## Metrikler

Çarpışma oranı · QP infeasibility oranı ve ilk anı · d_min · hedefe ulaşma süresi/başarı · ‖u_safe−u_nom‖ (integral+tepe). Bunlar üç ayrı olay: infeasibility ≠ çarpışma ≠ mesafe ihlali.

## Riskler (kısaltılmış)

- Gazebo Classic hareketli aktör kısıtı → hız-kontrollü model'e düş (hafta 3'te doğrula).
- 5 Hz lidar'da EKF ilişkilendirme → prediction step ara doldurma; ablasyon zaten ayrıştırıyor.
- TB3 tedariki → hafta 8'de durum kontrolü; yoksa yedek plana geç.
- Hakem "artımsal" derse → katkı cümlesi: girdi-kısıtlı CBF-QP feasibility karakterizasyonu + analitik sınır + ablasyon.
