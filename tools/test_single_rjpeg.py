from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models.image_record import RadiometricSettings
from src.thermal.dji_sdk_wrapper import DjiThermalSdk


def main() -> int:
    """Measure one DJI R-JPEG and save the Celsius matrix as .npy."""
    parser = argparse.ArgumentParser(description="DJI R-JPEG homersekleti matrix teszt")
    parser.add_argument("image", help="R-JPEG kep eleresi utja")
    parser.add_argument("-o", "--output", default="output/temperature_matrix.npy")
    args = parser.parse_args()

    sdk = DjiThermalSdk()
    measured = sdk.measure(args.image, RadiometricSettings())
    matrix = measured.data
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.save(output, matrix)
    print(f"Kepmeret: {measured.width} x {measured.height}")
    print(f"Minimumhomerseklet: {float(np.nanmin(matrix)):.2f} C")
    print(f"Maximumhomerseklet: {float(np.nanmax(matrix)):.2f} C")
    print(f"Atlaghomerseklet: {float(np.nanmean(matrix)):.2f} C")
    print(f"Mentve: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

