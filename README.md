
# Golf Träningslogg – Streamlit Prototyp

En enkel mobilvänlig webb-app för att logga golfträning med autodatum, stora knappar och statistik.
Byggd för att köras på **Streamlit Community Cloud**.

## Funktioner
- Logga pass: Range / Närspel / Bana
- Stora knappar (t.ex. ➕ Mitt i, ➕ Chip inom 2m, ➕ Kortputt i hål)
- Autodatum (dagens datum sparas automatiskt)
- Exportera CSV
- Statistik: Träffbild, Carry per klubba, Kortputtar per dag

## Så här deployar du (enkelt från mobilen)
1. Öppna **GitHub** (appen eller webben) och skapa ett nytt repo, t.ex. `golf-traningslogg`.
2. Ladda upp dessa filer:
   - `app.py`
   - `requirements.txt`
3. Gå till **https://share.streamlit.io** och välj **Deploy an app**.
4. Koppla ditt GitHub-konto, välj ditt repo och filen `app.py`.
5. Klicka **Deploy** → Du får en länk (t.ex. `https://dittnamn.streamlit.app`) som du kan spara på hemskärmen.

**Obs:** Appen sparar data i `data/logg.csv` på servern. På Streamlit Cloud ligger filen kvar mellan körningar,
men om du gör en ny deploy kan loggen nollställas. Exportera CSV regelbundet via knappen i sidomenyn.
