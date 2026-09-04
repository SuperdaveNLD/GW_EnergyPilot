# GW EnergyPilot-handleiding

Deze handleiding helpt je van een veilige eerste ingebruikname naar normaal
dagelijks gebruik van het ingebouwde EnergyPilot-dashboard in Home Assistant.

[English user guide](USER_GUIDE.md) · [Projectoverzicht](../README.md) ·
[Probleem melden](https://github.com/SuperdaveNLD/GW_EnergyPilot/issues)

> GW EnergyPilot kan aanzienlijke laad-, ontlaad- en netvermogens aansturen.
> Laat **Automatische regeling UIT** totdat je voor jouw installatie alle
> meetwaarden, tekens, EMHASS-uitgangen en de reactie van de omvormer hebt
> gecontroleerd.

## Wat EnergyPilot doet

EnergyPilot brengt vier taken samen die anders over losse schermen en
automatiseringen verspreid zijn:

1. Het leest de GoodWe ETA-G20 lokaal uit, of gebruikt optioneel SEMS+ Beta
   voor telemetrie.
2. Het laat een bestaande EMHASS-installatie een plan berekenen en publiceren.
3. Het past veiligheidsregels en de gekozen Battery-, Grid- of Hybrid-strategie
   toe.
4. Het stuurt de resulterende EMS-modus en doelwaarde lokaal via Modbus naar de
   omvormer en controleert daarna de teruglezing.

SEMS+ wordt nooit voor regeling gebruikt. EMHASS blijft eigenaar van het plan
en moet apart zijn geïnstalleerd.

## Benodigdheden

- Home Assistant 2026.8 of nieuwer en HACS;
- een ondersteunde GoodWe ETA-G20 die via Modbus TCP bereikbaar is;
- een vast IP-adres of DHCP-reservering voor de omvormer;
- een draaiende en geconfigureerde EMHASS-installatie voor optimalisatie;
- een prijsbron wanneer je prijsbewust wilt plannen.

De primair geteste omvormer is de **GoodWe GW15K-ETA-G20**. Controleer andere
ETA-G20-modellen en firmware zorgvuldig.

Gebruikelijk zijn poort `502` en Unit ID `247`, maar gebruik de waarden van jouw
omvormer. Laat bij voorkeur niet twee integraties tegelijk dezelfde
Modbus-interface continu pollen of aansturen.

## Installeren en verbinden

1. Installeer en start eerst EMHASS. Schakel automatisch starten en watchdog
   in.
2. Voeg deze GitHub-repository in HACS toe als **Integratie**, installeer GW
   EnergyPilot en herstart Home Assistant.
3. Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen**, kies
   **GW EnergyPilot** en vul de omvormerverbinding in.
4. Open **GW EnergyPilot** in de zijbalk van Home Assistant.
5. Laat **Automatische regeling UIT**.
6. Open het tandwiel en stel **ENERGYPILOT**, **EMHASS** en **GOODWE** in.
   Gebruik **EV** en **PV** alleen wanneer die voor jouw installatie nodig zijn.

Met de **?** in de bovenbalk open je altijd de handleiding. Bij een Nederlandse
Home Assistant-taal opent deze Nederlandse versie; anders opent de Engelse.

Zie [EMHASS instellen](EMHASS_SETUP.md) voor de volledige technische
parametermapping.

## Veilig valideren vóór automatisch regelen

Schakel Automatische regeling pas in als elk onderdeel hieronder klopt.

### 1. Controleer de live energiewaarden

Vergelijk het EnergyPilot-dashboard met de omvormer en elektriciteitsmeter:

- PV-opwek is aannemelijk;
- het huisverbruik verandert als je een bekend apparaat inschakelt;
- batterij-SOC komt overeen met de omvormer;
- batterijvermogen is **negatief tijdens laden** en **positief tijdens
  ontladen**;
- GoodWe-netvermogen is **negatief bij import** en **positief bij export**;
- fasestromen en temperaturen zijn aannemelijk wanneer ze beschikbaar zijn.

### 2. Controleer EMHASS

Druk op **Nu optimaliseren** en controleer dat:

- de optimizer gereed/succesvol meldt;
- `P_batt` een geldig getal is met het juiste batterijteken;
- `P_grid` geldig is wanneer je Grid of Hybrid gebruikt;
- Battery · Plan · Price een actueel/toekomstig plan toont en geen verzonnen
  nullen.

Let op: EMHASS en de GoodWe-meter gebruiken voor het net tegengestelde tekens:

```text
EMHASS P_grid: positief = geplande import, negatief = geplande export
GoodWe-meter:  negatief = werkelijke import, positief = werkelijke export
```

### 3. Test één handmatig commando

Laat Automatische regeling uit, kies een laag en veilig vermogen en voer één
handmatige EMS-actie uit. Controleer in Controller of modus, doelwaarde en
teruglezing kloppen. Stop wanneer de omvormer anders reageert dan verwacht.

### 4. Schakel automatisch regelen in

Kies de gewenste strategie, schakel **Automatische regeling** in en volg de
eerste planstap. Controller hoort uit te leggen welke planwaarde tot de actieve
GoodWe-modus heeft geleid.

## Rondleiding door het dashboard

- **Live energiestroom** toont richting en vermogen van PV, huis, net en
  batterij.
- **Battery** toont SOC, actueel batterijvermogen en het gekozen batterijbeleid.
- **Controller** toont eigenaarschap, strategie, GoodWe EMS-modus, doelwaarde
  en bewijs van teruglezing.
- **Battery · Plan · Price** vergelijkt gepland batterijvermogen, werkelijk
  batterijvermogen en marktprijs over 12, 24 of 36 uur.
- **Uitvoeringsgeschiedenis** bewaart planbeslissingen,
  veiligheidsoverschrijvingen, schrijfacties en teruglezing.
- **Verbindingsstatus** bovenin vat Modbus, EV-lader en effectieve
  EV-coördinatie samen.
- **Layout & visibility** laat kaarten ordenen/verbergen en optionele bewegende
  energiedeeltjes inschakelen. De uit-stand en `reduced motion` stoppen die
  volledig.
- Het **tandwiel** opent alle instellingen; de **?** opent deze handleiding.

## Kies een automatische strategie

### Battery

Volgt rechtstreeks het geplande batterijvermogen. Een laadplan kiest GoodWe
modus 11, een ontlaadplan modus 12 en een neutraal plan modus 8 (Battery Hold).
Dit is de compatibiliteitskeuze zonder gevalideerde GoodWe-smartmeter.

### Grid

Volgt de geplande stroom op het netaansluitpunt. Import kiest modus 9, export
modus 10 en een netdoel rond nul modus 1 (GoodWe Auto/eigen verbruik). Gebruik
dit alleen met een werkende, correct getekende GoodWe-smartmeter.

### Hybrid

Hybrid bewaart eerst een expliciet neutraal batterijplan met Battery Hold. Bij
een niet-neutraal batterijplan volgt het `P_grid`: GoodWe Auto rond nul en
modus 9/10 buiten de net-deadband. Zo combineert Hybrid een bewuste
batterij-rustbeslissing met GoodWe's snelle lokale PCC-regeling.

De twee deadbands hebben elk één taak: Battery Hold wordt bepaald met `P_batt`;
GoodWe Auto met `P_grid`. Je vindt ze via tandwiel → **GOODWE**.

## Batterijprofielen

EnergyPilot heeft vijf beheerde profielen:

- **Mad-Steve** — grootste SOC-bereik en meest agressieve inzet;
- **Gold Rush** — sterke prijsreactie met meer weerstand tegen pendelen;
- **Chargegasm** — ruim bruikbaar bereik met lichte bescherming;
- **Balanced** — meer bescherming tegen hoge SOC, throughput en piekvermogen;
- **Battery Saver** — laagste gemiddelde SOC-doel en sterkste bescherming.

Een beheerd profiel past de minimale GoodWe-SOC en alle eigen
EMHASS-batterijvelden toe als één transactie met rollback. Met **Aangepast**
krijg je de SOC- en kosteninstellingen zelf terug. De profielen zijn transparante
optimalisatievoorkeuren, geen levensduurgarantie. Alle waarden staan in
[Battery Saver](BATTERY_SAVER.md).

## Planning en prijzen

EnergyPilot optimaliseert op lokale klokgrenzen van 15, 30 of 60 minuten; 15
minuten wordt aanbevolen. Tussen optimalisaties publiceert het de juiste stap
uit het actieve plan. Wanneer beide tegelijk nodig zijn, wint de nieuwe
optimalisatie en is er maar één publicatie voor die grens.

Het laatste officiële EMHASS-plan wordt als herstelkopie bewaard. Die wordt
alleen gebruikt zolang het plan nog geldig is en de live publicatie ontbreekt.
Een expliciet niet-gereed optimizerresultaat blijft leidend en de laatste
planregel wordt na afloop nooit doorgetrokken.

## EV-functies

**EV anti-discharge** voorkomt dat de thuisbatterij een ladende EV voedt. Een
echt laadplan voor de thuisbatterij blijft toegestaan. Deze functie bedient de
lader niet.

Optionele **EV load balancing** kan één instelbare stroomlimiet van de lader
aanpassen om de ingestelde huisaansluiting zacht te bewaken. Hiervoor gebruikt
EnergyPilot de GoodWe-fasestromen en een aparte terugmelding van toegewezen
laadstroom. Het is best-effort coördinatie, geen zekeringbeveiliging. Valideer
fasekeuze, aansluitwaarde, maximale stroom en terugmelding vóór inschakelen.
Zie [EV load balancing](EV_LOAD_BALANCING.md).

## Overzicht instellingen

| Onderdeel | Doel |
|---|---|
| **ENERGYPILOT** | Algemene integratie-, dashboard- en orchestratiekeuzes |
| **EV** | Laaddetectie, bereikbaarheidsbewaking, anti-discharge en load balancing |
| **EMHASS** | URL, planning, uitgangen, prijzen, load forecast en configuratiecontrole |
| **PV** | Uitsluitend-weergave van interne en externe PV-bronnen |
| **GOODWE** | Telemetriebron, omvormeridentiteit, strategie en deadbands |

De opgeslagen SEMS-inlogcode wordt nooit teruggestuurd naar de browser of een
diagnoserapport.

## Dagelijks gebruik

Controleer normaal gesproken drie dingen:

1. De verbindingsstatus bovenin is gezond.
2. Battery · Plan · Price bevat een logisch plan voor de komende uren.
3. Controller toont het verwachte eigenaarschap, de modus en de geverifieerde
   doelwaarde.

Gebruik **Nu optimaliseren** na een belangrijke prijs- of configuratiewijziging
als je niet op de volgende klokgrens wilt wachten. Zet Automatische regeling uit
vóór hardwaretests, wijzigingen in meettopologie of onderzoek naar een
onverwacht teken of energierichting.

## Problemen oplossen

| Probleem | Controleer |
|---|---|
| Geen live waarden | IP, poort/Unit ID, Modbus-bereikbaarheid, gekozen telemetriebron en dubbele pollers |
| SEMS+ niet bereikbaar | Internet, station/omvormerkeuze en tijdstempel; lokale regeling heeft een aparte status |
| Nu optimaliseren mislukt | EMHASS draait, de URL is bereikbaar vanuit Home Assistant, vereiste config is gesynchroniseerd en SOC/prijzen zijn beschikbaar |
| Plan zichtbaar maar regeling wacht | Optimizerstatus, verse geldige `P_batt` en voor Grid/Hybrid ook verse `P_grid` |
| Onverwachte import/export | Controleer eerst de tegengestelde net-tekens van EMHASS en GoodWe |
| EV-coördinatie onderbroken | De onlinebron van de lader is langer dan de wachttijd weg; controleer status en terugmelding |
| Instelling wordt niet opgeslagen | Lees de validatiemelding; een beheerd batterijprofiel vergrendelt bewust zijn eigen waarden |
| Dashboard lijkt oud na update | Herlaad de integratie/frontendcache en controleer de versiebadge |

Voor ondersteuning: open tandwiel → **LOG**, start debugregistratie, reproduceer
het probleem kort, stop de registratie en kopieer het rapport. De buffer staat
alleen in het geheugen en bevat geen inloggegevens. Voeg het rapport, de Home
Assistant-versie, het omvormer- en batterijmodel, firmware en
smartmeterinformatie toe aan een
[GitHub-issue](https://github.com/SuperdaveNLD/GW_EnergyPilot/issues).

## Veiligheid en grenzen

- GoodWe/BMS-beveiligingen en hardwarelimieten blijven leidend.
- Verander nooit registerbetekenissen zonder hardware- of fabrikantevidence.
- Een minimum-SOC wordt eerst lokaal geschreven en teruggelezen voordat de
  overeenkomende EMHASS-waarde wordt geaccepteerd.
- Permanente netboekhouding gebruikt consistente GoodWe-tellerparen; grafieken
  zijn geen facturatiemeter.
- SEMS+ blijft optionele Beta-telemetrie en is geen EMS-transport.
- EMHASS is een externe vereiste; EnergyPilot installeert of vervangt het niet.

Voor de exacte technische afspraken kun je verder lezen in
[Architectuur](ARCHITECTURE.md), [EMS-modi](EMS_MODES.md),
[EMHASS-planherstel](EMHASS_PLAN_RUNTIME.md) en
[Instellingen/beveiliging](SETTINGS.md).
