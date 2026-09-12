// CBF-QP Guvenlik Filtresi -- akademik sunum
// Kullanim: node sunum.js cikti.pptx
const pptxgen = require('pptxgenjs');
const path = require('path');

const DOCS = 'C:/proje/proje/tez_cbf/docs';

// ---------- renkler / tipografi ----------
const NAVY = '1F3864';
const ACCENT = '2E74B5';
const GREY = '6B6B6B';
const DARK = '262626';
const LIGHT_BG = 'F2F2F2';
const LINE_GREY = 'D9D9D9';
const RED_BG = 'FBE4E4';
const RED_LINE = 'C0392B';
const AMBER = 'BF8F00';
const AMBER_BG = 'FFF2CC';
const CHIP_BG = 'DEEBF7';

const FONT = 'Calibri';
const MONO = 'Consolas';

const PAGE_W = 13.333, PAGE_H = 7.5;
const MX = 0.6;
const CW = PAGE_W - 2 * MX;

const pptx = new pptxgen();
pptx.defineLayout({ name: 'WIDE', width: PAGE_W, height: PAGE_H });
pptx.layout = 'WIDE';
pptx.author = '';
pptx.company = '';
pptx.subject = '';
pptx.title = 'CBF-QP Guvenlik Filtresi';

function newSlide() {
  const s = pptx.addSlide();
  s.background = { color: 'FFFFFF' };
  return s;
}
function addTitle(s, text) {
  s.addText(text, {
    x: MX, y: 0.42, w: CW, h: 0.72,
    fontFace: FONT, fontSize: 26, bold: true, color: NAVY,
    align: 'left', valign: 'top',
  });
}
function addBody(s, text, opts = {}) {
  s.addText(text, Object.assign({
    x: MX, y: opts.y || 1.4, w: opts.w || CW, h: opts.h || 1.0,
    fontFace: FONT, fontSize: opts.size || 15, color: opts.color || DARK,
    align: 'left', valign: 'top', lineSpacingMultiple: 1.18, bold: !!opts.bold,
    italic: !!opts.italic,
  }, opts));
}
function addBullets(s, items, opts = {}) {
  const runs = items.map((it) => ({
    text: it,
    options: { bullet: { characterCode: '2013', indent: 16 }, breakLine: true, paraSpaceAfter: opts.gap === undefined ? 10 : opts.gap },
  }));
  s.addText(runs, Object.assign({
    x: MX, y: opts.y || 1.4, w: opts.w || CW, h: opts.h || 4.5,
    fontFace: FONT, fontSize: opts.size || 15.5, color: opts.color || DARK,
    valign: 'top', lineSpacingMultiple: 1.18,
  }, opts));
}
function addCode(s, lines, opts = {}) {
  const size = opts.size || 14;
  const h = opts.h || (lines.length * (size / 72 * 1.35) + 0.28);
  const w = opts.w || CW;
  const x = opts.x === undefined ? MX : opts.x;
  s.addShape(pptx.ShapeType.rect, {
    x, y: opts.y, w, h,
    fill: { color: opts.fillColor || LIGHT_BG }, line: { color: LINE_GREY, width: 0.75 },
  });
  s.addText(lines.join('\n'), {
    x: x + 0.2, y: opts.y + 0.1, w: w - 0.4, h: h - 0.2,
    fontFace: MONO, fontSize: size, color: opts.color || DARK, valign: 'top', lineSpacingMultiple: 1.08,
  });
  return h;
}
function calloutBox(s, text, opts = {}) {
  const fill = opts.fill || CHIP_BG;
  const line = opts.line || ACCENT;
  s.addShape(pptx.ShapeType.roundRect, {
    x: opts.x === undefined ? MX : opts.x, y: opts.y, w: opts.w || CW, h: opts.h,
    rectRadius: 0.05, fill: { color: fill },
    line: { color: line, width: 1.0 },
  });
  s.addText(text, {
    x: (opts.x === undefined ? MX : opts.x) + 0.22, y: opts.y + 0.08, w: (opts.w || CW) - 0.44, h: opts.h - 0.16,
    fontFace: FONT, fontSize: opts.size || 14.5, color: opts.color || DARK, valign: 'middle',
    italic: !!opts.italic, lineSpacingMultiple: 1.12,
  });
}
function addNote(s, text) { s.addNotes(text); }

function tableRow(cells, opts = {}) {
  return cells.map((c) => {
    const text = typeof c === 'string' ? c : c.text;
    const o = typeof c === 'string' ? {} : (c.options || {});
    return { text, options: Object.assign({ fontFace: FONT, fontSize: 14, color: DARK, valign: 'middle', margin: 6 }, opts, o) };
  });
}

// ============================================================
// SLAYT 1 -- Baslik
// ============================================================
{
  const s = newSlide();
  s.addText('CBF-QP Güvenlik Filtreleri:\nUygulanabilirlik Sınırının Deneysel Karakterizasyonu', {
    x: 1.0, y: 2.55, w: PAGE_W - 2.0, h: 2.4,
    fontFace: FONT, fontSize: 32, bold: true, color: NAVY, align: 'center', valign: 'middle',
    lineSpacingMultiple: 1.2,
  });
  addNote(s, 'Başlık slaydı — talimat gereği isim, tarih, kurum, logo yok. Sunumun konusu tek cümlede: girdi kısıtlı bir mobil robotta CBF tabanlı güvenlik filtresinin ne zaman işe yaramadığını (feasibility sınırı) karakterize ediyoruz. Yeni bir filtre önermiyoruz — mevcut bir filtrenin çalışma zarfını ölçüyoruz.');
}

