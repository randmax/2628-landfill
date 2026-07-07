# Térmonitor-thermal

Python/PySide6 asztali alkalmazás DJI radiometrikus R-JPEG képek feldolgozására. A cél a szeméttelepi termikus felmérések gyors átnézése, a legmelegebb ROI automatikus megtalálása, WebODM radiometrikus TIFF export és rangsorolt CSV statisztika.

## Inditas

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Gyors SDK teszt:

```bat
python tools/test_single_rjpeg.py dji_thermal_sdk_v1.8_20250829\dataset\M3T\DJI_0001_R.JPG
```

## Projekt szerkezet

- `main.py`: PySide6 inditopont.
- `src/thermal`: DJI SDK wrapper, ROI algoritmus, palettas megjelenites.
- `src/gui`: foablak, kepnezegeto, beallitopanel, talalati tabla.
- `src/metadata`: ExifTool/Pillow metaadat olvasas.
- `src/storage`: JSON projektmentes, cache, CSV export.
- `src/workers`: QThread worker.
- `tests`: SDK-tol fuggetlen unit tesztek.
- `config/default_settings.json`: alapbeallitasok.
- `SDK_ANALYSIS.md`: helyi SDK feltarasi jegyzet.

## DJI SDK

Az SDK helye: `./dji_thermal_sdk_v1.8_20250829`.

A wrapper a Windows x64 DLL-eket hasznalja:

`dji_thermal_sdk_v1.8_20250829/tsdk-core/lib/windows/release_x64`

A homersekleti matrixot a dokumentalt `dirp_measure_ex` API allitja elo FLOAT32 Celsius ertekekkel. A GUI es a CLI nem a palettazott JPEG pixelbol szamit homersekletet.

## Hasznalat

1. Kattints a `Munkakönyvtár kiválasztása` gombra.
2. A program megkeresi a JPG/JPEG képeket. Ha a munkakönyvtár RGB és thermal almappákat is tartalmaz, akkor csak a termál képek kerülnek a feldolgozási listába, az azonos sorszámú RGB kép pedig párosítva lesz velük.
3. Allitsd be a ROI meretet, stride-ot es a rangsorolasi metrikat.
4. Inditsd az `Aktualis kep feldolgozasa` vagy `Osszes kep feldolgozasa` muveletet.
5. A talalatok a jobb oldali `Talalatok` fulon rendezhetok.
6. `CSV exportalasa` ket fajlt keszit az `output` konyvtarba:
   - `thermal_results_sorted.csv`
   - `thermal_hotspots_sorted.csv`

## RGB és termál kép-párosítás

A `Munkakönyvtár kiválasztása` gombbal olyan gyökérkönyvtár is megadható, amelyben például `M3T_RGB` és `M3T_T` almappa van. A program a DJI fájlnévben lévő négyjegyű képsorszám alapján párosít, ezért akkor is megtalálja az RGB párt, ha a thermal és RGB timestamp egy másodperccel eltér.

A `Hőkép / RGB nézet váltása` gombbal az aktuális termál kép és a hozzá tartozó RGB kép között lehet váltani. A feldolgozás, a WebODM export és a találati lista továbbra is a radiometrikus hőkameraképekkel dolgozik.

## WebODM radiometrikus export

A `Feldolgozas -> WebODM radiometrikus TIFF export` menupont a DJI R-JPEG kepekbol egycsatornas `float32` TIFF fajlokat keszit. A TIFF pixelertekei Celsius fokok, tehat nem 8 bites palettazott kepbol keszulnek.

Az export kimenete:

- `*_thermal_celsius_float32.tif`: radiometrikus homersekleti TIFF.
- `webodm_radiometric_manifest.csv`: forras, kimenet, min/max/atlag homerseklet, GPS adatok.
- `webodm_geo.txt`: EPSG:4326 georeferencia sidecar a TIFF fajlnevekkel.

Ha az ExifTool elerheto, a program megprobalja az eredeti R-JPEG metaadatait is atmasolni a TIFF fajlokra.

## ROI algoritmus

Az atlaghomerseklet szerinti kereses integralkeppel keszul, nem egymasba agyazott Python ciklussal. A `p95` es `max` rangsorolas `sliding_window_view` alapjan vektorizalt NumPy muveleteket hasznal. A NaN es Inf pixelek nem szamitanak ervenyesnek.

A `Termal GSD` beallitas a radiometrikus hokamera pixeleire vonatkozik, nem az RGB kamera vagy ortofoto GSD-jere. Ezt hasznalja a program a ROI meret meterbe valtasahoz es a ROI kozep GPS becslesehez.

## Metaadatok

Ha az `exiftool` elerheto a PATH-ban, a program konyvtarszinten egy kozos JSON hivasban olvassa a metaadatokat. ExifTool nelkul Pillow fallback fut, kevesebb mezovel. Hianyzo GPS adat nem allitja le a feldolgozast.

## Cache es projekt

A cache kulcs tartalmazza a fajl meretet, modositasi idejet, radiometrikus beallitasokat, ROI beallitasokat es SDK verzio markert. Minden sikeres kep utan autosave keszul: `output/autosave_project.json`.

## Tesztek

```bat
pytest
```

Az SDK-tol fuggo mereshez kulon CLI van, a unit tesztek fake/adatmatrix alapon futnak.

## Gyakori hibak

- `A DJI SDK nem toltheto be`: ellenorizd, hogy a `dji_thermal_sdk_v1.8_20250829` konyvtar a projekt gyokereben van.
- `dirp_create_from_rjpeg sikertelen`: a fajl nem tamogatott vagy nem DJI radiometrikus R-JPEG.
- ROI hiba: a ROI nem lehet nagyobb a 640x512 vagy aktualis kepmeretnel.
- ExifTool hianyzik: metaadat mezok hianyozhatnak, de a feldolgozas mehet tovabb.
