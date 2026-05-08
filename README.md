# DTI Interaktiivne Robot: Prototüüp "Quizmaster"

Käesolev repositoorium sisaldab Tallinna Ülikooli Digitehnoloogiate Instituudi (DTI) bakalaureusetöö raames arendatud sotsiaalse roboti prototüübi tehnilist dokumentatsiooni, tarkvara ja disainifaile. Projekti eesmärk on luua interaktiivne vahend, mis tutvustab IKT-valdkonda läbi mängustatud viktoriini ja füüsilise preemiamehhanismi.

## Repositooriumi struktuur

Süsteem on jaotatud neljaks põhivaldkonnaks, mis vastavad repositooriumi juurkataloogidele:

- **[/CAD](./CAD)** – Roboti korpuse ja mehaaniliste detailide mudelid (Solid Edge 2024).
  - `assembly/` – Seadme koostefailid (.par).
  - `stl/` – 3D-printimiseks valmis detailid.
  - `pleksi_loige.dft` – Joonis pleksiklaasi CNC- või laserlõikuse jaoks.
- **[/Fritzing](./Fritzing)** – Elektroonika komponentide ühendusskeem.
- **[/Lähtekood](./Lähtekood)** – Süsteemi tarkvaraline arhitektuur.
  - `esp32/` – Alamkontrolleri tarkvara (C++) servomootorite ja LED-ide juhtimiseks.
  - `frontend/` – Veebipõhine kasutajaliides (HTML/JS/CSS).
  - `main.py` – Kesksüsteemi loogika (Python/FastAPI).
  - `questions.json` – Muudetav viktoriini küsimuste baas.
- **[/Fotod](./Fotod)** – Visuaalne dokumentatsioon arendusprotsessist ja riistvara komponentidest.

## Tehniline teostus

### Põhifunktsioonid

- **Autonoomne tuvastus:** mmWave radari abil tajub robot lähenevaid inimesi ja algatab interaktsiooni.
- **Mängustatud viktoriin:** Interaktsioon toimub 7" ekraani ja taktiilset tagasisidet pakkuvate arkaadnuppude abil.
- **Mehaaniline väljastus:** Servomootoritega juhitud kaheastmeline premeerimissüsteem maiustuste väljastamiseks.
- **Multimeedia:** Animeeritud silmad ja sünteesitud eestikeelne kõne (TTS).

### Riistvaraline arhitektuur

Süsteem kasutab hajutatud arvutusmudelit:

- **Keskarvuti:** Raspberry Pi 4B - tegeleb backendi, frontendi, multimeedia ja anduritega.
- **Alamkontroller:** NodeMCU ESP32 - juhib servomootoreid ja LED-ribasid.
- **Toide:** X728 UPS HAT - stabiilse voolu tagamiseks ja `power_monitor.py` energiatarbe halduseks.
- **Signaali terviklikkus:** Kasutatud on loogikanivoo muundurit ja LED-ribade andmeliinidel 330 Ω takisteid.

### Disain ja valmistamine

Kõik detailid on modelleeritud **Solid Edge 2024** tarkvaraga. Valmistamisel on kasutatud 3D-printimise tehnoloogiat PLA plast filamendiga ja pleksiklaasi CNC-lõikust.

## Kasutamine

1.  **Riistvara:** Pane süsteem kokku järgides [/Fritzing](./Fritzing) kataloogis olevat elektriskeemi.
2.  **Süsteemi seadistamine:**
    - Paigalda vajalikud Pythoni teegid: `pip install -r requirements.txt`.
    - Laadi `esp32/` kood ESP32 mikrokontrollerisse kasutades selleks Arduino IDE.
    - Ühenda X728 UPS HAT autoboot viikudele "jumper".
3.  **Käivitamine:** Käivita kesksüsteem käsuga `python main.py`. Pärast toite ühendamist ja nupu vajutust käivitub roboti autonoomne režiim ning ootab interaktsiooni.

## Litsents

- **Tarkvara** ([/Lähtekood](./Lähtekood)): [MIT litsents](https://opensource.org/licenses/MIT).
- **Disain ja skeemid** ([/CAD](./CAD), [/Fritzing](./Fritzing)): [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

## Autorid

- **Ander Aava & Taavi Vendt**
- **Juhendajad:** Kalle Kivi ja Triinu Jesmin
- **Tehniline konsultant:** Tanel Toova

---

_Tallinna Ülikool, Digitehnoloogiate Instituut (2026)_