// ============================================================
// SLAYT 2 -- Icindekiler
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'İçindekiler');
  const sections = [
    ['I', 'Problem ve teorik çerçeve', '3–7'],
    ['II', 'Mimari ve formülasyon', '8–10'],
    ['III', 'Deneysel karakterizasyon', '11–14'],
    ['IV', 'Yol haritası', '15–17'],
  ];
  let y = 2.05;
  sections.forEach(([num, title, range]) => {
    s.addText(num, { x: MX, y, w: 1.0, h: 0.95, fontFace: FONT, fontSize: 30, bold: true, color: ACCENT, align: 'left', valign: 'middle' });
    s.addText(title, { x: MX + 1.2, y, w: 8.6, h: 0.95, fontFace: FONT, fontSize: 20, color: DARK, valign: 'middle' });
    s.addText(range, { x: PAGE_W - MX - 1.8, y, w: 1.8, h: 0.95, fontFace: FONT, fontSize: 16, color: GREY, align: 'right', valign: 'middle' });
    y += 1.18;
  });
  addNote(s, 'Dört bölüm: I. Problem ve teori (3-7) — sunumun gövdesi. II. Mimari ve formülasyon (8-10). III. Deneysel karakterizasyon (11-14) — bilinçli olarak kısa tutuldu, iki alt slayta bölündü (bulgular + görseller) okunabilirlik için. IV. Yol haritası (15-17).');
}

// ============================================================
// SLAYT 3 -- Problem tanimi
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Problem Tanımı');
  addBody(s, 'Platform: TurtleBot3 Burger, diferansiyel sürüş, ROS 2 / Gazebo.', { y: 1.32, h: 0.45, size: 16 });
  addCode(s, [
    'v_max = 0.22 m/s          ω_max = 2.84 rad/s',
    'robot yarıçapı = 0.1237 m (URDF, en kötü köşe)',
    'engel yarıçapı = 0.25 m',
    'temas mesafesi = 0.3737 m (merkez–merkez)',
  ], { y: 1.9, size: 15.5 });
  addBody(s, 'Engel hızları 0.4–1.4 m/s  →  hız oranı 1.8× – 6.4×', {
    y: 3.55, h: 0.55, size: 19, bold: true, color: ACCENT,
  });
  addBody(s, 'Bu rejimde robot engeli geçemez veya savuşamaz; yalnızca doğru anda doğru yerde olmamayı başarabilir. Soru: güvenlik filtresi bunu ne zaman başarabiliyor, ne zaman aktüatör limitleri yüzünden başaramıyor?', {
    y: 4.25, h: 1.5, size: 16.5,
  });
  calloutBox(s, 'ICS (Inevitable Collision States) çerçevesinin girdi-kısıtlı bir platformdaki nicel karşılığı.', {
    y: 5.95, h: 0.75, fill: LIGHT_BG, line: LINE_GREY, italic: true, color: GREY, size: 14.5,
  });
  addNote(s, 'Hız oranı 1.8-6.4x arası — bu, robotun kendi maksimum hızının katları cinsinden engelin ne kadar hızlı geldiği. Bu rejimde klasik "kaç ya da geçir" stratejileri çalışmıyor, çünkü robot ne kaçabilecek kadar hızlı ne de engeli fiziksel olarak geçebilecek durumda. Vurgulanacak: bu bir "iyi ayarlanmamış filtre" sorunu değil, temelde geometrik/kinematik bir sınırlama sorunu.');
}

// ============================================================
// SLAYT 4 -- Teorik cerceve (Lyapunov vs CBF)
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Teorik Çerçeve: CBF ve Lyapunov');
  const rows = [
    [
      { text: 'LYAPUNOV (CLF)', options: { bold: true, fill: { color: CHIP_BG }, align: 'center', color: NAVY } },
      { text: 'CBF', options: { bold: true, fill: { color: CHIP_BG }, align: 'center', color: NAVY } },
    ],
    ['V(x) > 0', 'h(x) ≥ 0,   C = {x : h(x) ≥ 0}'],
    ['V̇ ≤ −γ·V', 'ḣ ≥ −α(h)'],
    ['her yerde monoton azalma', 'yalnızca sınıra yakın bağlar'],
    ['iddia: hedefe yakınsar', 'iddia: güvenli kümeden çıkmaz'],
    ['attractivity', 'forward invariance'],
    ['tek bir davranış dayatır', 'tek taraflı, gerisi serbest'],
  ].map((r) => tableRow(r, { fontSize: 15 }));
  s.addTable(rows, {
    x: MX, y: 1.45, w: CW, colW: [CW / 2, CW / 2],
    border: { type: 'solid', color: LINE_GREY, pt: 0.75 },
    autoPage: false,
  });
  addBody(s, 'α·h terimi: h sıfıra yaklaştıkça izin verilen azalma hızı da sıfıra yaklaşır → küme ileri değişmez.', {
    y: 5.35, h: 0.65, size: 15.5,
  });
  calloutBox(s, 'Bu tek taraflılık, filtrenin "asgari müdahaleci" olabilmesinin sebebidir: CBF tercih bildirmez, yalnızca veto hakkı kullanır.', {
    y: 6.1, h: 0.75, size: 15, color: NAVY,
  });
  addNote(s, 'Lyapunov "hedefe git" der (attractivity, çift taraflı bir talep: hem yakınsa hem her yerde). CBF "o kümeden çıkma" der (forward invariance, tek taraflı: sadece sınıra yaklaşınca kısıtlar, içeride serbest bırakır). Bu asimetri CBF-QP filtresinin neden "görünmez" kalabildiğini açıklıyor — sadece gerektiğinde araya giriyor.');
}

