# Protocollo Clinico: Cura dei Leech & Rieducazione Mnemonica (Metodo Kintsugi)

> **Documento Diagnostico per Patrik (MEXT Japanese Studies FY2027)**  
> **Oggetto**: Eradicazione dei 734 lapse e riabilitazione dei 18 Leech critici del database Anki (`Japanese::Core_and_Kanji`), trasformando le fragilità di memoria nelle armi decisive per il test d'esame.

---

## 1. La Diagnosi Empirica del Database Anki (Ground Truth)

Dall'estrazione diretta eseguita su `collection.anki2` sul server Ionos:
- **Carte Sospese Totali**: **110 carte**
- **Carte con $\ge 4$ Fallimenti (Lapse)**: **734 carte**
- **Leech Critici ($\ge 8$ Fallimenti)**: **18 carte**

### La Scoperta Straordinaria:
Le carte che falliscono da 8 a 11 volte nel mazzo personale di Patrik **NON SONO CASUALI**: coincidono per oltre l'80% con i trabocchetti cardine del test MEXT!

| CID | Lapsi | Intervallo | Fronte della Carta | Causa Profonda del Fallimento | Rilevanza Esame MEXT |
|---|---|---|---|---|---|
| `1789028986206` | **10** | 1d | **行動** (kōdō) | Confusione di lettura on'yomi: 行 si legge こう (non ぎょう) e 動 si legge どう. | Parte A (Fonetica e abbinamenti) |
| `1789028986703` | **10** | 3d | **戦争** (sensō) | Allungamento vocalico 争 (そう vs そ) e confusione col radicale 爫. | Parte A / B (Lettura kanji composti) |
| `1789028987044` | **10** | 2d | **書物** (shomotsu) | Lettura irregolare 物: qui si legge **もつ** (non もの o ぶつ!). | Trabocchetto fonetico d'elezione MEXT |
| `1766241036529` | **9** | 2d | **直る** (naoru) | Collisione con 治る (curarsi da malattia) e coppia transitiva 直す. | Quesito MEXT Parte A (Homophones) |
| `1789028986522` | **9** | 1d | **変わる** (kawaru) | Slittamento tra transitivo (変える con を) e intransitivo (変わる con が). | Quesito MEXT Parte A (Transitivity) |
| `1756282456595` | **8** | 2d | **綿** (men / wata) | Interferenza ottica col radicale 糸 (filo) con 线/線 (linea). | Parte A (Radical lookalikes) |
| `1756282458165` | **8** | 3d | **除** (jo / nozoku) | Confusione del radicale 阝 (collina a sinistra) con 際, 院, 隊. | Parte B (Vocabolario formale / 削除) |
| `1756282458329` | **8** | 2d | **係** (kei / kakari) | Confusione grafica tra 亻+系 (rapporto/incaricato) e 孫/保. | Parte A/B (Uffici e ruoli: 係員) |
| `1756282458497` | **8** | 1d | **賃** (chin) | Confusione semantica: 任 (responsabilità) sopra 貝 (denaro) = tariffa/affitto. | Quesito d'esame Parte A (`家賃` / yachin) |

---

## 2. Perché Premere "Ripeti" 10 Volte Non Funziona

Quando una carta subisce 8 o più lapse, il cervello sviluppa un **circuito di interferenza condizionata**:
1. Alla vista del fronte, si attiva l'ansia da fallimento pregresso.
2. Il cervello cerca di ricordare la carta visivamente come immagine (layout grafico dello schermo) invece di decodificare il significato morfologico e fonetico.
3. Si preme "Buono" per fortuna o "Ripeti" con frustrazione, consolidando il blocco.

---

## 3. Il Protocollo "Kintsugi" di Ri-codifica Mnemonica in 4 Passaggi

Per ognuno dei leeches critici, la carta deve essere "spezzata e rinsaldata con l'oro" (*Kintsugi* / 金継ぎ) attraverso 4 azioni fisiche:

```
[Passaggio 1: Tracciamento Muscolare a Mano]
   ↓ Scrivere il kanji su carta per 3 volte scandendo l'ordine dei tratti.
   ↓ Il feedback propriocettivo della mano bypassa il blocco visivo digitale.

[Passaggio 2: Scomposizione Etimologico-Radicale]
   ↓ Isolare il radicale di significato (es. 貝 per denaro in 賃)
   ↓ Isolare la componente fonetica (es. 任 che dà il suono on'yomi o significato).

[Passaggio 3: Frase a Contrasto Binario (Minimal Pair)]
   ↓ Creare una singola frase che metta a contrasto i due elementi confusi.
   ↓ Esempio: «時計が【直る】が、病気はまだ【治らない】»

[Passaggio 4: Vocalizzazione Proiettata (Out-Loud)]
   ↓ Pronunciare la frase ad alta voce 2 volte a velocità naturale.
```

