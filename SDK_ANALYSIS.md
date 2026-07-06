# DJI Thermal SDK v1.8 elemzes

## Tartalom

Az SDK konyvtar: `./dji_thermal_sdk_v1.8_20250829`.

Fontos elemek:

- `tsdk-core/api/dirp_api.h`: a fo C API header.
- `tsdk-core/api/dirp_wrapper.h`: vendor API wrapper definicio.
- `tsdk-core/lib/windows/release_x64`: 64 bites Windows DLL-ek es import libek.
- `utility/bin/windows/release_x64`: kesz parancssori eszkozok, peldaul `dji_irp.exe`, `dji_irp_omp.exe`, `dji_ircm.exe`.
- `sample/dji_irp.cpp`: egy fajlos R-JPEG meresi es feldolgozasi minta.
- `dataset/M3T`: Mavic 3 Thermal mintakepek.
- `doc/index.html` es `doc/html`: Doxygen API referencia.

## Binarisok es fuggosegek

Windows x64 alatt a hasznalt konyvtar:

`dji_thermal_sdk_v1.8_20250829/tsdk-core/lib/windows/release_x64`

Ebben talalhato:

- `libdirp.dll`, `libdirp.lib`: fo DIRP API.
- `libv_iirp.dll`, `libv_hirp.dll`, `libv_girp.dll`, `libv_dirp.dll`: termek/vendor specifikus feldolgozo modulok.
- `MicroTA_Release_x64.dll`, `MicroJPEG_Release_x64.dll`, `MicroIA_Release_x64.dll`.
- `libexif.dll`, `libiconv-2.dll`, `libintl-8.dll`.
- `libv_list.ini`: a vendor modulok listaja.

Az alkalmazas `os.add_dll_directory()` hivassal adja hozza ezt a konyvtarat a DLL keresesi uthoz.

## Hasznalhato API

A dokumentalt, valoban letezo fuggvenyek kozul a homersekleti matrixhoz ezek szuksegesek:

- `dirp_create_from_rjpeg(const uint8_t *data, int32_t size, DIRP_HANDLE *ph)`
- `dirp_get_rjpeg_resolution(DIRP_HANDLE h, dirp_resolution_t *resolution)`
- `dirp_get_measurement_params(DIRP_HANDLE h, dirp_measurement_params_t *measurement_params)`
- `dirp_set_measurement_params(DIRP_HANDLE h, const dirp_measurement_params_t *measurement_params)`
- `dirp_measure_ex(DIRP_HANDLE h, float *temp_image, int32_t size)`
- `dirp_destroy(DIRP_HANDLE h)`

A `dirp_measure_ex` FLOAT32 Celsius kimenetet ad. A gyari dokumentacio szerint a `dirp_measure` INT16 kimenete 0.1 Celsius felbontasu, de a projekt a FLOAT32 API-t hasznalja.

## Parancssori validacio

Lefuttatott gyari minta:

```bat
dji_irp.exe -s .\dji_thermal_sdk_v1.8_20250829\dataset\M3T\DJI_0001_R.JPG -a measure -o .\tmp_measure_float.raw --measurefmt float32
```

Eredmeny:

- DIRP API version: `0x13`, magic: `relver`
- M3T kepmeret: `640 x 512`
- A meres sikeres volt, a kimenet FLOAT32 raw matrix.

## Architektura

Az SDK hasznalata `ctypes` wrapperben tortenik: `src/thermal/dji_sdk_wrapper.py`.

Az SDK hivast globalis `threading.Lock` vedi, mert a mellekelt dokumentacio nem allitja egyertelmuen, hogy a DIRP handle-ek es vendor DLL-ek parhuzamos hasznalata szalbiztos. A GUI emiatt reszponziv marad, de egy worker egyszerre egy SDK merest futtat.

## Korlatozasok

- A README a tamogatott DJI kamerak kozott H20T/H20N/XT S/M2EA/M30T modelleket sorol, de a csomag tartalmaz M3T es M3TD mintakepeket is. A helyi teszt M3T mintaval sikeres volt.
- A meresi parameter tartomanyokat a sample M3T kepnel az SDK adja: tavolsag `[1,25]`, paratartalom `[1,100]`, emisszivitas `[0.1,1]`, ambient `[-40,80]`, reflection `[-40,100]`. Emiatt az alkalmazas alap tavolsaga 25 m, mert ezt a helyi SDK elfogadja.
- OCR nincs hasznalva, a homerseklet nem a 8 bites JPEG pixelbol keszul.