// ============================================================
// SLAYT 5 -- Turetme zinciri (DIYAGRAM) + kucuk karsilastirma tablosu
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Türetme Zinciri: Kümeden QP\'ye');

  const steps = [
    ['Güvenli küme', 'C = { x : h(x) ≥ 0 }'],
    ['CBF koşulu', 'ḣ ≥ −α(h)'],
    ['Control-affine', 'ẋ = f(x) + g(x)u   ⟹   ḣ = L_f h + L_g h·u'],
    ['Lineer kısıt', 'L_g h·u ≥ −αh − L_f h     (u uzayında yarı-düzlem)'],
    ['Sonsuz çözüm', 'yarı-düzlemdeki her nokta güvenli — hangisi?'],
    ['Doğal cevap', 'nominal komuta en yakın olan'],
    ['QP', 'min ‖u − u_nom‖²    s.t. lineer kısıt,  u ∈ U'],
  ];
  const rowH = 0.46, gap = 0.09;
  let y = 1.35;
  const labelW = 2.15;
  steps.forEach(([label, formula], i) => {
    const isLast = i === steps.length - 1;
    s.addShape(pptx.ShapeType.roundRect, {
      x: MX, y, w: CW, h: rowH, rectRadius: 0.045,
      fill: { color: isLast ? CHIP_BG : 'F7F9FC' },
      line: { color: isLast ? ACCENT : LINE_GREY, width: isLast ? 1.25 : 0.75 },
    });
    s.addText(label, {
      x: MX + 0.15, y, w: labelW, h: rowH, fontFace: FONT, fontSize: 12.5, bold: true,
      color: isLast ? ACCENT : NAVY, valign: 'middle',
    });
    s.addText(formula, {
      x: MX + labelW + 0.15, y, w: CW - labelW - 0.3, h: rowH, fontFace: MONO,
      fontSize: isLast ? 13.5 : 12, color: DARK, valign: 'middle',
    });
    if (!isLast) {
      const cx = MX + CW / 2;
      s.addShape(pptx.ShapeType.line, {
        x: cx, y: y + rowH, w: 0, h: gap,
        line: { color: GREY, width: 1.25, endArrowType: 'triangle' },
      });
    }
    y += rowH + gap;
  });

  addBody(s, 'QP bir çözücü değil, problem tipidir: her kontrol adımında sıfırdan kurulup çözülür — 10 Hz\'de saniyede 10 bağımsız problem, aralarında hafıza yok.', {
    y: y + 0.05, h: 0.55, size: 12.5, italic: true, color: GREY,
  });

  // kucuk karsilastirma tablosu
  const cmpHeader = ['Yöntem', 'Maliyet', 'Kısıt', 'Ufuk', 'Çözüm yöntemi', 'Tek başına kontrolcü mü'].map((t) =>
    ({ text: t, options: { bold: true, fill: { color: CHIP_BG }, align: 'center', color: NAVY, fontSize: 10.5 } }));
  const cmpData = [
    ['LQR', 'ikinci derece\n(durum+girdi)', 'yok', 'sonsuz', 'Riccati\n(çevrimdışı)', 'Evet'],
    ['MPC', 'ikinci derece\n(ufuk boyu)', 'durum+girdi', 'sonlu, kayan', 'QP/NLP\n(çevrimiçi)', 'Evet'],
    ['CBF-QP', '‖u−u_nom‖²\n(anlık)', 'güvenlik+girdi', 'anlık (T=0)', 'QP\n(çevrimiçi)', 'Hayır (filtre)'],
  ].map((r) => tableRow(r, { fontSize: 10.5, align: 'center' }));
  s.addTable([cmpHeader, ...cmpData], {
    x: MX, y: y + 0.62, w: CW, colW: [1.15, 2.1, 1.85, 1.55, 1.75, CW - 1.15 - 2.1 - 1.85 - 1.55 - 1.75],
    border: { type: 'solid', color: LINE_GREY, pt: 0.5 }, autoPage: false, rowH: 0.32,
  });

  addNote(s, 'Her ok bir zorunluluk, tercih değil. Kritik geçiş: "sonsuz çözüm" adımında bir şey seçmemiz gerekiyor, ve doğal/asgari-müdahale cevabı nominal komuta en yakın nokta — bu QP\'yi doğurur. Alttaki tablo CBF-QP\'yi tanıdık kontrolcülerle konumlandırıyor: LQR ve MPC\'den farklı olarak CBF-QP tek başına bir kontrolcü değil, bir FİLTRE — bir nominal komut olmadan hiçbir şey üretmez.');
}

