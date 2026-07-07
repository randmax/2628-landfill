from pathlib import Path

from src.gui.main_window import _guess_rgb_pair, _image_pair_key, _is_rgb_image, _is_thermal_image


def test_dji_rgb_and_thermal_images_are_paired_by_sequence_number(tmp_path: Path) -> None:
    """Az RGB és termál fájlokat a DJI képsorszám köti össze, nem a timestamp."""
    root = tmp_path / "mission"
    thermal_dir = root / "M3T_T"
    rgb_dir = root / "M3T_RGB"
    thermal_dir.mkdir(parents=True)
    rgb_dir.mkdir(parents=True)

    thermal = thermal_dir / "DJI_20260626131741_0001_T.JPG"
    rgb = rgb_dir / "DJI_20260626131742_0001_V.JPG"
    thermal.write_bytes(b"thermal")
    rgb.write_bytes(b"rgb")

    assert _is_thermal_image(thermal)
    assert _is_rgb_image(rgb)
    assert _image_pair_key(thermal) == "0001"
    assert _image_pair_key(rgb) == "0001"
    assert _guess_rgb_pair(thermal) == rgb


def test_radiometric_rjpeg_suffix_is_treated_as_thermal() -> None:
    """A DJI SDK mintákban előforduló _R.JPG név is termál forrás."""
    thermal = Path("dataset/M3T/DJI_0001_R.JPG")

    assert _is_thermal_image(thermal)
    assert _image_pair_key(thermal) == "DJI_0001"
