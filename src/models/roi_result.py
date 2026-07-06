from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class RoiSettings:
    """User controlled ROI search settings."""

    width: int = 20
    height: int = 20
    stride: int = 1
    min_valid_ratio: float = 0.95
    ranking_metric: str = "mean"
    gsd_m_per_px: float = 0.05
    auto_thermal_gsd: bool = True
    thermal_hfov_deg: float = 61.0

    def validate_for_shape(self, shape: tuple[int, int]) -> None:
        """Validate settings against a matrix shape."""
        image_h, image_w = shape
        if self.width < 1 or self.height < 1:
            raise ValueError("A ROI szelessege es magassaga legalabb 1 pixel legyen.")
        if self.stride < 1:
            raise ValueError("A lepeskoz legalabb 1 pixel legyen.")
        if self.width > image_w or self.height > image_h:
            raise ValueError("A ROI nem lehet nagyobb a kepnel.")
        if not 0 < self.min_valid_ratio <= 1:
            raise ValueError("A minimum ervenyes pixelarany 0 es 1 koze essen.")
        if self.ranking_metric not in {"mean", "p95", "max"}:
            raise ValueError("Ismeretlen rangsorolasi metrika.")

    def to_dict(self) -> dict[str, object]:
        """Return a JSON serializable representation."""
        return asdict(self)


@dataclass
class RoiResult:
    """Statistics for the best ROI on one thermal matrix."""

    x: int
    y: int
    width: int
    height: int
    mean_temperature: float
    min_temperature: float
    max_temperature: float
    median_temperature: float
    p95_temperature: float
    valid_pixel_ratio: float
    ranking_metric: str
    ranking_value: float
    center_x_px: float | None = None
    center_y_px: float | None = None
    thermal_width_px: int | None = None
    thermal_height_px: int | None = None
    gsd_m_per_px: float | None = None
    width_m: float | None = None
    height_m: float | None = None
    center_latitude: float | None = None
    center_longitude: float | None = None
    relative_altitude: float | None = None
    absolute_altitude: float | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON serializable representation."""
        return asdict(self)