// ============================================================
// SLAYT 6 -- Sistem modeli + bariyer + u-duzlemi semasi
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Sistem Modeli ve Bariyer Fonksiyonu');

  const leftW = 7.1;
  addCode(s, [
    'Unicycle:   ẋ = v cos θ,   ẏ = v sin θ,   θ̇ = ω',
    '            u = [v, ω]ᵀ,  v ∈ [0, 0.22],  ω ∈ [−2.84, 2.84]',
    '',
    'Bariyer:    h = ‖p_eff − p_o‖² − d_safe²',
    '            d_safe = temas(0.3737) + L(0.10) + marj(0.05) = 0.5237',
  ], { x: MX, y: 1.5, w: leftW, size: 13.5 });

  addBody(s, 'Sistem nonlineer ama control-affine: g(x) içinde cos θ, sin θ var, sabit B matrisi değil. Kısıtın u\'da lineer olması bu yapıdan geliyor.', {
    x: MX, y: 3.35, w: leftW, h: 1.3, size: 15,
  });

  calloutBox(s, 'QP\'nin çözdüğü geometri: yarı-düzlem (güvenlik) ∩ kutu (donanım) içinde u_nom\'a en yakın nokta.', {
    x: MX, y: 4.85, w: leftW, h: 0.95, size: 14, italic: true,
  });

  // ---- u-duzlemi semasi (sag panel) ----
  const px = MX + leftW + 0.5, py = 1.45, pw = PAGE_W - MX - px, ph = 4.55;
  s.addShape(pptx.ShapeType.rect, { x: px, y: py, w: pw, h: ph, fill: { color: 'FFFFFF' }, line: { color: LINE_GREY, width: 0.75 } });

  const ox = px + 0.85, oy = py + ph / 2;
  // eksenler
  s.addShape(pptx.ShapeType.line, { x: px + 0.25, y: oy, w: pw - 0.7, h: 0, line: { color: GREY, width: 1.25, endArrowType: 'triangle' } });
  s.addText('v', { x: px + pw - 0.42, y: oy - 0.36, w: 0.35, h: 0.32, fontFace: MONO, fontSize: 14, italic: true, color: DARK });
  s.addShape(pptx.ShapeType.line, { x: ox, y: py + ph - 0.3, w: 0, h: -(ph - 0.6), line: { color: GREY, width: 1.25, endArrowType: 'triangle' } });
  s.addText('ω', { x: ox - 0.32, y: py + 0.06, w: 0.35, h: 0.32, fontFace: MONO, fontSize: 14, italic: true, color: DARK });

  // kutu (girdi kisiti U)
  const boxW = 2.15, boxH = 2.35;
  s.addShape(pptx.ShapeType.rect, {
    x: ox, y: oy - boxH / 2, w: boxW, h: boxH,
    fill: { type: 'none' }, line: { color: NAVY, width: 1.25, dashType: 'dash' },
  });

  // guvensiz ucgen (sol-alt kose)
  const triX = ox, triY = oy + boxH / 2 - 1.05, triW = 1.35, triH = 1.05;
  s.addShape(pptx.ShapeType.rtTriangle, {
    x: triX, y: triY, w: triW, h: triH,
    fill: { color: RED_BG, transparency: 15 }, line: { type: 'none' },
  });
  // sinir cizgisi (hipotenus: triangle ust-sol -> alt-sag)
  s.addShape(pptx.ShapeType.line, {
    x: triX, y: triY, w: triW, h: triH,
    line: { color: RED_LINE, width: 2 },
  });

  // u_nom (guvensiz bolgede) ve u* (sinir uzerinde)
  const unom = { x: triX + 0.32, y: triY + 0.78 };
  const t = 0.55;
  const ustar = { x: triX + triW * t, y: triY + triH * t };
  s.addShape(pptx.ShapeType.ellipse, { x: unom.x - 0.05, y: unom.y - 0.05, w: 0.1, h: 0.1, fill: { color: RED_LINE }, line: { type: 'none' } });
  s.addText('u_nom', { x: unom.x - 0.75, y: unom.y + 0.06, w: 0.85, h: 0.28, fontFace: MONO, fontSize: 11.5, color: RED_LINE, align: 'right' });
  s.addShape(pptx.ShapeType.ellipse, { x: ustar.x - 0.05, y: ustar.y - 0.05, w: 0.1, h: 0.1, fill: { color: ACCENT }, line: { type: 'none' } });
  s.addText('u*', { x: ustar.x + 0.08, y: ustar.y - 0.32, w: 0.6, h: 0.28, fontFace: MONO, fontSize: 12.5, bold: true, color: ACCENT });
  s.addShape(pptx.ShapeType.line, {
    x: unom.x, y: unom.y, w: ustar.x - unom.x, h: ustar.y - unom.y,
    line: { color: GREY, width: 1, dashType: 'dash', endArrowType: 'triangle' },
  });

  s.addText('kutu = girdi kısıtı U        gölgeli bölge = güvenlik ihlali', {
    x: px, y: py + ph + 0.08, w: pw, h: 0.4, fontFace: FONT, fontSize: 10.5, color: GREY, align: 'center',
  });

  addNote(s, 'Sağdaki şema QP\'nin geometrisini gösteriyor: v-ω düzleminde kutu, donanım limitlerini (girdi kısıtı U) temsil ediyor; gölgeli üçgen güvenlik kısıtının ihlal edildiği bölge. u_nom (nominal komut) bu bölgenin içine düşerse, QP onu sınırın üzerindeki en yakın noktaya (u*) projekte ediyor — bu, filtrenin "asgari müdahale" ilkesinin görsel karşılığı.');
}

// ============================================================
// SLAYT 7 -- Relative degree ve lookahead onarimi
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Relative Degree ve Lookahead Onarımı');

  addBody(s, 'Robot merkezinde yazılan bariyer:', { y: 1.35, h: 0.4, size: 15.5 });
  addCode(s, [
    'h = ‖e‖² − d²    ⟹    ḣ = 2v(e·t̂)        ← ω HİÇ GÖRÜNMÜYOR',
  ], { y: 1.8, size: 15 });
  addBody(s, 'Kısıt dönüşü kısıtlayamıyor; filtrenin tek yapabildiği frenlemek.', {
    y: 2.55, h: 0.5, size: 15.5, italic: true, color: GREY,
  });

  addBody(s, 'Lookahead onarımı:', { y: 3.2, h: 0.4, size: 15.5, bold: true, color: ACCENT });
  addCode(s, [
    'p_eff = (x + L cos θ,  y + L sin θ)',
    'ṗ_eff = v·t̂ + Lω·n̂                       ← ω türeve giriyor',
  ], { y: 3.65, size: 15 });

  calloutBox(s,
    'Onarımın bedeli: CBF ‖p_eff − p_o‖ ≥ d_safe garanti eder; ama çarpışan şey gövde, ve gövde p_eff\'ten L kadar geride. d_safe\'e L payı eklenmek zorunda. L, gövde marjı ile kontrol yetkisi arasında bir takas yaratıyor.',
    { y: 5.1, h: 1.55, size: 15, fill: AMBER_BG, line: AMBER });

  addNote(s, 'Bu, "bağıl derece" probleminin somut hali: h robot merkezine yazılınca ω türevde hiç görünmüyor (teğet yön t̂ ile hız çarpımı sadece v içeriyor). Çözüm, bariyeri merkezden L kadar ileride sanal bir noktaya (lookahead) yazmak — bu noktanın hızı hem v hem ω\'ya bağlı (normal yön n̂ üzerinden). Ama bunun bir bedeli var: artık garanti edilen şey gövdenin değil, bu sanal noktanın güvenliği — L kadar bir pay eklemek zorunda kalıyoruz.');
}

