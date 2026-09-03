"""
Lightweight YOLOv8-seg inference via onnxruntime (no PyTorch).

Returns a small Result-like object compatible with tray_common.class_area_fractions
and visualize_prediction.draw_masks (.masks.data.cpu().numpy(), .boxes, .names, .orig_shape).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from tray_common import CLASS_NAMES

try:
    import onnxruntime as ort
except ImportError as e:  # pragma: no cover
    raise SystemExit("pip install onnxruntime") from e


class _Tensor:
    """Mimic torch tensor .cpu().numpy() used by existing code."""

    def __init__(self, arr: np.ndarray):
        self._arr = arr

    def cpu(self):
        return self

    def numpy(self):
        return self._arr


@dataclass
class _Masks:
    data: _Tensor

    def __len__(self):
        return 0 if self.data is None else int(self.data.numpy().shape[0])


@dataclass
class _Boxes:
    cls: _Tensor
    conf: _Tensor


@dataclass
class OnnxResult:
    masks: _Masks | None
    boxes: _Boxes
    names: dict
    orig_shape: tuple[int, int]


def _letterbox(image: np.ndarray, imgsz: int):
    h, w = image.shape[:2]
    scale = min(imgsz / h, imgsz / w)
    nh, nw = int(round(h * scale)), int(round(w * scale))
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((imgsz, imgsz, 3), 114, dtype=np.uint8)
    top = (imgsz - nh) // 2
    left = (imgsz - nw) // 2
    canvas[top:top + nh, left:left + nw] = resized
    return canvas, scale, left, top


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thres: float) -> list[int]:
    if len(boxes) == 0:
        return []
    x1, y1, x2, y2 = boxes.T
    areas = (x2 - x1).clip(0) * (y2 - y1).clip(0)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = (xx2 - xx1).clip(0) * (yy2 - yy1).clip(0)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        order = order[1:][iou <= iou_thres]
    return keep


class OnnxSegModel:
    def __init__(self, model_path: str | Path, imgsz: int = 320):
        self.path = str(model_path)
        self.imgsz = imgsz
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(
            self.path, sess_options=opts, providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name
        self.names = {i: n for i, n in enumerate(CLASS_NAMES)}

    def predict(self, image_bgr: np.ndarray, conf: float = 0.25) -> OnnxResult:
        orig_h, orig_w = image_bgr.shape[:2]
        lb, scale, pad_x, pad_y = _letterbox(image_bgr, self.imgsz)
        blob = lb[:, :, ::-1].transpose(2, 0, 1).astype(np.float32) / 255.0
        blob = np.ascontiguousarray(blob[None])

        outs = self.session.run(None, {self.input_name: blob})
        # YOLOv8-seg ONNX: [pred (1, 4+nc+nm, N), proto (1, nm, mh, mw)]
        if len(outs) < 2:
            return OnnxResult(
                masks=None,
                boxes=_Boxes(_Tensor(np.zeros((0,), np.float32)), _Tensor(np.zeros((0,), np.float32))),
                names=self.names,
                orig_shape=(orig_h, orig_w),
            )

        pred = outs[0]
        proto = outs[1]
        if pred.ndim == 3:
            pred = pred[0]
        if proto.ndim == 4:
            proto = proto[0]
        # pred shape: (4+nc+nm, N) or (N, 4+nc+nm)
        if pred.shape[0] < pred.shape[1]:
            pred = pred.T

        nc = len(CLASS_NAMES)
        nm = proto.shape[0]
        boxes_xywh = pred[:, :4]
        class_scores = pred[:, 4:4 + nc]
        mask_coef = pred[:, 4 + nc:4 + nc + nm]

        cls_ids = class_scores.argmax(axis=1)
        scores = class_scores.max(axis=1)
        keep_conf = scores >= conf
        boxes_xywh = boxes_xywh[keep_conf]
        scores = scores[keep_conf]
        cls_ids = cls_ids[keep_conf]
        mask_coef = mask_coef[keep_conf]

        if len(scores) == 0:
            return OnnxResult(
                masks=None,
                boxes=_Boxes(_Tensor(np.zeros((0,), np.float32)), _Tensor(np.zeros((0,), np.float32))),
                names=self.names,
                orig_shape=(orig_h, orig_w),
            )

        # xywh (center) on letterboxed image -> xyxy
        x, y, w, h = boxes_xywh.T
        x1 = x - w / 2
        y1 = y - h / 2
        x2 = x + w / 2
        y2 = y + h / 2
        boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)

        keep = _nms(boxes_xyxy, scores, 0.45)
        boxes_xyxy = boxes_xyxy[keep]
        scores = scores[keep]
        cls_ids = cls_ids[keep]
        mask_coef = mask_coef[keep]

        # proto masks -> instance masks on letterbox, then map to original
        mh, mw = proto.shape[1], proto.shape[2]
        # (n, nm) @ (nm, mh*mw) -> (n, mh, mw)
        mats = mask_coef @ proto.reshape(nm, -1)
        mats = 1.0 / (1.0 + np.exp(-mats))
        mats = mats.reshape(-1, mh, mw)

        full_masks = []
        for i, mat in enumerate(mats):
            # upsample mask to letterbox size
            m = cv2.resize(mat, (self.imgsz, self.imgsz), interpolation=cv2.INTER_LINEAR)
            # crop letterbox padding
            y0 = pad_y
            x0 = pad_x
            y1b = pad_y + int(round(orig_h * scale))
            x1b = pad_x + int(round(orig_w * scale))
            m = m[y0:y1b, x0:x1b]
            m = cv2.resize(m, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
            # clip to box in original coords
            bx1, by1, bx2, by2 = boxes_xyxy[i]
            bx1 = int(np.clip((bx1 - pad_x) / scale, 0, orig_w - 1))
            by1 = int(np.clip((by1 - pad_y) / scale, 0, orig_h - 1))
            bx2 = int(np.clip((bx2 - pad_x) / scale, 0, orig_w - 1))
            by2 = int(np.clip((by2 - pad_y) / scale, 0, orig_h - 1))
            clip = np.zeros_like(m, dtype=np.float32)
            clip[by1:by2 + 1, bx1:bx2 + 1] = m[by1:by2 + 1, bx1:bx2 + 1]
            full_masks.append(clip)

        masks_arr = np.stack(full_masks, axis=0).astype(np.float32)
        return OnnxResult(
            masks=_Masks(_Tensor(masks_arr)),
            boxes=_Boxes(
                cls=_Tensor(cls_ids.astype(np.float32)),
                conf=_Tensor(scores.astype(np.float32)),
            ),
            names=self.names,
            orig_shape=(orig_h, orig_w),
        )


def load_onnx_model(path: str | Path, imgsz: int = 320) -> OnnxSegModel:
    return OnnxSegModel(path, imgsz=imgsz)
