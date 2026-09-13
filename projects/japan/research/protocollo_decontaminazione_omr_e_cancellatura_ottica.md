# 📐 Protocollo: Decontaminazione OMR & Cancellatura Ottica MEXT

**Focus**: Neutralizzazione del rischio di invalidazione per "Doppia Marcatura" (*Jūfuku Kaitō*) sui fogli ottici OMR.  
**Hardware Bersaglio**: Scanner ottici ad infrarossi ad alto contrasto impiegati dal Ministero e dalle sedi consolari.

---

## 1. La Fisica degli Scanner Ottici OMR

I fogli di risposta MEXT vengono scansionati tramite lettori OMR (*Optical Mark Recognition*) tarati su lunghezze d'onda nel visibile e vicino infrarosso:
- Il sensore misura la **densità ottica relativa** (riflettanza) all'interno dell'ellisse.
- Una casella riempita a matita 2B produce un assorbimento di luce $\ge 75\%$.
- Una casella bianca pulita riflette $\ge 90\%$ della luce.
- **La Soglia di Riconoscimento (*Threshold*)**: Qualsiasi casella che presenti una densità ottica residua $\ge 18–20\%$ viene registrata come **marcata**.

> **Il Rischio di Doppia Marcatura**: Se il candidato cambia idea, cancella sommariamente una casella e ne annerisce un'altra sulla stessa riga, la grafite residua smossa ma non asportata supera la soglia del 20%. Lo scanner registra **due risposte simultanee** e assegna automaticamente **ZERO punti** al quesito per squalifica formale.

---

## 2. Selezione dell'Equipaggiamento Tattico di Cancellazione

Non utilizzare MAI la gommina posta sul retro delle matite o gomme da cancellare commerciali economiche a base di gomma naturale (che degradano e lasciano patine unte sul foglio).

| Strumento | Modello Raccomandato | Proprietà Fisico-Chimica |
| :--- | :--- | :--- |
| **Gomma Polimerica Primaria** | **Tombow MONO Plastic Eraser** (o **Pentel Ain Black**) | Matrice polimerica sintetica che ingloba le micro-particelle di grafite nei trucioli senza strofinamento untuoso. |
| **Gomma di Precisione Chirurgica** | **Tombow MONO Zero** (punta tonda 2.3mm a penna) | Permette di cancellare una singola ellisse OMR senza toccare le guide millimetriche o le caselle adiacenti. |
| **Pennellino Tascabile Morbido** | Pennello a setole morbide piatte da disegno | Rimuove i residui di gomma dal foglio senza strisciare la mano sulla grafite fresca (zero sbavature). |

---

## 3. Protocollo di Cancellatura a 3 Fasi (Zero-Residuo)

1. **Fase 1: Asportazione Meccanica Monodirezionale**:
   Non effettuare movimenti circolari o oscillatori rapidi. Applicare la gomma Tombow Mono Zero con passaggi leggeri **esclusivamente dall'alto verso il basso**, sollevando la gomma ad ogni passata.
2. **Fase 2: Asportazione Residui senza Contatto Manuale**:
   Spazzolare via i trucioli con il pennellino a setole morbide. È **tassativamente vietato** soffiare sul foglio (rischio di micro-gocce di saliva che alterano la carta) o strofinare il palmo della mano (la pressione spalmerebbe la polvere di grafite sulla griglia).
3. **Fase 3: Ispezione della Bianchezza Ottica**:
   Verificare controluce che la carta sia tornata al bianco vergine. Se permane un'ombra grigia, eseguire 2 passate delicate con la gomma polimerica pulita. Solo a questo punto procedere all'annerimento della nuova scelta con matita 2B.
