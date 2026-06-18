"""
VisionAgent — local frame sampling and Hugging Face vision inference.

Public methods:
    - analyze_video()
    - detect_objects()
    - detect_graphs()
    - extract_text()

The implementation stays fully local by using Hugging Face models. Frame
sampling uses OpenCV.
"""

from __future__ import annotations

import json
import logging
from importlib import import_module
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.result import AgentResult


logger = logging.getLogger(__name__)

DEFAULT_FRAME_INTERVAL_SECONDS = 5.0
MAX_SAMPLED_FRAMES = 12

OBJECT_MODEL_NAME = "facebook/detr-resnet-50"
CAPTION_MODEL_NAME = "Salesforce/blip-image-captioning-base"
ZERO_SHOT_MODEL_NAME = "openai/clip-vit-base-patch32"
OCR_MODEL_NAME = "microsoft/trocr-base-printed"


class VisionAgent(BaseAgent):
    name = "vision"

    def __init__(self):
        self._object_detector = None
        self._caption_model = None
        self._zero_shot_classifier = None
        self._ocr_model = None

    @property
    def actions(self):
        return {
            "analyze_video": self.analyze_video,
            "analyze_frames": self.analyze_video,
            "detect_objects": self.detect_objects,
            "detect_graphs": self.detect_graphs,
            "detect_charts_and_graphs": self.detect_graphs,
            "extract_text": self.extract_text,
            "extract_text_from_frames": self.extract_text,
        }

    def run(self, context: AgentContext) -> AgentResult:
        action = context.action or "analyze_video"
        handler = self.actions.get(action)
        if handler is None:
            raise ValueError(f"VisionAgent: unknown action '{action}'")
        return handler(context)

    # ── Model loading ────────────────────────────────────────────────────────

    def _load_object_detector(self):
        transformers_module = self._get_transformers_module()
        pipeline = getattr(transformers_module, "pipeline", None) if transformers_module is not None else None
        if pipeline is None:
            raise HTTPException(status_code=500, detail="Vision dependencies are not installed. Install opencv-python, pillow, transformers, torch, and sentencepiece.")
        if self._object_detector is None:
            logger.info("Loading object detection model: %s", OBJECT_MODEL_NAME)
            self._object_detector = pipeline("object-detection", model=OBJECT_MODEL_NAME)
        return self._object_detector

    def _load_captioner(self):
        if self._caption_model is None:
            transformers_module = self._get_transformers_module()
            torch_module = self._get_torch_module()
            if transformers_module is None or torch_module is None:
                raise HTTPException(status_code=500, detail="Vision dependencies are not installed. Install opencv-python, pillow, transformers, torch, and sentencepiece.")
            logger.info("Loading caption model: %s", CAPTION_MODEL_NAME)
            processor = transformers_module.BlipProcessor.from_pretrained(CAPTION_MODEL_NAME)
            model = transformers_module.BlipForConditionalGeneration.from_pretrained(CAPTION_MODEL_NAME)
            model.eval()
            self._caption_model = (processor, model, torch_module)
        return self._caption_model

    def _load_zero_shot_classifier(self):
        transformers_module = self._get_transformers_module()
        pipeline = getattr(transformers_module, "pipeline", None) if transformers_module is not None else None
        if pipeline is None:
            raise HTTPException(status_code=500, detail="Vision dependencies are not installed. Install opencv-python, pillow, transformers, torch, and sentencepiece.")
        if self._zero_shot_classifier is None:
            logger.info("Loading zero-shot model: %s", ZERO_SHOT_MODEL_NAME)
            self._zero_shot_classifier = pipeline(
                "zero-shot-image-classification",
                model=ZERO_SHOT_MODEL_NAME,
            )
        return self._zero_shot_classifier

    def _load_ocr_model(self):
        if self._ocr_model is None:
            transformers_module = self._get_transformers_module()
            torch_module = self._get_torch_module()
            if transformers_module is None or torch_module is None:
                raise HTTPException(status_code=500, detail="Vision dependencies are not installed. Install opencv-python, pillow, transformers, torch, and sentencepiece.")
            logger.info("Loading OCR model: %s", OCR_MODEL_NAME)
            processor = transformers_module.TrOCRProcessor.from_pretrained(OCR_MODEL_NAME)
            model = transformers_module.VisionEncoderDecoderModel.from_pretrained(OCR_MODEL_NAME)
            model.eval()
            self._ocr_model = (processor, model, torch_module)
        return self._ocr_model

    def _get_transformers_module(self):
        try:
            return import_module("transformers")
        except ImportError:
            return None

    def _get_torch_module(self):
        try:
            return import_module("torch")
        except ImportError:
            return None

    def _get_cv2(self):
        try:
            return import_module("cv2")
        except ImportError:
            return None

    def _get_image_module(self):
        try:
            return import_module("PIL.Image")
        except ImportError:
            return None

    # ── Frame sampling ───────────────────────────────────────────────────────

    def _frame_interval_seconds(self, context: AgentContext) -> float:
        raw_value = context.metadata.get("frame_interval_seconds", DEFAULT_FRAME_INTERVAL_SECONDS)
        try:
            return max(1.0, float(raw_value))
        except (TypeError, ValueError):
            return DEFAULT_FRAME_INTERVAL_SECONDS

    def _sample_frames(self, video_path: str, interval_seconds: float) -> list[dict[str, Any]]:
        cv2 = self._get_cv2()
        image_module = self._get_image_module()
        if cv2 is None or image_module is None:
            raise HTTPException(status_code=500, detail="Vision dependencies are not installed. Install opencv-python, pillow, transformers, torch, and sentencepiece.")
        capture = cv2.VideoCapture(video_path)
        if not capture.isOpened():
            raise HTTPException(status_code=400, detail="Unable to open video for vision analysis")

        frames: list[dict[str, Any]] = []
        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

            if fps > 0 and frame_count > 0:
                frame_step = max(1, int(round(interval_seconds * fps)))
                frame_indexes = list(range(0, frame_count, frame_step))
                if len(frame_indexes) > MAX_SAMPLED_FRAMES:
                    stride = max(1, len(frame_indexes) // MAX_SAMPLED_FRAMES)
                    frame_indexes = frame_indexes[::stride][:MAX_SAMPLED_FRAMES]

                for frame_index in frame_indexes:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                    success, frame = capture.read()
                    if not success:
                        continue
                    timestamp = frame_index / fps
                    frames.append({"timestamp": round(timestamp, 2), "image": self._to_pil_image(frame)})
            else:
                next_sample_time = 0.0
                frame_index = 0
                while True:
                    success, frame = capture.read()
                    if not success:
                        break
                    timestamp = frame_index / fps if fps > 0 else float(frame_index)
                    if timestamp + 1e-6 >= next_sample_time:
                        frames.append({"timestamp": round(timestamp, 2), "image": self._to_pil_image(frame)})
                        next_sample_time += interval_seconds
                        if len(frames) >= MAX_SAMPLED_FRAMES:
                            break
                    frame_index += 1
        finally:
            capture.release()

        return frames

    def _to_pil_image(self, frame) -> Any:
        cv2 = self._get_cv2()
        image_module = self._get_image_module()
        if cv2 is None or image_module is None:
            raise HTTPException(status_code=500, detail="Vision dependencies are not installed. Install opencv-python, pillow, transformers, torch, and sentencepiece.")
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return image_module.fromarray(rgb_frame)

    # ── Model helpers ────────────────────────────────────────────────────────

    def _extract_caption(self, image: Any) -> str:
        processor, model, torch_module = self._load_captioner()
        inputs = processor(images=image, return_tensors="pt")
        inputs = {key: value.to(model.device) for key, value in inputs.items() if hasattr(value, "to")}

        with torch_module.inference_mode():
            output_ids = model.generate(**inputs, max_new_tokens=32)

        caption = processor.batch_decode(output_ids, skip_special_tokens=True)
        return caption[0].strip() if caption else ""

    def _detect_objects_in_image(self, image: Any) -> list[dict[str, Any]]:
        detections = self._load_object_detector()(image)
        return [
            {
                "label": detection.get("label", "unknown"),
                "score": round(float(detection.get("score", 0.0)), 4),
                "box": {
                    key: round(float(value), 2)
                    for key, value in (detection.get("box") or {}).items()
                },
            }
            for detection in detections
        ]

    def _classify_scene(self, image: Any) -> dict[str, Any]:
        candidate_labels = [
            "person",
            "people",
            "screen",
            "monitor",
            "laptop",
            "chart",
            "graph",
            "text-heavy slide",
            "presentation slide",
        ]
        predictions = self._load_zero_shot_classifier()(image, candidate_labels=candidate_labels)
        best_labels = {prediction["label"]: round(float(prediction["score"]), 4) for prediction in predictions}

        return {
            "predictions": best_labels,
            "has_people": best_labels.get("person", 0.0) >= 0.25 or best_labels.get("people", 0.0) >= 0.25,
            "has_screen": max(best_labels.get("screen", 0.0), best_labels.get("monitor", 0.0), best_labels.get("laptop", 0.0)) >= 0.25,
            "has_chart": best_labels.get("chart", 0.0) >= 0.25,
            "has_graph": best_labels.get("graph", 0.0) >= 0.25,
            "has_text": max(best_labels.get("text-heavy slide", 0.0), best_labels.get("presentation slide", 0.0)) >= 0.25,
        }

    def _extract_text_from_image(self, image: Any) -> str:
        processor, model, torch_module = self._load_ocr_model()
        inputs = processor(images=image, return_tensors="pt")
        pixel_values = inputs.pixel_values.to(model.device)

        with torch_module.inference_mode():
            generated_ids = model.generate(pixel_values, max_new_tokens=64)

        text = processor.batch_decode(generated_ids, skip_special_tokens=True)
        return text[0].strip() if text else ""

    def _build_result(self, action: str, payload: dict[str, Any]) -> AgentResult:
        return AgentResult(
            agent=self.name,
            action=action,
            response=json.dumps(payload, indent=2, ensure_ascii=False),
            confidence=float(payload.get("confidence", 0.85)),
            objects=payload.get("objects", []),
            frames=payload.get("frames", []),
            metadata=payload,
        )

    def _analyze_frames(self, context: AgentContext) -> list[dict[str, Any]]:
        interval_seconds = self._frame_interval_seconds(context)
        sampled_frames = self._sample_frames(context.video_path, interval_seconds)
        if not sampled_frames:
            raise HTTPException(status_code=500, detail="No frames could be sampled from the video")

        frame_results: list[dict[str, Any]] = []
        for sampled_frame in sampled_frames:
            image = sampled_frame["image"]
            object_detections = self._detect_objects_in_image(image)
            scene = self._classify_scene(image)
            caption = self._extract_caption(image)
            text = self._extract_text_from_image(image)

            frame_results.append(
                {
                    "timestamp": sampled_frame["timestamp"],
                    "caption": caption,
                    "objects": object_detections,
                    "scene": scene,
                    "text": text,
                }
            )

        return frame_results

    # ── Public actions ───────────────────────────────────────────────────────

    def analyze_video(self, context: AgentContext) -> AgentResult:
        frame_results = self._analyze_frames(context)
        interval_seconds = self._frame_interval_seconds(context)

        unique_objects: list[str] = []
        people_count = 0
        chart_frames: list[float] = []
        graph_frames: list[float] = []
        screen_frames: list[float] = []
        text_frames: list[float] = []

        for frame in frame_results:
            for detection in frame["objects"]:
                label = detection["label"]
                if label not in unique_objects:
                    unique_objects.append(label)
                if label == "person":
                    people_count += 1

            scene = frame["scene"]
            timestamp = frame["timestamp"]
            if scene.get("has_chart"):
                chart_frames.append(timestamp)
            if scene.get("has_graph"):
                graph_frames.append(timestamp)
            if scene.get("has_screen"):
                screen_frames.append(timestamp)
            if scene.get("has_text") or frame.get("text"):
                text_frames.append(timestamp)

        payload = {
            "agent": self.name,
            "action": "analyze_video",
            "result": "Video analyzed using local Hugging Face vision models.",
            "frame_interval_seconds": interval_seconds,
            "frame_count": len(frame_results),
            "summary": {
                "people_detected": people_count,
                "objects_detected": unique_objects,
                "chart_frames": chart_frames,
                "graph_frames": graph_frames,
                "screen_frames": screen_frames,
                "text_frames": text_frames,
            },
            "frames": frame_results,
            "confidence": 0.9,
        }
        return self._build_result("analyze_video", payload)

    def detect_objects(self, context: AgentContext) -> AgentResult:
        frame_results = self._analyze_frames(context)
        interval_seconds = self._frame_interval_seconds(context)

        detections_by_frame = []
        unique_objects: list[str] = []
        people_count = 0

        for frame in frame_results:
            objects = frame["objects"]
            detections_by_frame.append(
                {
                    "timestamp": frame["timestamp"],
                    "objects": objects,
                }
            )
            for detection in objects:
                label = detection["label"]
                if label not in unique_objects:
                    unique_objects.append(label)
                if label == "person":
                    people_count += 1

        payload = {
            "agent": self.name,
            "action": "detect_objects",
            "result": "Objects detected from sampled frames using a local Hugging Face model.",
            "frame_interval_seconds": interval_seconds,
            "frame_count": len(frame_results),
            "summary": {
                "people_detected": people_count,
                "objects_detected": unique_objects,
            },
            "frames": detections_by_frame,
            "confidence": 0.92,
        }
        return self._build_result("detect_objects", payload)

    def detect_graphs(self, context: AgentContext) -> AgentResult:
        frame_results = self._analyze_frames(context)
        interval_seconds = self._frame_interval_seconds(context)

        graph_frames = []
        chart_frames = []
        screen_frames = []

        for frame in frame_results:
            scene = frame["scene"]
            entry = {
                "timestamp": frame["timestamp"],
                "predictions": scene["predictions"],
                "caption": frame["caption"],
                "text": frame["text"],
            }
            if scene.get("has_chart"):
                chart_frames.append(entry)
            if scene.get("has_graph"):
                graph_frames.append(entry)
            if scene.get("has_screen"):
                screen_frames.append(entry)

        payload = {
            "agent": self.name,
            "action": "detect_graphs",
            "result": "Charts, graphs, and screens detected from sampled frames using a local Hugging Face model.",
            "frame_interval_seconds": interval_seconds,
            "frame_count": len(frame_results),
            "summary": {
                "chart_frames": [frame["timestamp"] for frame in chart_frames],
                "graph_frames": [frame["timestamp"] for frame in graph_frames],
                "screen_frames": [frame["timestamp"] for frame in screen_frames],
            },
            "frames": {
                "charts": chart_frames,
                "graphs": graph_frames,
                "screens": screen_frames,
            },
            "confidence": 0.88,
        }
        return self._build_result("detect_graphs", payload)

    def extract_text(self, context: AgentContext) -> AgentResult:
        frame_results = self._analyze_frames(context)
        interval_seconds = self._frame_interval_seconds(context)

        text_frames = []
        extracted_texts = []
        for frame in frame_results:
            text = frame.get("text", "")
            if text:
                extracted_texts.append(text)
                text_frames.append(
                    {
                        "timestamp": frame["timestamp"],
                        "text": text,
                        "caption": frame["caption"],
                    }
                )

        payload = {
            "agent": self.name,
            "action": "extract_text",
            "result": "Text extracted from sampled frames using a local Hugging Face OCR model.",
            "frame_interval_seconds": interval_seconds,
            "frame_count": len(frame_results),
            "summary": {
                "text_frames": [frame["timestamp"] for frame in text_frames],
                "text_snippets": extracted_texts[:10],
            },
            "frames": text_frames,
            "confidence": 0.86,
        }
        return self._build_result("extract_text", payload)