"""
Songa CV — Detector
Player and ball detection using YOLOv8.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# COCO class names relevant to basketball
_PERSON_CLASSES = {"person"}
_BALL_CLASSES = {"sports ball"}


@dataclass
class Detection:
    """Single detected object."""
    id: int
    bbox: tuple[float, float, float, float]  # xyxy
    confidence: float
    class_name: str

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]


@dataclass
class DetectionResult:
    """Output of one detection pass on a single frame."""
    players: list[Detection] = field(default_factory=list)
    ball: Optional[Detection] = None

    @property
    def all_detections(self) -> list[Detection]:
        result = list(self.players)
        if self.ball is not None:
            result.append(self.ball)
        return result


class Detector:
    """
    YOLOv8-based object detector for basketball scenes.

    Loads a YOLO model and filters detections into players (person) and ball
    (sports ball). Falls back to yolov8n.pt if the specified model path does
    not exist.
    """

    def __init__(
        self,
        model_path: str = "models/songa-basketball.pt",
        conf_threshold: float = 0.35,
        device: str = "cpu",
    ) -> None:
        self.conf_threshold = conf_threshold
        self.device = device
        self._model = None
        self._model_path = self._resolve_model(model_path)
        self._load_model()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_model(self, model_path: str) -> str:
        p = Path(model_path)
        if p.exists():
            return str(p)
        logger.warning(
            "Model not found at '%s' — falling back to yolov8n.pt (auto-download).",
            model_path,
        )
        return "yolov8n.pt"

    def _load_model(self) -> None:
        try:
            from ultralytics import YOLO  # type: ignore

            self._model = YOLO(self._model_path)
            self._model.to(self.device)
            logger.info("YOLO model loaded: %s on %s", self._model_path, self.device)
        except ImportError:
            logger.error(
                "ultralytics not installed. Run: pip install ultralytics>=8.3.0"
            )
            self._model = None
        except Exception as exc:
            logger.error("Failed to load YOLO model: %s", exc)
            self._model = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Run detection on a single BGR frame.

        Returns a DetectionResult with separated player and ball detections.
        Falls back to empty result if the model is unavailable.
        """
        if self._model is None:
            return DetectionResult()

        try:
            results = self._model(
                frame,
                conf=self.conf_threshold,
                device=self.device,
                verbose=False,
            )
        except Exception as exc:
            logger.warning("Detection failed: %s", exc)
            return DetectionResult()

        players: list[Detection] = []
        ball: Optional[Detection] = None

        for result in results:
            if result.boxes is None:
                continue
            boxes = result.boxes
            names: dict[int, str] = result.names  # type: ignore

            for idx, box in enumerate(boxes):
                cls_id = int(box.cls[0].item())
                cls_name = names.get(cls_id, "unknown").lower()
                conf = float(box.conf[0].item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                bbox = (x1, y1, x2, y2)

                det = Detection(id=idx, bbox=bbox, confidence=conf, class_name=cls_name)

                if cls_name in _PERSON_CLASSES:
                    players.append(det)
                elif cls_name in _BALL_CLASSES:
                    if ball is None or conf > ball.confidence:
                        ball = det

        return DetectionResult(players=players, ball=ball)

    def draw_detections(
        self, frame: np.ndarray, detections: DetectionResult
    ) -> np.ndarray:
        """
        Draw bounding boxes on a copy of the frame for debug visualisation.

        Players are drawn in green, the ball in orange.
        """
        for det in detections.players:
            x1, y1, x2, y2 = (int(v) for v in det.bbox)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
            label = f"P {det.confidence:.2f}"
            cv2.putText(
                frame, label, (x1, y1 - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 0), 1
            )

        if detections.ball is not None:
            b = detections.ball
            x1, y1, x2, y2 = (int(v) for v in b.bbox)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 140, 255), 2)
            cx, cy = (int(v) for v in b.center)
            cv2.circle(frame, (cx, cy), 6, (0, 140, 255), -1)
            cv2.putText(
                frame, f"Ball {b.confidence:.2f}", (x1, y1 - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 140, 255), 1
            )

        return frame