// ============================================================
// SLAYT 8 -- Mimari (DIYAGRAM)
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Mimari');

  const boxW = 5.0, cx = PAGE_W / 2;
  const bx = cx - boxW / 2;
  const boxH = 0.85;
  const y1 = 1.55, y2 = 3.15, y3 = 4.75;

  function block(y, label, fill, line, color) {
    s.addShape(pptx.ShapeType.roundRect, {
      x: bx, y, w: boxW, h: boxH, rectRadius: 0.06,
      fill: { color: fill }, line: { color: line, width: 1.25 },
    });
    s.addText(label, {
      x: bx + 0.15, y, w: boxW - 0.3, h: boxH, fontFace: FONT, fontSize: 14.5, bold: true,
      color: color, align: 'center', valign: 'middle', lineSpacingMultiple: 1.05,
    });
  }
  block(y1, 'Nominal kontrolcü\n(hedefe yönelme, ENGELDEN HABERSİZ)', 'F7F9FC', GREY, DARK);
  block(y2, 'CBF-QP güvenlik filtresi', CHIP_BG, ACCENT, NAVY);
  block(y3, 'TurtleBot3 (Gazebo)', 'F7F9FC', GREY, DARK);

  function arrow(yTop, yBot, label) {
    s.addShape(pptx.ShapeType.line, { x: cx, y: yTop, w: 0, h: yBot - yTop, line: { color: GREY, width: 1.5, endArrowType: 'triangle' } });
    s.addText(label, { x: cx + 0.15, y: yTop + (yBot - yTop) / 2 - 0.16, w: 3.2, h: 0.32, fontFace: MONO, fontSize: 11.5, color: DARK, valign: 'middle' });
  }
  arrow(y1 + boxH, y2, 'u_nom = (v_nom, ω_nom)');
  arrow(y2 + boxH, y3, 'u_safe = (v_safe, ω_safe)');

  // engel durumu kutusu, filtreye yandan giriyor
  const ew = 3.35;
  const ex = bx + boxW + 0.55;
  s.addShape(pptx.ShapeType.roundRect, {
    x: ex, y: y2, w: ew, h: boxH, rectRadius: 0.06,
    fill: { color: 'F7F9FC' }, line: { color: GREY, width: 1.25 },
  });
  s.addText('Engel durumu\n(ground truth; kestirim\nkatmanı planlanıyor)', {
    x: ex + 0.1, y: y2, w: ew - 0.2, h: boxH, fontFace: FONT, fontSize: 12, color: DARK,
    align: 'center', valign: 'middle', lineSpacingMultiple: 1.05,
  });
  s.addShape(pptx.ShapeType.line, {
    x: ex, y: y2 + boxH / 2, w: -(ex - (bx + boxW)), h: 0,
    line: { color: GREY, width: 1.5, endArrowType: 'triangle' },
  });

  calloutBox(s,
    'İzolasyon: nominal katmanın engelden haberi yok. Kaçınmanın tamamı filtreden gelir, böylece filtrenin katkısı ölçülebilir. Bu bilinçli bir tasarım tercihi — hazır bir yerel planlayıcının kendi kaçınması filtrenin katkısına karışırdı.',
    { y: 5.85, h: 1.1, size: 14.5 });

  addNote(s, 'Mimarideki en önemli tasarım kararı: nominal kontrolcü tamamen engelden habersiz. Bu izolasyon sayesinde ölçtüğümüz her kaçınma davranışı doğrudan filtreye atfedilebiliyor — bir Nav2/DWB gibi hazır bir planlayıcı kullansaydık, kendi kaçınma mantığı filtrenin etkisiyle karışırdı ve neyin neden kaynaklandığını ayıramazdık.');
}

// ============================================================
// SLAYT 9 -- Filtre modlari
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Filtre Modları');
  const header = ['Mod', 'Kısıtta engel hızı', 'Not'].map((t) =>
    ({ text: t, options: { bold: true, fill: { color: CHIP_BG }, color: NAVY, fontSize: 15 } }));
  const rows = [
    ['REACTIVE', 'yok', 'sabit engel varsayımı — model hatası'],
    ['SHIFT_NAIVE', 'konum kaydırılır, türev düzeltilmez', 'matematiksel olarak hatalı'],
    ['SHIFT_CORRECT', 'ḣ = 2Δp_s·(v_r − v_o)', 'doğru türev'],
    ['DCBF', 'L_f h = −2(e·v_o)', '≡ SHIFT_CORRECT(T=0)'],
  ].map((r) => tableRow(r, { fontSize: 14.5 }));
  s.addTable([header, ...rows], {
    x: MX, y: 1.6, w: CW, colW: [2.2, 4.2, CW - 2.2 - 4.2],
    border: { type: 'solid', color: LINE_GREY, pt: 0.75 }, autoPage: false, rowH: 0.62,
  });
  calloutBox(s, 'Son satırdaki eşdeğerlik ampirik olarak doğrulandı.', {
    y: 4.4, h: 0.65, italic: true, size: 15,
  });
  addNote(s, 'Dört mod, tek bir farkla ayrılıyor: engelin hareketi ḣ\'ye nasıl giriyor. REACTIVE hiç girmiyor (model hatası — engel duruyor sanılıyor). SHIFT_NAIVE konumu ileri kaydırıyor ama türevi buna göre düzeltmiyor — bu bir bug, ve REACTIVE\'den bile kötü sonuç veriyor. SHIFT_CORRECT doğru türetilmiş hali. DCBF ise SHIFT_CORRECT\'in T=0 (öngörü ufku sıfır) özel hali — bunu hem matematiksel olarak türettik hem deneysel olarak (T=0 koşularında iki modun birebir aynı çıktığını göstererek) doğruladık.');
}

