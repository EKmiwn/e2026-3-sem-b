# Kravspecifikation – Digital patientregistrering (Bispebjerg Akutmodtagelse)

> Konverteret til markdown fra `kravspif.pdf`. Teksten er gengivet som i originaldokumentet.

## 1. Projektets formål

Formålet er at optimere arbejdsgangene på Bispebjerg Akutmodtagelse ved at digitalisere indsamlingen af patientoplysninger.

Løsningen skal:

- Mindske patienternes oplevede ventetid.
- Frigøre tid for sygeplejersker og læger.
- Reducere gentagelser i kommunikationen.
- Sikre hurtigere adgang til relevante undersøgelser.
- Skabe mere sammenhængende patientforløb.

## 2. Interessenter

### Primære interessenter

- Patienter
- Sygeplejersker
- Læger

### Sekundære interessenter

- Hospitalets ledelse
- Region Hovedstaden
- Akuttelefonen 1813
- Røntgenafdelingen
- IT-afdelingen

## 3. Brugere

### Patienter

- Registrerer symptomer før eller ved ankomst.
- Kan følge status på deres forløb.

### Sygeplejersker

- Ser patientdata før den første samtale.
- Kan prioritere patienter hurtigere.

### Læger

- Får adgang til patientens symptomer og historik.
- Kan vurdere behov for undersøgelser tidligere.

## 4. Begrænsninger

- Systemet må ikke erstatte faglig vurdering.
- Skal følge GDPR-regler.
- Skal kunne integreres med eksisterende hospitals-IT.
- Skal være brugervenligt for personer med begrænset digital erfaring.

## 5. Definitioner

| Begreb | Definition |
|---|---|
| Triage | Prioritering af patienter efter alvorlighed |
| Symptomregistrering | Indtastning af symptomer og helbredsoplysninger |
| Patientprofil | Samlet patientinformation brugt i behandlingen |

## 6. Antagelser

- De fleste patienter har adgang til smartphone.
- Personalet har adgang til computer eller tablet.
- Hospitalet ønsker øget digitalisering.
- Patienter er villige til at registrere oplysninger digitalt.

# Funktionelle krav

## 7. Scope for arbejdet

Projektet omfatter:

- Registrering af symptomer.
- Deling af oplysninger mellem personale.
- Understøttelse af hurtigere visitation.

Projektet omfatter ikke:

- Selve behandlingen.
- Diagnosestillelse.
- AI-baseret medicinsk rådgivning.

## 8. Produktets scope

Systemet skal fungere som en webbaseret platform, der forbindes med akutmodtagelsens eksisterende systemer.

## 9. Funktionelle krav

### FR1

Patienten skal kunne indtaste:

- Symptomer
- Skadetype
- Smertegrad
- Medicin
- Allergier

### FR2

Patienten skal modtage et unikt registreringsnummer.

### FR3

Sygeplejersker skal kunne se de registrerede oplysninger.

### FR4

Læger skal kunne se de registrerede oplysninger.

### FR5

Systemet skal gemme patientdata sikkert.

### FR6

Systemet skal kunne sende information videre til relevante afdelinger.

### FR7

Personale skal kunne markere behov for undersøgelser som:

- Røntgen
- Blodprøver
- CT-scanning

### FR8

Patienten skal kunne opdatere oplysninger ved behov.

### FR9

Systemet skal kunne vise patientens status i forløbet.

Eksempel:

- Registreret
- Venter på sygeplejerske
- Undersøgelse bestilt
- Venter på læge

# Non-funktionelle krav

## 10. Look & Feel

- Simpelt design.
- Store knapper.
- Hospitalets farver.
- Letlæselig tekst.

## 11. Brugervenlighed

- Kunne bruges uden oplæring.
- Maksimalt 5 minutter at udfylde.
- Understøtte dansk og engelsk.

## 12. Performance

- Data skal gemmes inden for 3 sekunder.
- Systemet skal kunne håndtere mindst 500 samtidige brugere.
- Oppetid på minimum 99 %.

## 13. Driftskrav

- Webbaseret løsning.
- Tilgængelig 24/7.
- Virke på mobil, tablet og computer.

## 14. Vedligeholdelse

- Opdateringer skal kunne foretages uden længere nedetid.
- Fejl skal kunne spores via logning.

## 15. Sikkerhed

- GDPR-compliant.
- Krypteret datatransmission.
- Login til sundhedspersonale.
- Rollebaseret adgang.

## 16. Kulturelle krav

- Skal kunne anvendes af personer med forskellig sproglig baggrund.
- Letforståeligt sprog.
- Understøtte tilgængelighed.

## 17. Lovkrav

- GDPR.
- Databeskyttelsesloven.
- Sundhedsloven.
- NIS2-krav til cybersikkerhed.

# Open Issues

## 18. Åbne spørgsmål

- Skal patienten kunne registrere sig hjemmefra?
- Skal løsningen integreres med 1813?
- Skal systemet kunne foreslå undersøgelser automatisk?

# Risici

## 23. Risici

- Ældre patienter kan have svært ved at bruge løsningen.
- IT-nedbrud kan påvirke patientflowet.
- Manglende integration med eksisterende systemer.
- Datasikkerhedsproblemer.

# Forventede gevinster

- Mindre dobbeltarbejde for sygeplejersker og læger.
- Kortere ventetid for patienter.
- Hurtigere visitation.
- Bedre patientoplevelse.
- Mere effektiv ressourceudnyttelse.
