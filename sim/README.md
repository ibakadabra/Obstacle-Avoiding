# Faz 0 — numpy Unicycle + CBF-QP Simülasyonu

ROS'suz, saf Python. Amaç: 3 filtre modunu ve analitik sınırı ucuz ortamda doğrulamak.

## Dosyalar ve sahiplik

| Dosya | İçerik | Sahibi |
|---|---|---|
| `params.py` | Robot/sim/senaryo parametreleri (TB3 Burger değerleri) | Claude ✅ hazır |
| `dynamics.py` | Unicycle ve engel adım fonksiyonları | **İbrahim — Görev 1a** |
| `cbf.py` | h fonksiyonu + 3 modlu QP güvenlik filtresi | **İbrahim — Görev 1b** |
| `scenario.py` | Yol-kesme senaryosu üreteci + sim döngüsü | Claude ✅ hazır |
| `metrics.py` | Koşu metrikleri (d_min, çarpışma, infeasibility, süre) | **İbrahim — Görev 2** |
| `run_boundary_map.py` | (hız oranı × T × mod) süpürmesi → CSV + ısı haritası | Claude ✅ hazır (stub'lar dolunca çalışır) |
| `tests/test_faz0.py` | Kabul testleri — hepsi geçince Görev 1 tamam | Claude ✅ hazır |

## Çalıştırma

```bash
cd tez_cbf/sim
python -m pytest tests/ -v        # Görev 1-2 kabul kriteri
python run_boundary_map.py        # sınır haritası (tüm testler geçince)
```

## Görev sırası

1. **Görev 1a** — `dynamics.py`: `unicycle_step` (Euler yeterli, dt=0.02) ve `obstacle_step`.
2. **Görev 1b** — `cbf.py`: önce `REACTIVE` mod (lookahead noktası formülasyonuyla), testleri geçir.
   Sonra `DCBF` ve `SHIFT` modları. cvxpy ile başla; OSQP'ye geçiş Faz 1'de.
3. **Görev 2** — `metrics.py`: docstring'lerdeki tanımlara göre.
4. Paralel (kağıt üstü): 1D kafa-kafaya kapalı-form sınır türetmesi — şablon: `../docs/1d_tureme_sablonu.md`

## D1 kararı (hafta 2)

`cbf.py`'de lookahead formülasyonu çalışınca aynı arayüzle collision-cone (C3BF) varyantını
ekleyeceğiz; `run_boundary_map.py` ikisini aynı senaryolarda koşturup karar verdirecek.