// ============================================================
// SLAYT 10 -- Slack gevsetmesi
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Slack Gevşetmesi');
  addCode(s, [
    'min  ‖u − u_nom‖²_W + ρ·δ²',
    's.t. ḣ ≥ −α·h − δ,   δ ≥ 0',
  ], { y: 1.45, size: 17 });

  addBullets(s, [
    'Karar değişkeni [v, ω, δ]. Neden: hard modda kısıt sağlanamadığında davranış tanımsızdı.',
    'δ, feasibility ölçümünü ikiliden sürekliye çeviriyor — "infeasible mi" yerine "sınırın ne kadar dışındayız".',
    'Ölçek bağımsızlığı için δ_rel = δ / max(|α·h|, ε), aktiflik eşiği %1.',
  ], { y: 2.9, h: 2.0, size: 15.5, gap: 12 });

  calloutBox(s,
    'Ayrıca: QP maliyeti normalize edilmeli. v ve ω aralıkları arasında ~26× ölçek farkı var; normalize edilmezse filtre için tamamen durmak, küçük bir dönüşten ucuz hale geliyor.',
    { y: 5.35, h: 1.2, size: 15, fill: AMBER_BG, line: AMBER });

  addNote(s, 'Slack, hard-kısıtlı QP\'nin çözümsüz kaldığı anlarda "ne olacağı tanımsız" sorununu çözüyor: δ≥0 gevşeme değişkeni ekleyip ihlali maliyete (ρ·δ²) sokuyoruz. δ_rel normalizasyonu önemli çünkü ham δ, α ve h\'nin ölçeğine göre anlamsız büyür/küçülür — normalize etmeden "aktif mi değil mi" eşiği koymak mümkün değil. Maliyet normalizasyonu ayrı bir konu: v ve ω\'nın fiziksel aralıkları çok farklı, bunu düzeltmezseniz optimizasyon sessizce yanlış tercihler yapar.');
}

// ============================================================
// SLAYT 11 -- Deneyler: ne yaptik
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Deneyler: Ne Yaptık');
  addBullets(s, [
    'Otomatik kampanya altyapısı: deterministik senaryo başlatma, otomatik kayıt, metrik çıkarımı, parametre taraması, kesintiye dayanıklı çalışma.',
    'Ölçek: ~2.500 simülasyon koşusu.',
    'Taranan eksenler: engel hızı, yanal ofset, filtre modu, öngörü ufku T, sınıf-K katsayısı α, lookahead kolu L, maliyet ağırlığı w.',
  ], { y: 1.4, h: 2.2, size: 16 });

  calloutBox(s,
    'Yöntem notu: dört parametre ekseninin tam kartezyen çarpımı ~172.000 koşu ederdi. Aranan şey bir yüzey değil bir eğri olduğu için, ikili aramayla sınır doğrudan izlendi — yaklaşık 1/100 maliyet.',
    { y: 3.75, h: 1.05, size: 15 });

  addCode(s, [
    'çarpışma      fiziksel temas',
    'gövde marjı   gövde merkezine göre d_safe ihlali',
    'feasibility   δ_rel > %1, aktüatör limiti bağlayıcı',
  ], { y: 5.05, size: 15 });

  addNote(s, 'Bu bölümü kısa tutuyoruz — asıl vurgu teori ve mimaride. Tek metodolojik nokta önemli: tam parametre taraması yerine ikili arama (binary search) ile doğrudan sınır izlendi, çünkü ilgilendiğimiz şey bir yüzeyin tamamı değil sadece nerede kritik geçişin olduğu. Üç ayrı sınır tanımı — çarpışma, gövde marjı, feasibility — bundan sonraki bulgular slaytının temeli.');
}

// ============================================================
// SLAYT 12 -- Deneyler: ne bulduk (bulgular)
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Deneyler: Ne Bulduk — Bulgular');

  const findings = [
    ['İki ayrı güvenlik sınırı.', 'Ayrışma bandının çekirdeğinde filtre çarpışmayı önlüyor ama tasarım marjı ihlal ediliyor — girdi doygunluğunun sonucu. CBF garantisi girdi kısıtı altında pratikte bozulabiliyor.'],
    ['Aktüasyon sınırı, güvenlik sınırının yarısında.', 'feasibility ≈ 0.75 m/s, çarpışma ≈ 1.31 m/s. Arada geniş bir "doygun ama hâlâ başarılı" rejim var.'],
    ['α\'nın optimal değeri var.', 'v_crit iç bükey, tepe α=1.0\'da. Çok küçük α erken/yumuşak müdahale, otorite kalmıyor; çok büyük α geç/sert, aktüatör yetişmiyor.'],
    ['Öngörünün üst sınırı var.', 'Manevra yapan engelde büyük T, kaydırılan engel konumunu robotun gerisine düşürüyor; filtre QP açısından rahat kalıyor ama gerçek engele karşı körleşiyor. İmza: yüksek feasibility + düşük çarpışma sınırı.'],
    ['Yarım türetilmiş öngörü, öngörüsüzden kötü.', 'Türev düzeltmesi yapılmayan konum kaydırma güvenliği azaltıyor.'],
  ];
  let y = 1.35;
  const rowH = 1.02;
  findings.forEach(([lead, rest], i) => {
    s.addShape(pptx.ShapeType.ellipse, { x: MX, y: y + 0.03, w: 0.42, h: 0.42, fill: { color: CHIP_BG }, line: { color: ACCENT, width: 1 } });
    s.addText(String(i + 1), { x: MX, y: y + 0.03, w: 0.42, h: 0.42, fontFace: FONT, fontSize: 15, bold: true, color: ACCENT, align: 'center', valign: 'middle' });
    s.addText([
      { text: lead + '  ', options: { bold: true, color: NAVY } },
      { text: rest, options: { color: DARK } },
    ], {
      x: MX + 0.62, y, w: CW - 0.62, h: rowH, fontFace: FONT, fontSize: 14, valign: 'top', lineSpacingMultiple: 1.15,
    });
    y += rowH;
  });

  addNote(s, 'Beş bulgu, önem sırasına yakın: (1) sınırın tekil değil iki-katmanlı olması tezin merkezi kavramsal katkısı; (2) aktüasyon sınırının çarpışma sınırının çok öncesinde başlaması pratik tasarım için doğrudan uyarı; (3) alfa taramasının iç bükey olması "optimal" bir tasarım noktası olduğunu gösteriyor; (4) öngörü ufkunun üst sınırı en beklenmedik bulgu — sezgiye aykırı; (5) yarım türetilmiş SHIFT_NAIVE\'in REACTIVE\'den kötü çıkması matematiksel titizliğin önemini gösteriyor.');
}

