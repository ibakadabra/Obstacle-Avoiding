# SINIR TAKİBİ — ANALİZ DÜZELTMELERİ (YENİ KOŞU GEREKTİRMEZ)

İŞ 3/4/5 sınır takibi 750 koşu ile tamamlandı. Veri duruyor, ama **analiz
katmanında üç yapısal sorun var**. Üçü de mevcut bag/CSV'lerden düzeltilebilir.

**Bu üçü kapanmadan İŞ 6 (T taraması, 720 koşu) başlatılmamalı** — aksi halde
yorumlanamayacak bir gürültü seviyesiyle koşulmuş olur.

---

## DÜZELTME 1 — ÜÇ METRİK TEK KOŞU HAVUZUNDAN ÇIKARILMALI

### Tespit: mantıksal olarak imkânsız bir sonuç var

Tanımlar:
```
contact:            ‖p_merkez − p_o‖ < contact_distance = 0.3737
margin_violation:   h < 0  ⟺  ‖p_eff − p_o‖ < d_safe = 0.5237
                    p_eff = p_merkez + L·[cos θ, sin θ]
```

Üçgen eşitsizliği:
```
‖p_eff − p_o‖ ≤ ‖p_merkez − p_o‖ + L
```

L = 0.10 iken:
```
contact varsa:  ‖p_eff − p_o‖ < 0.3737 + 0.10 = 0.4737 < 0.5237
                → margin_violation ZORUNLU
```

Yani **L ≤ 0.15 iken `margin_rate ≥ contact_rate` her hızda**, dolayısıyla
`v_crit(marj) ≤ v_crit(çarpışma)` her zaman.

Sonuç tablosunda ihlal:
```
α = 0.3  (L = 0.10):   çarpışma 1.100,  marj 1.125     ← marj DAHA YÜKSEK
```

Bu yapısal olarak imkânsız. Büyüklüğü (0.025) gürültü seviyesinde ama
**imkânsız bir olayın gürültüyle açıklanması yeterli değil** — anlamı, iki
metriğin aynı koşulardan hesaplanmadığı.

### Kök neden
Her sınır araması (`contact_rate`, `margin_violation_rate`, `delta_active_rate`)
kendi koşu setini üretiyor. Üç sınır bağımsız örneklemlerden geliyor.

### Düzeltme
```
Tek sınır araması → tek koşu havuzu → üç metrik post-hoc hesaplanır
```

`boundary_search.py` yeniden yapılandırılmalı:
1. Arama, **birincil metrik** (`contact_rate`) üzerinden yürür
2. Her hız noktasında koşulan tüm koşulardan **üç metrik birden** çıkarılır
3. `v_crit(marj)` ve `v_crit(feasibility)`, aynı hız-oran tablosundan
   interpolasyonla türetilir — yeni koşu yok

Yan fayda: koşu sayısı üçte bire iner.

### Doğrulama kontrolü (pipeline'a eklenecek)
```python
if lookahead_L <= (d_safe - contact_distance):
    assert v_crit_margin <= v_crit_contact + tolerance, \
        "Yapısal ihlal: marj sınırı çarpışma sınırından yüksek"
```
`tolerance` gürültü tabanı kadar (bkz. Düzeltme 4 notu). İhlal çıkarsa hata versin.

### Ayrıca kontrol edilecek: gap = 0.000 iki kez
`w_w=0.25` ve `w_w=0.5` satırlarında çarpışma − marj boşluğu **tam olarak
0.000**. Oysa 5.4-B'de y=0.3, v=0.8'de DCBF `contact=0, margin_violation=10`
çıkmıştı — yani "ihlal var ama temas yok" bandı ulaşılabilir.

d_safe (0.5237) ile temas (0.3737) arasında 0.15 m'lik bir band var; bu banda
hiç koşu düşmemesi iki kez üst üste şüpheli. Ham koşu verisinden doğrula:
gerçekten hiçbir koşu bu bantta mı, yoksa raporlama artefaktı mı?

---

