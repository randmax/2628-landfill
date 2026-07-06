from src.thermal.webodm_exporter import WebOdmExportResult, WebOdmRadiometricExporter


def test_write_geo_txt_uses_tiff_filename_and_lon_lat_alt(tmp_path) -> None:
    path = tmp_path / "webodm_geo.txt"
    result = WebOdmExportResult(
        source_path="input.JPG",
        output_path=str(tmp_path / "image_thermal_celsius_float32.tif"),
        status="sikeres",
        gps_latitude=47.1,
        gps_longitude=19.2,
        altitude_m=123.4,
    )
    WebOdmRadiometricExporter.write_geo_txt(path, [result])
    assert path.read_text(encoding="utf-8").splitlines() == [
        "EPSG:4326",
        "image_thermal_celsius_float32.tif 19.2000000000 47.1000000000 123.400",
    ]