// ============================================================
// SLAYT 13 -- Deneyler: ne bulduk (gorseller)
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Deneyler: Ne Bulduk — Sınır Eğrileri');
  addBody(s, 'Sayısal detaylar ve tam tablo için teknik rapora bakınız.', {
    y: 1.28, h: 0.4, size: 13.5, italic: true, color: GREY,
  });

  const gap = 0.35;
  const imgW = (CW - gap) / 2;
  const y0 = 1.85;
  const h1 = imgW * (768 / 2247);
  const h2 = imgW * (754 / 1885);

  s.addImage({ path: path.join(DOCS, 'boundary_curves_fixed.png'), x: MX, y: y0, w: imgW, h: h1 });
  s.addText('Sınır eğrileri — α, w, L eksenleri\n(çarpışma / gövde marjı / feasibility)', {
    x: MX, y: y0 + h1 + 0.12, w: imgW, h: 0.6, fontFace: FONT, fontSize: 12.5, color: GREY, align: 'center', lineSpacingMultiple: 1.1,
  });

  const x2 = MX + imgW + gap;
  s.addImage({ path: path.join(DOCS, 't_sweep_full.png'), x: x2, y: y0, w: imgW, h: h2 });
  s.addText('Öngörü ufku (T) taraması — düz vs manevra eden engel', {
    x: x2, y: y0 + h2 + 0.12, w: imgW, h: 0.6, fontFace: FONT, fontSize: 12.5, color: GREY, align: 'center', lineSpacingMultiple: 1.1,
  });

  addNote(s, 'Soldaki figür: kritik hız (v_crit) eğrileri α, w ve L eksenlerinde, üç sınır göstergesiyle (çarpışma, gövde marjı, feasibility). Sağdaki: T (öngörü ufku) taraması, düz giden ve manevra eden engel karşılaştırması — büyük T\'de manevra senaryosunda çarpışma sınırının düştüğü, ama feasibility sınırının YÜKSELDİĞİ (filtre "rahat" ama yanlış yerde) görülüyor. Bu ayrışma slayt 12\'deki 4. bulgunun görsel kanıtı.');
}

// ============================================================
// SLAYT 14 -- Gecerlilik sinirlari
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Geçerlilik Sınırları');
  addBody(s, 'Açıkça belirtilmeli:', { y: 1.35, h: 0.4, size: 16, bold: true, color: NAVY });
  addBullets(s, [
    'Tüm sonuçlar simülasyon; donanım doğrulaması yapılmadı.',
    'Engel hızı ground truth\'tan; kestirim katmanı devrede değil. Bu harita aktüasyon-sınırlı sınırı ölçüyor, kestirim-sınırlı sınır ölçülmedi.',
    'Karşılaştırma kendi modlarımız arasında; yayınlanmış bir yönteme karşı kıyas yapılmadı.',
    'Simülatör artefaktları tespit edildi (kafa-kafaya geometride tünelleme, düşük hızda stick-slip).',
    'Bazı kritik hız değerleri ölçüm değil, tarama aralığından interpolasyon.',
  ], { y: 1.95, h: 4.3, size: 16, gap: 16 });
  addNote(s, 'Bu slayt bilinçli olarak dürüst ve savunmacı değil: her madde, jürinin/dinleyicinin soracağı bir soruya önden cevap. En kritik olanı ikincisi — "aktüasyon-sınırlı" ile "kestirim-sınırlı" ayrımı, çünkü ground truth kullandığımız için ölçtüğümüz sınır SADECE aktüatör kısıtlarından kaynaklanan çöküşü yakalıyor, gerçek bir lidar/EKF zincirinin ekleyeceği belirsizliği değil.');
}