## DÜZELTME 2 — `delta_active` EŞİĞİ TANIMSIZ

### Tespit
11 hücrenin 9'unda `delta_active_rate` = ALL_ABOVE. Yani feasibility sınırı
kaba taramanın en düşük noktasının (v=0.6) bile altında.

**Bu bir aralık sorunu değil, tanım sorunu.** δ > 0 sayılıyorsa sayısal artık
neredeyse her kontrol adımında pozitiftir ve oran her zaman 1 çıkar. Arama
aralığını 0.3'e çekmek bunu çözmez — 0.3'te de ALL_ABOVE çıkar.

### Düzeltme: δ'yı kısıt ölçeğine normalize et
```python
# δ tek başına anlamsız — kısıtın büyüklüğüne göre değerlendirilmeli
delta_rel = delta / max(abs(alpha * h), eps)

delta_active = delta_rel > delta_threshold    # varsayılan 0.01 (kısıtın %1'i)
```

Yeni/güncellenen metrikler:
```
delta_rel_max            # max δ_rel
delta_rel_integral       # ∫ δ_rel dt
delta_active_rate        # δ_rel > eşik olan adımların oranı
delta_first_t            # δ_rel'in ilk eşiği aştığı an
```

### Eşik duyarlılık analizi (zorunlu)
Eşik keyfi bir seçim olduğu için, sonucun ona ne kadar bağlı olduğu
gösterilmeli. Mevcut veriden üç eşikte yeniden çıkar:

```
delta_threshold ∈ {0.01, 0.05, 0.10}
→ her hücre için üç ayrı v_crit(feasibility)
```

Eşik değiştikçe sınır kayıyorsa bu raporlanır; kaymıyorsa sonuç sağlam demektir.
Makalede tek bir eşik seçilir ama duyarlılık ek olarak verilir.

### Beklenen kazanç
Bu düzeltme, raporun "sınırlama" diye geçtiği şeyi ana bulguya çeviriyor.
Ölçülebilen iki nokta zaten çarpıcı:
```
L=0.20:  feasibility 0.638   vs   çarpışma 1.313
L=0.30:  feasibility 0.788   vs   çarpışma 1.363
```
Aktüatör limiti, güvenliğin bozulduğu hızın **yarısında** bağlayıcı hale
geliyor. Arada geniş bir "doygun ama hâlâ başarılı" rejimi var — bu, çalışmanın
başlığındaki feasibility karakterizasyonunun tam cevabı.

Eşik düzeltilip tüm hücrelerde ölçülünce ana figürlerden biri olur.

---

## DÜZELTME 3 — L-BAĞIMSIZ MARJ METRİĞİ

### Tespit: L büyüdükçe `margin_violation` gövde güvenliğini izlemeyi bırakıyor

L = 0.30 iken:
```
‖p_eff − p_o‖ ≤ ‖p_merkez − p_o‖ + 0.30
contact anında:  ≤ 0.3737 + 0.30 = 0.674  >  d_safe = 0.5237
→ ÇARPIŞMA OLDUĞU HALDE h ≥ 0 KALABİLİR
```

Tabloda tam olarak bu görünüyor:
```
L = 0.30:   çarpışma v_crit = 1.363
            marj     v_crit = "ihlal yok (>1.5)"
```
1.363'te robot çarpıyor ama h hâlâ pozitif.

Yani **"L arttıkça marj sınırı iyileşiyor" okuması yanlış.** İyileşen şey
filtre değil; metrik gövdeyi izlemeyi bırakmış. `d_safe − L = 0.2237 < 0.3737`
olduğu için korunan nokta gövdenin dışında.

### Düzeltme: ikinci, L'den bağımsız metrik
```python
# Mevcut (L'ye bağlı, filtrenin kendi tanımı):
margin_violation = h_min < 0                        # ‖p_eff − p_o‖ < d_safe

# YENİ (gövde referanslı, L'den bağımsız):
body_margin_violation = d_min_center < d_safe       # ‖p_merkez − p_o‖ < d_safe
body_margin_depth     = max(0, d_safe - d_min_center)
```

