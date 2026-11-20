# CraftBeerPi 4 voor Home Assistant

HACS-integratie die CraftBeerPi 4 **rechtstreeks via de REST-API** uitleest en bedient. Geen MQTT en geen extra plugin in CBPi nodig.

## Wat je krijgt
- **Vergisters**: temperatuur, doeltemperatuur, brouwsel, actieve stap (met alle stappen als attribuut), eindtijd van de stap, SG (als `sensor2` is ingesteld), verwarming/koeling/regeling-actief, regeling aan/uit, doel instellen, knoppen volgende stap / pauzeren / start.
- **Alcohol**: vul per vergister *Start-SG* en *Eind-SG* in (CBPi bewaart die niet; HA onthoudt ze) en kies eventueel de *SG-bron* (een iSpindel). Je krijgt *Alcohol (nu)*, *Alcohol (eind)* en *Vergistingsgraad*, met de formule (OG − SG) × 131,25.
- **Ketels**: temperatuur, doel instellen, verwarming, regeling.
- **Actoren**: schakelaars (pompen, kleppen, relais).
- **Alle CBPi-sensoren** (OneWire, iSpindel SG/Plato/batterij/temperatuur, ESPHome, …) als eigen sensor.

## Installeren
1. HACS → drie puntjes → *Aangepaste repositories* → `https://github.com/arcidodo/ha-craftbeerpi`, categorie *Integratie*.
2. Download, herstart Home Assistant.
3. Instellingen → Apparaten & services → *Integratie toevoegen* → **CraftBeerPi 4** → adres invullen.

Verversen kan onder *Configureren* (standaard 15 s).