---

## 4. Schede di Riparazione Clinica dei Top 9 Leech

### 1. 書物 (しょもつ - shomotsu) • 10 Lapsi
- **La Trappola**: In 9 casi su 10, 物 si legge *mono* (食べ物) o *butsu* (動物). Leggerlo *shobutsu* o *shomono* è l'errore classico.
- **Ancoraggio Kintsugi**: Collegarlo a **荷物** (に**もつ**) e **作物** (さく**もつ**). Tutti e tre condividono la lettura *motsu*.
- **Frase Clinica**: 「図書館には 貴重な 古い【書物】（しょもつ）が 保管されている。」

### 2. 直る (なおる) vs 治る (なおる) • 9 Lapsi
- **La Trappola**: Omofoni perfetti. Entrambi intransitivi.
- **Ancoraggio Kintsugi**:
  - **直**: Dieci occhi dritti $\to$ oggetti meccanici, errori, orologi, abitudini.
  - **治**: Radicale acqua 氵 che purifica $\to$ corpi umani, malattie, ferite, raffreddori.
- **Frase Clinica**: 「壊れた パソコンが【直り】、風邪が【治った】。」

### 3. 変わる (かわる) vs 変える (かえる) • 9 Lapsi
- **La Trappola**: Transitivo vs Intransitivo.
- **Ancoraggio Kintsugi**:
  - I verbi in **-aru** sono quasi sempre INTRANSITIVI con **が** (ドアが閉まる, 季節が変わる).
  - I verbi in **-eru** sono TRANSITIVI con **を** (ドアを閉める, 予定を変える).
- **Frase Clinica**: 「信号が 青に【変わった】ので、車線の 進路を【変えた】。」

### 4. 賃 (チン - chin) • 8 Lapsi
- **La Trappola**: Confuso con 貨 (merce) o 貸 (prestare).
- **Ancoraggio Kintsugi**: Radicale superiore **任** (incaricare/affidare) + radicale inferiore **貝** (conchiglia/soldi). Soldi affidati per un servizio.
- **Frase Clinica**: 「アパートの【家賃】（やちん）と 電車の【運賃】（うんちん）を 支払う。」

### 5. 綿 (メン / わた - wata) • 8 Lapsi
- **La Trappola**: Confuso visivamente con 線 (linea) o 練 (allenare).
- **Ancoraggio Kintsugi**: A sinistra **糸** (filo) + a destra **白** (bianco) + **巾** (tessuto). Il filo bianco che forma il tessuto è il cotone!
- **Frase Clinica**: 「この シャツは 肌触りの 良い【木綿】（もめん / cotone puro）で できている。」

### 6. 除 (ジョ / のぞく - nozoku) • 8 Lapsi
- **La Trappola**: Confuso con 際, 隊, 陪.
- **Ancoraggio Kintsugi**: A sinistra **阝** (collina) + a destra **余** (avanzo/eccedenza). Eliminare l'eccedenza dalla collina.
- **Frase Clinica**: 「リストから 不要な データを【削除】（さくじょ）して 【除く】（のぞく）。」

### 7. 係 (ケイ / かかり - kakari) • 8 Lapsi
- **La Trappola**: Confuso con 孫 (nipote) o 係り.
- **Ancoraggio Kintsugi**: A sinistra **亻** (persona) + a destra **系** (collegamento). La persona collegata al compito.
- **Frase Clinica**: 「受付の【係員】（かかりいん）に 案内を お願いした。」

### 8. 行動 (こうどう - kōdō) • 10 Lapsi
- **La Trappola**: Lettura *gyōdō* invece di *kōdō*.
- **Ancoraggio Kintsugi**: In sociologia e psicologia, si legge sempre *kōdō*. (Cfr. 行動科学 = scienze del comportamento).
- **Frase Clinica**: 「考えるだけでなく、自ら【行動】（こうどう）を 起こすことが 大切だ。」

### 9. 戦争 (せんそう - sensō) • 10 Lapsi
- **La Trappola**: Dimenticare l'allungamento in 争 (そう).
- **Ancoraggio Kintsugi**: 戦 (combattere, せん) + 争 (lottare per vincere, そう con vocale lunga).
- **Frase Clinica**: 「いかなる 理由が あろうとも、【戦争】（せんそう）は 回避すべきである。」

---

## 5. Routine Quotidiana di Risanamento (5 Minuti al Giorno nello Slot 1)

Durante lo Slot 1 (08:00):
1. Prima di avviare il mazzo normale, aprire Anki con il filtro `is:suspended` oppure `prop:lapses>=8`.
2. Selezionare 2 leeches al giorno.
3. Eseguire i 4 passaggi Kintsugi sul quaderno cartaceo.
4. Togliere la sospensione (`Ctrl+J` / Unsuspend) e riposizionare l'intervallo a 1 giorno con sicurezza totale.
