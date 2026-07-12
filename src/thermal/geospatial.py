from __future__ import annotations

import math

from src.models.image_record import ImageMetadata
from src.models.roi_result import RoiResult, RoiSettings

EARTH_RADIUS_M = 6_378_137.0


def enrich_roi_georeference(
    roi: RoiResult,
    metadata: ImageMetadata,
    image_shape: tuple[int, int],
    gsd_m_per_px: float,
) -> RoiResult:
    """Méteres ROI-méretet és becsült középponti GPS koordinátát ad az eredményhez."""
    image_h, image_w = image_shape
    center_x = roi.x + roi.width / 2.0
    center_y = roi.y + roi.height / 2.0
    roi.center_x_px = center_x
    roi.center_y_px = center_y
    roi.thermal_width_px = image_w
    roi.thermal_height_px = image_h
    roi.gsd_m_per_px = gsd_m_per_px
    roi.width_m = roi.width * gsd_m_per_px
    roi.height_m = roi.height * gsd_m_per_px
    roi.relative_altitude = metadata.relative_altitude
    roi.absolute_altitude = metadata.absolute_altitude if metadata.absolute_altitude is not None else metadata.gps_altitude

    # Ha nincs kép GPS, akkor is megtartjuk a méteres ROI-méretet; csak a koordináta
    # becslése marad üres.
    if metadata.gps_latitude is None or metadata.gps_longitude is None:
        return roi

    point = pixel_to_gps(metadata, image_shape, center_x, center_y, gsd_m_per_px)
    if point is not None:
        roi.center_latitude, roi.center_longitude = point
    return roi


def pixel_to_gps(
    metadata: ImageMetadata,
    image_shape: tuple[int, int],
    pixel_x: float,
    pixel_y: float,
    gsd_m_per_px: float,
) -> tuple[float, float] | None:
    """Képpontból becsült GPS koordinátát számol a kép középponti GPS-e alapján."""
    if metadata.gps_latitude is None or metadata.gps_longitude is None:
        return None

    image_h, image_w = image_shape
    east_m = (pixel_x - image_w / 2.0) * gsd_m_per_px
    north_m = -(pixel_y - image_h / 2.0) * gsd_m_per_px
    yaw = metadata.flight_yaw if metadata.flight_yaw is not None else metadata.gimbal_yaw
    if yaw is not None:
        north_m, east_m = _rotate_north_east(north_m, east_m, yaw)

    return offset_lat_lon(metadata.gps_latitude, metadata.gps_longitude, north_m, east_m)


def resolve_thermal_gsd(
    settings: RoiSettings,
    metadata: ImageMetadata,
    image_width_px: int,
) -> float:
    """Képenként visszaadja a tényleges termál GSD-t."""
    if (
        settings.auto_thermal_gsd
        and metadata.relative_altitude is not None
        and metadata.relative_altitude > 0
        and settings.thermal_hfov_deg > 0
    ):
        ground_width_m = 2.0 * metadata.relative_altitude * math.tan(math.radians(settings.thermal_hfov_deg) / 2.0)
        return ground_width_m / float(image_width_px)
    return settings.gsd_m_per_px


def offset_lat_lon(latitude: float, longitude: float, north_m: float, east_m: float) -> tuple[float, float]:
    """Offset latitude and longitude by local north/east meters."""
    lat_rad = math.radians(latitude)
    new_lat = latitude + math.degrees(north_m / EARTH_RADIUS_M)
    new_lon = longitude + math.degrees(east_m / (EARTH_RADIUS_M * math.cos(lat_rad)))
    return new_lat, new_lon


def _rotate_north_east(north_m: float, east_m: float, yaw_degrees: float) -> tuple[float, float]:
    yaw = math.radians(yaw_degrees)
    rotated_north = north_m * math.cos(yaw) - east_m * math.sin(yaw)
    rotated_east = north_m * math.sin(yaw) + east_m * math.cos(yaw)
    return rotated_north, rotated_east