Üç metrik artık net bir hiyerarşi oluşturuyor:
```
contact               → fiziksel temas          (‖p_merkez−p_o‖ < 0.3737)
body_margin_violation → gövde marjı             (‖p_merkez−p_o‖ < 0.5237)
margin_violation      → filtrenin kendi kümesi  (‖p_eff−p_o‖    < 0.5237)
```

`contact ⟹ body_margin_violation` her zaman (0.3737 < 0.5237, aynı nokta).
Bu ilişki L'den bağımsız — doğrulama kontrolü olarak kullanılabilir.

### Yapılacaklar
1. Metriği ekle, mevcut 750 koşuyu yeniden çıkar
2. L taraması tablosunu `body_margin_violation` ile yeniden üret
3. L karşılaştırmasında **birincil metrik bu olsun**; `margin_violation`
   ikincil olarak kalsın (filtrenin kendi tanımının nasıl kaydığını gösterir)

### Tez/makale metnine
L, gövde marjı ile kontrol yetkisi arasında bir takas yapıyor:
- L ↑ → aynı ω için daha fazla yanal manevra kapasitesi (kaçış hızı L·ω)
- L ↑ → korunan nokta gövdeden uzaklaşıyor, `h ≥ 0` gövde güvenliğini
  garanti etmiyor

`d_safe_mode = fixed` bu takası ortadan kaldırmıyor, sadece ikinci yönünü
görünmez yapıyor. Her iki yön de raporlanmalı.

---

## SONRAKİ (koşu gerektiren, bu üçünden SONRA)

Bilgi olarak: bu üç düzeltme kapandıktan sonra sıra şöyle.

```
4. Nominal noktayı 5× tekrarla → gürültü tabanını resmen ölç      ~300 koşu
   (w_w=1.0, α=1.0, L=0.10 üç taramada 1.228 / 1.221 / 1.200 verdi
    → gözlenen yayılım 0.028; bu resmen ölçülmeli ve tüm v_crit'ler
      ± bu değerle raporlanmalı. Üç ondalık basamak sahte hassasiyet.)

5. Tüm v_crit'leri güven aralığıyla yeniden raporla                analiz

6. α = 0.75 ve 1.5 ekle                                           ~120 koşu
   (tepe 4 noktalı ızgarada 1.0'da çıktı ama 1.0 zaten varsayılandı;
    tepenin yeri çözülmemiş. 0.5→1.0 kazancı 0.113, 1.0→2.0 kaybı 0.244 —
    asimetri var, düşüşün nerede başladığı bilinmiyor.)

7. Feasibility sınırını düzeltilmiş eşikle tüm hücrelerde tara

8. İŞ 6 — T taraması (720 koşu)
```

**4 numara olmadan hiçbir eğri yorumlanamaz.** Şu anda hangi farkın gerçek
hangisinin gürültü olduğu ayırt edilemiyor:

| İddia | Yayılım | Gözlenen gürültü (0.028) | Hüküm |
|---|---|---|---|
| w_w → marj sınırı düşüyor | 0.150 | 5× | gerçek |
| α → tepe noktalı eğri | 0.244 | 8× | gerçek |
| w_w → çarpışma sınırı | 0.053 | 1.9× | ayırt edilemez |
| L → çarpışma sınırı iyileşiyor | 0.050 | 1.8× | ayırt edilemez |
| w_w=0.25 vs 0.5 farkı | 0.017 | 0.6× | ayırt edilemez |

---

## SIRA

```
1. Üç metrik tek koşu havuzundan + sıralama doğrulaması   [kod, yeniden çıkarım]
2. delta_rel + eşik tanımı + duyarlılık analizi           [kod, yeniden çıkarım]
3. body_margin_violation metriği                          [kod, yeniden çıkarım]
```

Üçü de mevcut 750 koşunun bag'lerinden çalışıyor. Yeni koşu yok.

Bitince sonuç tablosunu yeniden üret ve hangi sonuçların değiştiğini
`results/CHANGELOG.md`'ye yaz.
