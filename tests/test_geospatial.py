from src.models.image_record import ImageMetadata
from src.models.roi_result import RoiResult
from src.thermal.geospatial import enrich_roi_georeference


def test_enrich_roi_georeference_adds_center_and_metric_size() -> None:
    roi = RoiResult(310, 246, 20, 20, 1, 1, 1, 1, 1, 1, "mean", 1)
    metadata = ImageMetadata(
        gps_latitude=47.0,
        gps_longitude=19.0,
        relative_altitude=80.0,
        absolute_altitude=180.0,
    )
    enriched = enrich_roi_georeference(roi, metadata, (512, 640), 0.05)
    assert enriched.center_x_px == 320
    assert enriched.center_y_px == 256
    assert enriched.width_m == 1.0
    assert enriched.height_m == 1.0
    assert enriched.center_latitude == 47.0
    assert enriched.center_longitude == 19.0
    assert enriched.relative_altitude == 80.0
    assert enriched.absolute_altitude == 180.0

