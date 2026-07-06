from __future__ import annotations

import ctypes
import os
import platform
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.models.image_record import RadiometricSettings


ERROR_CODES = {
    0: "DIRP_SUCCESS",
    -1: "DIRP_ERROR_MALLOC",
    -2: "DIRP_ERROR_POINTER_NULL",
    -3: "DIRP_ERROR_INVALID_PARAMS",
    -4: "DIRP_ERROR_INVALID_RAW",
    -5: "DIRP_ERROR_INVALID_HEADER",
    -6: "DIRP_ERROR_INVALID_CURVE",
    -7: "DIRP_ERROR_RJPEG_PARSE",
    -8: "DIRP_ERROR_SIZE",
    -9: "DIRP_ERROR_INVALID_HANDLE",
    -10: "DIRP_ERROR_FORMAT_INPUT",
    -11: "DIRP_ERROR_FORMAT_OUTPUT",
    -12: "DIRP_ERROR_UNSUPPORTED_FUNC",
    -13: "DIRP_ERROR_NOT_READY",
    -14: "DIRP_ERROR_ACTIVATION",
    -15: "DIRP_ERROR_INVALID_INI",
    -16: "DIRP_ERROR_INVALID_SUB_DLL",
    -32: "DIRP_ERROR_ADVANCED",
    -64: "DIRP_ERROR_SUPER_MODE",
}


class DjiSdkError(RuntimeError):
    """Raised when DJI DIRP returns an error."""


class DirpResolution(ctypes.Structure):
    _fields_ = [("width", ctypes.c_int32), ("height", ctypes.c_int32)]


class DirpApiVersion(ctypes.Structure):
    _fields_ = [("api", ctypes.c_uint32), ("magic", ctypes.c_char * 8)]


class DirpMeasurementParams(ctypes.Structure):
    _fields_ = [
        ("distance", ctypes.c_float),
        ("humidity", ctypes.c_float),
        ("emissivity", ctypes.c_float),
        ("reflection", ctypes.c_float),
        ("ambient_temp", ctypes.c_float),
    ]


@dataclass
class TemperatureMatrix:
    """Radiometric output from one R-JPEG image."""

    data: np.ndarray
    width: int
    height: int
    api_version: str


class DjiThermalSdk:
    """Magyar oldali `ctypes` burkoló a DJI Thermal SDK DIRP függvényeihez."""

    _lock = threading.Lock()

    def __init__(self, lib_dir: str | Path | None = None) -> None:
        self.lib_dir = Path(lib_dir) if lib_dir else self._default_lib_dir()
        self.dll_path = self.lib_dir / "libdirp.dll"
        if not self.dll_path.exists():
            raise DjiSdkError(f"Nem talalhato a DJI SDK DLL: {self.dll_path}")
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(self.lib_dir.resolve()))
        self._lib = ctypes.CDLL(str(self.dll_path))
        self._configure_signatures()

    @staticmethod
    def _default_lib_dir() -> Path:
        machine = platform.machine().lower()
        arch = "release_x64" if "64" in machine else "release_x86"
        return Path("dji_thermal_sdk_v1.8_20250829") / "tsdk-core" / "lib" / "windows" / arch

    def sdk_version(self) -> str:
        """Return the SDK version path marker used for cache invalidation."""
        return f"dirp:{self.dll_path.stat().st_mtime_ns}:{self.dll_path.stat().st_size}"

    def measure(self, image_path: str | Path, settings: RadiometricSettings) -> TemperatureMatrix:
        """DJI R-JPEG képből float32 Celsius hőmérsékleti mátrixot olvas."""
        path = Path(image_path)
        data = path.read_bytes()
        buffer = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
        handle = ctypes.c_void_p()

        # Az SDK szálbiztonsága nincs egyértelműen dokumentálva, ezért minden DIRP hívást
        # egy közös záron keresztül futtatunk. A GUI ettől még reszponzív marad, mert worker
        # szálból hívjuk ezt a metódust.
        with self._lock:
            self._check(self._lib.dirp_create_from_rjpeg(buffer, len(data), ctypes.byref(handle)), "dirp_create_from_rjpeg")
            try:
                resolution = DirpResolution()
                self._check(self._lib.dirp_get_rjpeg_resolution(handle, ctypes.byref(resolution)), "dirp_get_rjpeg_resolution")
                params = self._get_measurement_params(handle)
                params.distance = settings.distance
                params.humidity = settings.humidity
                params.emissivity = settings.emissivity
                params.reflection = settings.reflected_temperature
                params.ambient_temp = settings.ambient_temperature
                self._check(self._lib.dirp_set_measurement_params(handle, ctypes.byref(params)), "dirp_set_measurement_params")

                # A dirp_measure_ex közvetlenül valós Celsius értékeket ad float32 formában;
                # semmilyen 8 bites/palettázott képből származtatott értéket nem használunk.
                size = resolution.width * resolution.height
                out = (ctypes.c_float * size)()
                self._check(
                    self._lib.dirp_measure_ex(handle, out, size * ctypes.sizeof(ctypes.c_float)),
                    "dirp_measure_ex",
                )
                arr = np.ctypeslib.as_array(out).reshape((resolution.height, resolution.width)).copy()
                version = DirpApiVersion()
                api_text = "unknown"
                if self._lib.dirp_get_api_version(handle, ctypes.byref(version)) == 0:
                    api_text = f"0x{version.api:x}:{bytes(version.magic).split(chr(0).encode())[0].decode(errors='ignore')}"
                return TemperatureMatrix(arr.astype(np.float32, copy=False), resolution.width, resolution.height, api_text)
            finally:
                self._lib.dirp_destroy(handle)

    def _get_measurement_params(self, handle: ctypes.c_void_p) -> DirpMeasurementParams:
        params = DirpMeasurementParams()
        self._check(self._lib.dirp_get_measurement_params(handle, ctypes.byref(params)), "dirp_get_measurement_params")
        return params

    def _configure_signatures(self) -> None:
        self._lib.dirp_create_from_rjpeg.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int32, ctypes.POINTER(ctypes.c_void_p)]
        self._lib.dirp_create_from_rjpeg.restype = ctypes.c_int32
        self._lib.dirp_destroy.argtypes = [ctypes.c_void_p]
        self._lib.dirp_destroy.restype = ctypes.c_int32
        self._lib.dirp_get_rjpeg_resolution.argtypes = [ctypes.c_void_p, ctypes.POINTER(DirpResolution)]
        self._lib.dirp_get_rjpeg_resolution.restype = ctypes.c_int32
        self._lib.dirp_measure_ex.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.c_int32]
        self._lib.dirp_measure_ex.restype = ctypes.c_int32
        self._lib.dirp_get_measurement_params.argtypes = [ctypes.c_void_p, ctypes.POINTER(DirpMeasurementParams)]
        self._lib.dirp_get_measurement_params.restype = ctypes.c_int32
        self._lib.dirp_set_measurement_params.argtypes = [ctypes.c_void_p, ctypes.POINTER(DirpMeasurementParams)]
        self._lib.dirp_set_measurement_params.restype = ctypes.c_int32
        self._lib.dirp_get_api_version.argtypes = [ctypes.c_void_p, ctypes.POINTER(DirpApiVersion)]
        self._lib.dirp_get_api_version.restype = ctypes.c_int32

    @staticmethod
    def _check(code: int, call: str) -> None:
        if code != 0:
            name = ERROR_CODES.get(code, f"DIRP_ERROR_{code}")
            raise DjiSdkError(f"{call} sikertelen: {name} ({code})")