// ============================================================
// SLAYT 15 -- Yol haritasi
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Yol Haritası');

  const colW = (CW - 0.4) / 2;
  const xL = MX, xR = MX + colW + 0.4;

  function tier(x, y, w, label, items, color) {
    s.addText(label, { x, y, w, h: 0.35, fontFace: FONT, fontSize: 14, bold: true, color, valign: 'middle' });
    s.addText(items.map((it) => ({ text: it, options: { bullet: { characterCode: '2013' }, breakLine: true, paraSpaceAfter: 6 } })), {
      x, y: y + 0.38, w, h: 2.0, fontFace: FONT, fontSize: 12, color: DARK, valign: 'top', lineSpacingMultiple: 1.1,
    });
  }

  tier(xL, 1.35, colW, 'YAKIN', [
    'Ölçüm belirsizliğinin nicelleştirilmesi (güven aralıkları)',
    'ICS sınırının analitik hesabı → indirgenemez / indirgenebilir hücre ayrımı (filtre kusuru ile fiziksel imkânsızlığın ayrıştırılması)',
    'Uyarlanabilir öngörü ufku: T_etkin = min(T, t_en_yakın_yaklaşma)',
  ], ACCENT);

  tier(xL, 3.75, colW, 'ORTA', [
    'Collision-cone CBF (C3BF) → kafa-kafaya dejenerasyonu ve gereksiz konservatifliği birlikte hedefler → aynı zamanda eksik olan harici baseline',
    'Lidar tabanlı algılama + durum kestirimi',
    '2×2 ablasyon: {ground truth, kestirim} × {düz, manevra} → kestirim-sınırlı ve aktüasyon-sınırlı başarısızlığın ayrıştırılması',
    'Gecikme ekseni: yapay gecikme enjeksiyonu, donanım öncesi hazırlık',
  ], ACCENT);

  tier(xR, 1.35, colW, 'AÇIK TASARIM KARARI (danışmanla belirlenecek)', [
    'Doygunluk rejiminde filtrenin amacı ne olmalı?',
    'Şu an: kısıt ihlali minimize ediliyor (anlık kriter).',
    'Alternatif: en yakın yaklaşma mesafesi maksimize edilebilir (terminal kriter).',
    'Literatürde infeasibility altındaki davranış büyük ölçüde tanımsız — potansiyel katkı alanı.',
  ], AMBER);

  tier(xR, 4.55, colW, 'UZAK', [
    'Donanım: robot + harici konum referansı + hareketli engel düzeneği',
    'Bildiri (simülasyon), ardından dergi (donanım sonrası)',
  ], GREY);

  addNote(s, 'Yol haritasını dört ufuk katmanında sunuyoruz. En çok tartışma yaratacak kısım sağ üstteki "açık tasarım kararı": şu an filtre anlık kısıt ihlalini minimize ediyor, ama doygunluk rejiminde belki de terminal bir kriter (en yakın yaklaşmayı maksimize etmek) daha savunulabilir olurdu — literatürde bu net değil, bu bizim için hem bir risk hem bir fırsat.');
}

// ============================================================
// SLAYT 16 -- Acik sorular
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Açık Sorular');
  const qs = [
    'Analitik sınır formülü deneysel haritayı öngörüyor mu? Öngörmüyorsa neyi ihmal ediyor — lookahead konservatifliği, ω kanalı, maliyet ağırlıkları?',
    'Sınır neye bağlı: engel hızına mı, hız oranına mı, kapanma hızına mı? Robot hızı hiç değiştirilmedi; üçü bu veri setinde ayırt edilemiyor.',
    'Doygunlukta filtre ne yapmalı? Anlık kriterin argmax\'ı "doğrudan uzağa dönük"; dönüş süresi boyunca yer değiştirme olmuyor.',
    'Tekerlek uzayındaki kare limit (v, ω) uzayında eşkenar dörtgene dönüşür. Dikdörtgen model kabiliyeti fazla tahmin ediyor — bildirilen kritik hızlar üst sınır.',
  ];
  let y = 1.5;
  const rowH = 1.28;
  qs.forEach((q) => {
    s.addText('?', { x: MX, y, w: 0.55, h: rowH, fontFace: FONT, fontSize: 26, bold: true, color: ACCENT, align: 'center', valign: 'top' });
    s.addText(q, { x: MX + 0.75, y, w: CW - 0.75, h: rowH, fontFace: FONT, fontSize: 15.5, color: DARK, valign: 'top', lineSpacingMultiple: 1.18 });
    y += rowH;
  });
  addNote(s, 'Bu sorular çözülmüş değil — bilerek açık bırakıldı. Özellikle ikincisi metodolojik bir boşluk: tüm kampanyalarda robotun kendi hızı sabit tutuldu, bu yüzden "hız oranı" ile "mutlak kapanma hızı" etkilerini birbirinden ayıramıyoruz. Dördüncüsü ise tüm sayısal sonuçlara bir çekince koyuyor: bildirdiğimiz kritik hızlar muhtemelen gerçek kabiliyetten daha iyimser (üst sınır).');
}

// ============================================================
// SLAYT 17 -- Ozet
// ============================================================
{
  const s = newSlide();
  addTitle(s, 'Özet');
  const points = [
    'Girdi kısıtlı nonholonomik bir platformda CBF-QP güvenlik filtresinin çalışma zarfı, dört parametre ekseninde deneysel olarak haritalandı.',
    'Fiziksel çarpışma sınırı ile CBF tasarım garantisi sınırı ayrı yerlerde; aktüatör doygunluğu, güvenliğin bozulduğu hızın yarısında başlıyor.',
    'Öngörü faydalıdır ama üst sınırı vardır — çok büyük ufuk filtreyi rahatlatarak körleştirir.',
  ];
  let y = 2.0;
  points.forEach((p, i) => {
    s.addText(String(i + 1), { x: 1.3, y, w: 0.7, h: 1.1, fontFace: FONT, fontSize: 34, bold: true, color: ACCENT, align: 'center', valign: 'top' });
    s.addText(p, { x: 2.2, y, w: PAGE_W - 2.2 - 1.0, h: 1.1, fontFace: FONT, fontSize: 18, color: DARK, valign: 'top', lineSpacingMultiple: 1.25 });
    y += 1.5;
  });
  addNote(s, 'Kapanış: bu üç cümle sunumun tamamının özeti. Vurgulanacak kelime seçimleri: "haritalandı" (ölçüldü, kanıtlandı değil), "ayrı yerlerde" (tek sınır değil), "üst sınırı vardır" (öngörü konusunda dengeli bir mesaj — ne "öngörü gereksiz" ne "öngörü her zaman iyi").');
}

// ---------- kaydet ----------
pptx.writeFile({ fileName: process.argv[2] || 'sunum.pptx' }).then((fileName) => {
  console.log('yazildi:', fileName);
}).catch((err) => {
  console.error('HATA:', err);
  process.exit(1);
});
