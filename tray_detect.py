"""
หา "วงถาด" ในภาพ เพื่อตัดทุกอย่างนอกถาดทิ้งก่อนคิด %

ปัญหาที่แก้: โมเดลยังแยกไม่ออกว่าอะไรคือถาด อะไรคือพื้นหลัง — mask ของ liquid
ชอบไปเกาะพื้นหลัง/เสื้อนักเรียน/ขอบภาพ ทำให้ % เพี้ยน (ขึ้นน้ำ 71% ทั้งที่ในถาดแทบไม่มี)
วิธีแก้ที่ไม่ต้องรอ retrain คือหาขอบถาดด้วย classical CV แล้วกรอง detection นอกวงทิ้ง

ใช้ทดสอบว่าหาวงถาดถูกไหม (วาดวงทับภาพให้ดูด้วยตา):
    python tray_detect.py samples/demo --out runs/tray_check
    python tray_detect.py รูป.jpg --out runs/tray_check
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np

from tray_common import TrayCircle, iter_images

# ---- ข้อจำกัดเชิงเรขาคณิต: ถาดเป็นของใหญ่ที่วางกลางภาพ ----
# ใช้กันไม่ให้ไปจับจานเล็ก ๆ หรือวงกลมมั่ว ๆ ที่มุมภาพ
MIN_RADIUS_RATIO = 0.18   # รัศมีอย่างน้อยเท่านี้เทียบด้านสั้นของภาพ
MAX_RADIUS_RATIO = 0.75   # และไม่เกินเท่านี้
MAX_CENTER_OFFSET = 0.32  # จุดศูนย์กลางต้องห่างจากกลางภาพไม่เกินเท่านี้ (สัดส่วนด้านสั้น)


def _is_plausible(cx: float, cy: float, r: float, shape: tuple[int, int]) -> bool:
    """วงนี้ 'เป็นถาดได้ไหม' — เช็กขนาดกับตำแหน่งก่อนจะเชื่อ"""
    h, w = shape
    short = min(h, w)
    if not (MIN_RADIUS_RATIO * short <= r <= MAX_RADIUS_RATIO * short):
        return False
    offset = np.hypot(cx - w / 2, cy - h / 2)
    return offset <= MAX_CENTER_OFFSET * short


def _geometry_score(cx: float, cy: float, r: float, shape: tuple[int, int]) -> float:
    """คะแนนจากรูปทรงล้วน ๆ 0-1: วงยิ่งใหญ่และยิ่งอยู่กลางภาพ ยิ่งน่าจะเป็นถาด"""
    h, w = shape
    short = min(h, w)
    size_score = min(r / (0.5 * short), 1.0)
    offset = np.hypot(cx - w / 2, cy - h / 2) / short
    center_score = max(0.0, 1.0 - offset / MAX_CENTER_OFFSET)
    return float(0.5 * size_score + 0.5 * center_score)


#: แถบค้นหาขอบรอบเส้นรอบวง (พิกเซล) — ต้องแคบและ "คงที่" ไม่ผูกกับรัศมี
#: ถ้าให้แถบกว้างตามรัศมี วงที่ใหญ่เกินจริงจะกวาดไปเจอขอบอะไรก็ได้แล้วได้คะแนนสูงลอย ๆ
EDGE_BAND_PX = 4
#: ขอบถาดจริง gradient ต้องชี้ตามแนวรัศมี — ต่ำกว่านี้ถือว่าเป็นขอบของอย่างอื่น
RADIAL_ALIGN_MIN = 0.65


def _edge_support(gx: np.ndarray, gy: np.ndarray, mag: np.ndarray, strong: float,
                  cx: float, cy: float, r: float, n_samples: int = 240) -> float:
    """
    "ขอบวงนี้มีอยู่จริงในภาพไหม" — เดินรอบเส้นรอบวงแล้วนับว่ากี่ % ของจุดตกบนขอบจริง

    นี่คือหัวใจที่ทำให้ผลนิ่ง: HoughCircles คืนวงมาเสมอแม้รัศมีจะผิด ถ้าเชื่อดื้อ ๆ
    จะไปตัดอาหารจริงทิ้ง เกณฑ์ที่ใช้มี 2 ข้อ ต้องผ่านทั้งคู่:
      1. ความชันของภาพตรงนั้นแรงพอ (เป็นขอบอะไรสักอย่าง)
      2. ทิศของความชัน "ชี้ออกตามแนวรัศมี" (เป็นขอบของวงกลมวงนี้จริง ๆ)
    ข้อ 2 สำคัญมาก เพราะขอบของอาหาร/ลายพื้นหลังจะมีทิศมั่ว ผ่านข้อ 1 แต่ตกข้อ 2
    """
    h, w = mag.shape
    angles = np.linspace(0, 2 * np.pi, n_samples, endpoint=False)
    cos_a, sin_a = np.cos(angles), np.sin(angles)

    supported = np.zeros(n_samples, dtype=bool)
    polarity = np.zeros(n_samples, dtype=np.float32)   # เก็บ "ขั้ว" ของขอบไว้เช็กความสม่ำเสมอ

    for dr in range(-EDGE_BAND_PX, EDGE_BAND_PX + 1):
        fx = cx + (r + dr) * cos_a
        fy = cy + (r + dr) * sin_a
        valid = (fx >= 0) & (fx < w) & (fy >= 0) & (fy < h)   # นอกภาพ = ไม่นับว่ามีขอบ
        xs = np.clip(fx, 0, w - 1).astype(int)
        ys = np.clip(fy, 0, h - 1).astype(int)

        m = mag[ys, xs]
        # ทิศของ gradient เทียบกับแนวรัศมี: บวก = ยิ่งออกนอกยิ่งสว่าง, ลบ = ยิ่งออกนอกยิ่งมืด
        with np.errstate(divide="ignore", invalid="ignore"):
            signed = (gx[ys, xs] * cos_a + gy[ys, xs] * sin_a) / np.maximum(m, 1e-6)
        hit = valid & (m > strong) & (np.abs(signed) > RADIAL_ALIGN_MIN)
        polarity = np.where(hit & (polarity == 0), np.sign(signed), polarity)
        supported |= hit

    frac = float(supported.mean())
    if frac == 0:
        return 0.0

    # ขอบถาดจริงเป็นวงปิดที่ "สว่างข้างใน มืดข้างนอก" (หรือกลับกัน) เหมือนกันทั้งวง
    # ส่วนวงมั่ว ๆ ที่พาดผ่านอาหาร/พื้นหลังจะมีขั้วสลับไปมา -> ค่านี้ต่ำ
    signs = polarity[supported]
    consistency = float(abs(signs.mean())) if signs.size else 0.0
    return frac * (0.55 + 0.45 * consistency)


def _contrast_score(gray: np.ndarray, cx: float, cy: float, r: float) -> float:
    """ในถาดกับนอกถาดควรสว่างต่างกัน (สเตนเลสสว่างกว่าโต๊ะ) — ใช้เป็นตัวช่วยรอง"""
    h, w = gray.shape
    yy, xx = np.ogrid[:h, :w]
    d2 = (xx - cx) ** 2 + (yy - cy) ** 2
    inside = gray[d2 <= (0.8 * r) ** 2]
    ring = gray[(d2 >= (1.08 * r) ** 2) & (d2 <= (1.35 * r) ** 2)]
    if inside.size < 50 or ring.size < 50:
        return 0.0
    return float(min(abs(float(inside.mean()) - float(ring.mean())) / 45.0, 1.0))


# --------------------------------------------------------------------------
# วิธี a: HoughCircles
# --------------------------------------------------------------------------
def _detect_hough(gray: np.ndarray, grads) -> list[TrayCircle]:
    """
    หาวงกลมด้วย HoughCircles แล้วคืน "ผู้สมัคร" ทั้งหมดที่ผ่านเกณฑ์รูปทรง

    param2 คือ threshold ของ accumulator — ค่าสูง = เข้มงวด เจอยาก, ต่ำ = เจอเยอะแต่มั่ว
    เราไล่หลายค่าเพื่อเก็บผู้สมัครให้ครบ แล้วค่อยตัดสินด้วยหลักฐานขอบในภาพ
    (การใช้ค่าเดียวตายตัวไม่นิ่งข้ามสภาพแสง ซึ่งเป็นข้อจำกัดที่รู้กันของ Hough)
    """
    h, w = gray.shape
    short = min(h, w)
    blurred = cv2.medianBlur(gray, 7)
    candidates: list[TrayCircle] = []

    for param2 in (120, 100, 80, 60, 45, 32):
        circles = cv2.HoughCircles(
            blurred, cv2.HOUGH_GRADIENT, dp=1.2,
            minDist=short / 4,
            param1=120, param2=param2,
            minRadius=int(MIN_RADIUS_RATIO * short),
            maxRadius=int(MAX_RADIUS_RATIO * short),
        )
        if circles is None:
            continue
        for cx, cy, r in np.round(circles[0]).astype(int):
            if not _is_plausible(cx, cy, r, gray.shape):
                continue
            candidates.append(_make_candidate(gray, grads, cx, cy, r, "hough"))
    return candidates


def _make_candidate(gray, grads, cx, cy, r, method: str) -> TrayCircle:
    """รวมคะแนนทั้ง 3 ทาง — น้ำหนักหลักอยู่ที่ 'ขอบมีจริงไหม'"""
    gx, gy, mag, strong = grads
    edge = _edge_support(gx, gy, mag, strong, cx, cy, r)
    geom = _geometry_score(cx, cy, r, gray.shape)
    contrast = _contrast_score(gray, cx, cy, r)
    score = 0.60 * edge + 0.25 * geom + 0.15 * contrast
    return TrayCircle(int(cx), int(cy), int(r), method, float(score))


def _refine(gray, grads, cand: TrayCircle) -> TrayCircle:
    """
    ขัดเกลาวงที่ได้มาแบบหยาบ ๆ ให้เกาะขอบถาดจริง

    จำเป็นมาก เพราะ HoughCircles เก่งเรื่องบอก "แถวนี้มีวงกลม" แต่รัศมีที่คืนมา
    มักคลาดเยอะ (เจอบ่อยว่าใหญ่เกินจริง 50-100%) ถ้าเอาไปใช้ตรง ๆ จะครอบพื้นหลัง
    เข้ามาด้วย ตรงนี้จึงค้นหาซ้ำแบบ coordinate descent โดยยึด 'ขอบที่ชี้ตามแนวรัศมี'
    เป็นเกณฑ์: หา r ที่ดีสุด -> ขยับจุดศูนย์กลาง -> หา r ละเอียดอีกรอบ
    """
    gx, gy, mag, strong = grads
    h, w = gray.shape
    short = min(h, w)
    r_lo, r_hi = int(MIN_RADIUS_RATIO * short), int(MAX_RADIUS_RATIO * short)

    def support(cx, cy, r):
        return _edge_support(gx, gy, mag, strong, cx, cy, r)

    cx, cy, r = cand.cx, cand.cy, cand.r

    # สลับ "หา r ที่ดีสุด" กับ "ไต่หาจุดศูนย์กลาง" หลายรอบ
    # การไต่ใช้ while-loop ต่อ step เพื่อให้เดินไกลเท่าไรก็ได้ — จำเป็นเมื่อถาดวางเยื้อง
    # ศูนย์เยอะ ๆ (จุดตั้งต้นอาจห่างจากถาดจริงเป็นร้อยพิกเซล)
    for round_no in range(3):
        span = (0.45, 1.6) if round_no == 0 else (0.8, 1.25)
        lo, hi = max(r_lo, int(r * span[0])), min(r_hi, int(r * span[1]))
        if lo <= hi:
            r = max(range(lo, hi + 1, 2), key=lambda rr: support(cx, cy, rr), default=r)

        for step in (32, 16, 8, 4, 2, 1):
            while True:
                base = support(cx, cy, r)
                best_c, best_s = (cx, cy), base
                for dx in (-step, 0, step):
                    for dy in (-step, 0, step):
                        if dx == 0 and dy == 0:
                            continue
                        s = support(cx + dx, cy + dy, r)
                        if s > best_s:
                            best_s, best_c = s, (cx + dx, cy + dy)
                if best_c == (cx, cy):
                    break
                cx, cy = best_c

    # เก็บรัศมีให้ละเอียดอีกรอบด้วยจุดศูนย์กลางสุดท้าย
    lo, hi = max(r_lo, r - 30), min(r_hi, r + 30)
    if lo <= hi:
        r = max(range(lo, hi + 1), key=lambda rr: support(cx, cy, rr), default=r)

    if not _is_plausible(cx, cy, r, gray.shape):
        return cand
    return _make_candidate(gray, grads, cx, cy, r, cand.method)


# --------------------------------------------------------------------------
# วิธี b (fallback): threshold + largest contour + minEnclosingCircle
# --------------------------------------------------------------------------
def _detect_contour(gray: np.ndarray, grads) -> list[TrayCircle]:
    """
    ถาดสเตนเลสเป็นก้อนสีเทาสว่างก้อนใหญ่กลางภาพ — แยกด้วย Otsu แล้วหา contour ใหญ่สุด

    ลองทั้งภาพ threshold ปกติและภาพกลับสี เพราะบางฉากพื้นหลังสว่างกว่าถาด
    (โต๊ะขาว/ผ้าปูขาว) ถ้าเลือกผิดขั้วจะได้พื้นหลังแทนถาด
    """
    h, w = gray.shape
    blurred = cv2.GaussianBlur(gray, (9, 9), 0)
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # ปิดรูที่เกิดจากอาหารในหลุม ให้ถาดกลายเป็นก้อนตัน ๆ ก่อนหา contour
    k = max(9, int(min(h, w) * 0.02) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))

    candidates: list[TrayCircle] = []
    for binary in (otsu, cv2.bitwise_not(otsu)):
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        closed = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
            (cx, cy), r = cv2.minEnclosingCircle(cnt)
            if not _is_plausible(cx, cy, r, gray.shape):
                continue
            # fill ratio: contour เต็มวงแค่ไหน — ถาดกลมจะเต็ม รูปร่างแปลก ๆ จะไม่เต็ม
            fill = cv2.contourArea(cnt) / (np.pi * r * r) if r > 0 else 0.0
            if fill < 0.35:                     # ยาว ๆ แบน ๆ ไม่ใช่ถาดกลมแน่ ๆ
                continue
            cand = _make_candidate(gray, grads, cx, cy, r, "contour")
            candidates.append(cand._replace(score=float(cand.score * (0.85 + 0.15 * fill))))

            # วงจาก "พื้นที่เทียบเท่า" อีกตัว: minEnclosingCircle ถูกยืดง่ายมากถ้า contour
            # มีติ่งยื่นออกไป (ถาดติดกับของสว่างข้าง ๆ) ส่วนวงจากพื้นที่จะทนติ่งได้ดีกว่า
            m = cv2.moments(cnt)
            if m["m00"] > 0:
                ex, ey = m["m10"] / m["m00"], m["m01"] / m["m00"]
                er = float(np.sqrt(cv2.contourArea(cnt) / np.pi))
                if _is_plausible(ex, ey, er, gray.shape):
                    candidates.append(_make_candidate(gray, grads, ex, ey, er, "contour"))
    return candidates


# --------------------------------------------------------------------------
# วิธี c: โหวตจุดศูนย์กลางจากทิศของ gradient
# --------------------------------------------------------------------------
def _vote_center(gray: np.ndarray, grads, max_points: int = 6000) -> list[TrayCircle]:
    """
    หาจุดศูนย์กลางแบบ accumulator: ขอบของวงกลมมี gradient ชี้เข้า/ออกจากจุดศูนย์กลางเสมอ
    ดังนั้นให้ทุกพิกเซลขอบ "โหวต" ไปตามแนว gradient ที่ระยะ r ต่าง ๆ จุดที่โดนโหวตหนาสุด
    คือจุดศูนย์กลางของวง

    ต่างจาก HoughCircles ตรงที่เราสะสมโหวตเฉพาะ "จุดศูนย์กลาง" โดยไม่สนรัศมี ทำให้
    โหวตจากทุกรัศมีมารวมกองเดียว → ทนต่อกรณีรัศมีไม่รู้ล่วงหน้าและถาดวางเยื้องศูนย์
    ได้ดีกว่ามาก (ซึ่งเป็นสองเคสที่ HoughCircles พลาดบ่อยที่สุด)
    """
    gx, gy, mag, strong = grads
    h, w = gray.shape
    short = min(h, w)

    ys, xs = np.nonzero(mag > strong)
    if ys.size == 0:
        return []
    if ys.size > max_points:                      # จำกัดงานให้คงที่ ไม่ให้ภาพรก ๆ ช้าเกิน
        pick = np.argsort(mag[ys, xs])[-max_points:]
        ys, xs = ys[pick], xs[pick]

    m = mag[ys, xs]
    nx, ny = gx[ys, xs] / m, gy[ys, xs] / m
    acc = np.zeros(h * w, dtype=np.float32)

    r_lo, r_hi = int(MIN_RADIUS_RATIO * short), int(MAX_RADIUS_RATIO * short)
    for r in range(r_lo, r_hi + 1, max(2, (r_hi - r_lo) // 40)):
        for sign in (1.0, -1.0):                  # ไม่รู้ว่าข้างในสว่างหรือมืดกว่า โหวตทั้งสองทาง
            cxv = np.round(xs + sign * r * nx).astype(np.int32)
            cyv = np.round(ys + sign * r * ny).astype(np.int32)
            ok = (cxv >= 0) & (cxv < w) & (cyv >= 0) & (cyv < h)
            if ok.any():
                acc += np.bincount(cyv[ok] * w + cxv[ok], minlength=h * w).astype(np.float32)

    acc2d = cv2.GaussianBlur(acc.reshape(h, w), (0, 0), short * 0.02)
    out = []
    for _ in range(2):                            # เก็บ 2 จุดยอด เผื่อจุดแรกเป็นของปลอม
        _, _, _, (px, py) = cv2.minMaxLoc(acc2d)
        if _is_plausible(px, py, 0.33 * short, gray.shape):
            out.append(TrayCircle(int(px), int(py), int(0.33 * short), "vote", 0.0))
        cv2.circle(acc2d, (px, py), int(short * 0.1), 0.0, -1)   # ลบยอดนี้แล้วหายอดถัดไป
    return out


# --------------------------------------------------------------------------
# API หลัก
# --------------------------------------------------------------------------
#: คะแนนขั้นต่ำที่จะยอมรับผลจาก Hough โดยไม่ต้องไปลองวิธี fallback
HOUGH_TRUST = 0.62
#: ต่ำกว่านี้ถือว่า "หาไม่เจอ" ดีกว่าเชื่อวงมั่ว ๆ แล้วไปตัดอาหารจริงทิ้ง
MIN_ACCEPT = 0.42


#: ย่อภาพก่อนหาวงถาด — ความแม่นแทบไม่ต่าง แต่เร็วขึ้นหลายเท่า (สำคัญเพราะเว็บเรียกทุก request)
WORK_SHORT_SIDE = 320

# ---- เกณฑ์ตัดสินว่า "เห็นถาดเต็มวง" หรือไม่ ----
#: วงถาดต้องครอบพื้นที่อย่างน้อยเท่านี้ของภาพ ต่ำกว่านี้แปลว่าน่าจะไปจับแค่ "หลุมเดียว"
MIN_TRAY_COVERAGE = 0.12
#: ขอบวงทะลุออกนอกเฟรมได้ไม่เกินกี่ด้าน (ถ่ายใกล้จนถาดล้นเฟรมจะทะลุ 2-4 ด้าน)
MAX_CLIPPED_SIDES = 1
#: คะแนนขั้นต่ำที่จะเชื่อว่าเป็นถาดจริง
MIN_TRAY_SCORE = 0.52


class TrayRegion(NamedTuple):
    """
    ผลการหา "พื้นที่ทำงาน" ของภาพ

    mode:
      full_tray  -> เห็นถาดเต็มวง ใช้วงนี้กรอง detection นอกถาดทิ้งได้
      full_frame -> ไม่มั่นใจ/ถาดล้นเฟรม -> ใช้ทั้งภาพเป็นพื้นที่ทำงาน "ไม่กรองอะไรทิ้ง"

    การมี full_frame เป็นทางถอยสำคัญมาก: ก่อนหน้านี้ถ้าถ่ายใกล้จนถาดล้นเฟรม
    ระบบจะไปจับได้แค่หลุมเดียวแล้ว "กรอง detection ที่เหลือทิ้งหมด" ซึ่งแย่กว่าการไม่กรองเลย
    """
    circle: TrayCircle | None
    mode: str
    reason: str

    @property
    def crop(self) -> TrayCircle | None:
        """วงที่จะเอาไปกรอง detection — None = ไม่กรอง (โหมด full_frame)"""
        return self.circle if self.mode == "full_tray" else None

    @property
    def is_full_tray(self) -> bool:
        return self.mode == "full_tray"


def _clipped_sides(circle: TrayCircle, shape: tuple[int, int]) -> list[str]:
    """วงล้นออกนอกเฟรมกี่ด้าน (ใช้บอกว่าถ่ายใกล้เกินจนถาดไม่อยู่ในภาพครบ)"""
    h, w = shape
    out = []
    if circle.cx - circle.r < 0:
        out.append("ซ้าย")
    if circle.cx + circle.r > w:
        out.append("ขวา")
    if circle.cy - circle.r < 0:
        out.append("บน")
    if circle.cy + circle.r > h:
        out.append("ล่าง")
    return out


def assess_tray(circle: TrayCircle | None, shape: tuple[int, int]) -> tuple[str, str]:
    """ตัดสินว่าจะใช้โหมดไหน — คืน (mode, เหตุผลสำหรับ log/UI)"""
    if circle is None:
        return "full_frame", "หาวงถาดไม่เจอ"

    h, w = shape
    coverage = np.pi * circle.r ** 2 / float(h * w)
    clipped = _clipped_sides(circle, shape)

    if coverage < MIN_TRAY_COVERAGE:
        return "full_frame", (f"วงที่เจอครอบแค่ {coverage*100:.0f}% ของภาพ "
                              "— น่าจะเป็นหลุมเดียว ไม่ใช่ถาดทั้งใบ")
    if len(clipped) > MAX_CLIPPED_SIDES:
        return "full_frame", (f"ขอบวงทะลุออกนอกเฟรม {len(clipped)} ด้าน ({', '.join(clipped)}) "
                              "— ถ่ายใกล้เกินจนถาดล้นเฟรม")
    if circle.score < MIN_TRAY_SCORE:
        return "full_frame", f"ความมั่นใจต่ำ (score {circle.score:.2f})"

    note = f"เห็นถาดเต็มวง ครอบ {coverage*100:.0f}% ของภาพ"
    if clipped:
        note += f" (ล้นเฟรมด้าน{clipped[0]}เล็กน้อย)"
    return "full_tray", note


def detect_tray_region(image: np.ndarray) -> TrayRegion:
    """
    หาพื้นที่ทำงานของภาพ = หาวงถาด แล้วตัดสินว่าเชื่อได้ไหม

    นี่คือฟังก์ชันที่ผู้เรียกควรใช้ (แทน detect_tray_circle ตรง ๆ) เพราะมันรวม
    การตัดสินใจ fallback ไว้ให้แล้ว
    """
    circle = detect_tray_circle(image)
    shape = image.shape[:2]
    mode, reason = assess_tray(circle, shape)
    return TrayRegion(circle, mode, reason)


def detect_tray_circle(image: np.ndarray) -> TrayCircle | None:
    """
    หาวงถาดในภาพ — คืน None ถ้าหาไม่เจอ (ผู้เรียกควร 'ปล่อยผ่าน' ไม่ใช่ทิ้งทั้งภาพ)

    ลำดับตามที่ออกแบบไว้: HoughCircles ก่อน ถ้าผลไม่นิ่งค่อย fallback ไป threshold+contour
    "ไม่นิ่ง" วัดจากคะแนนหลักฐานขอบในภาพ ไม่ใช่แค่ 'Hough คืนค่าอะไรมาไหม' —
    เพราะ Hough มักคืนวงที่รัศมีผิดมาแบบหน้าตาเฉย ถ้าเชื่อดื้อ ๆ จะตัดอาหารจริงทิ้ง
    ถ้าสองวิธีแรกยังไม่ดีพอ มีวิธีที่สาม (โหวตจุดศูนย์กลางจากทิศ gradient) รับอีกชั้น
    """
    if image is None or image.size == 0:
        return None
    full = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image

    # ทำงานบนภาพย่อ แล้วค่อยขยายผลลัพธ์กลับตอนท้าย
    fh, fw = full.shape
    scale = WORK_SHORT_SIDE / min(fh, fw) if min(fh, fw) > WORK_SHORT_SIDE else 1.0
    gray = (cv2.resize(full, (int(fw * scale), int(fh * scale)), interpolation=cv2.INTER_AREA)
            if scale < 1.0 else full)

    # เตรียม gradient ไว้ครั้งเดียว ใช้ให้คะแนนผู้สมัครทุกตัว
    smooth = cv2.GaussianBlur(gray, (5, 5), 0)
    gx = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    # เกณฑ์ "ขอบชัดพอ" — ต้องมีพื้นขั้นต่ำด้วย เพราะภาพที่พื้นหลังเรียบ ๆ
    # ค่า percentile จะออกมาเป็น 0 แล้วทุกพิกเซลกลายเป็น 'ขอบ' จนวัดอะไรไม่ได้เลย
    strong = max(float(np.percentile(mag, 90)), 8.0)
    grads = (gx, gy, mag, strong)

    def dedupe(cands: list[TrayCircle]) -> list[TrayCircle]:
        seen, out = set(), []
        for c in sorted(cands, key=lambda c: -c.score):
            key = (c.cx // 12, c.cy // 12, c.r // 12)
            if key not in seen:
                seen.add(key)
                out.append(c)
        return out[:6]

    # (a) HoughCircles — ใช้บอกว่า "วงอยู่แถวไหน" แล้วขัดเกลารัศมีเอาเอง
    candidates = [_refine(gray, grads, c) for c in dedupe(_detect_hough(gray, grads))]
    best = max(candidates, key=lambda c: c.score) if candidates else None

    # ทำ fallback ต่อเมื่อผลจาก Hough ยังไม่น่าเชื่อพอ (ประหยัดเวลาเมื่อ Hough ทำได้ดีอยู่แล้ว)
    if best is None or best.score < HOUGH_TRUST:
        # (b) threshold + largest contour + minEnclosingCircle
        fallback = [_refine(gray, grads, c) for c in dedupe(_detect_contour(gray, grads))]

        # (c) โหวตจุดศูนย์กลางจากทิศ gradient + จุดกลางภาพเป็นตัวสำรองสุดท้าย
        h, w = gray.shape
        seeds = _vote_center(gray, grads)
        seeds.append(TrayCircle(w // 2, h // 2, int(0.33 * min(h, w)), "center-seed", 0.0))
        fallback += [_refine(gray, grads, s) for s in seeds]

        for cand in fallback:
            if best is None or cand.score > best.score:
                best = cand

    if best is None or best.score < MIN_ACCEPT:
        return None

    # ขยายพิกัดกลับไปที่ resolution ของภาพจริง
    if scale < 1.0:
        inv = 1.0 / scale
        best = best._replace(cx=int(round(best.cx * inv)), cy=int(round(best.cy * inv)),
                             r=int(round(best.r * inv)))
    return best


def draw_tray_circle(canvas: np.ndarray, tray: TrayCircle | None,
                     color=(0, 255, 255), label: bool = True, used: bool = True) -> np.ndarray:
    """
    วาดวงถาดทับภาพ ไว้ตรวจด้วยตาว่าหาวงถูกไหม

    used=False (โหมด full-frame) จะวาดเป็นสีส้มพร้อมกำกับว่าไม่ได้ใช้กรอง
    เพื่อไม่ให้เข้าใจผิดว่าระบบตัดของนอกวงทิ้งไปแล้ว
    """
    if tray is None:
        return canvas
    if not used:
        color = (0, 140, 255)
    thickness = max(2, int(min(canvas.shape[:2]) * 0.004))
    cv2.circle(canvas, (tray.cx, tray.cy), tray.r, color, thickness, cv2.LINE_AA)
    cv2.drawMarker(canvas, (tray.cx, tray.cy), color, cv2.MARKER_CROSS,
                   thickness * 6, thickness)
    if label:
        scale = max(0.5, min(canvas.shape[:2]) / 1200.0)
        tag = "tray" if used else "tray (NOT used - full frame)"
        cv2.putText(canvas, f"{tag}: {tray.method} r={tray.r} score={tray.score:.2f}",
                    (tray.cx - tray.r, max(20, tray.cy - tray.r - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6 * scale, color,
                    max(1, int(2 * scale)), cv2.LINE_AA)
    return canvas


# --------------------------------------------------------------------------
# CLI: ตรวจด้วยตาว่าหาวงถาดถูกไหม
# --------------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="ทดสอบการหาวงถาด แล้ววาดวงทับภาพให้ดู")
    p.add_argument("images", help="ไฟล์ภาพ หรือโฟลเดอร์")
    p.add_argument("--out", default="runs/tray_check", help="โฟลเดอร์เซฟภาพผลลัพธ์")
    p.add_argument("--dim-outside", action="store_true",
                   help="หรี่พื้นที่นอกวงถาดให้มืดลง จะได้เห็นชัดว่าตัดตรงไหน")
    return p.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = iter_images(args.images)
    if not paths:
        raise SystemExit(f"ไม่พบไฟล์ภาพใน {args.images}")

    found = 0
    print(f"[tray] ตรวจ {len(paths)} ภาพ\n")
    for path in paths:
        image = cv2.imread(str(path))
        if image is None:
            print(f"  {path.name}: อ่านภาพไม่ได้")
            continue

        tray = detect_tray_circle(image)
        canvas = image.copy()

        if tray is None:
            print(f"  {path.name}: หาวงถาดไม่เจอ -> จะไม่กรอง detection ในภาพนี้")
        else:
            found += 1
            h, w = image.shape[:2]
            coverage = np.pi * tray.r ** 2 / (h * w)
            print(f"  {path.name}: {tray.method:8s} center=({tray.cx},{tray.cy}) r={tray.r} "
                  f"score={tray.score:.2f} ครอบคลุม {coverage*100:.0f}% ของภาพ")
            if args.dim_outside:
                from tray_common import circle_mask
                mask = circle_mask(image.shape[:2], tray)
                canvas[~mask] = (canvas[~mask] * 0.25).astype(np.uint8)
            canvas = draw_tray_circle(canvas, tray)

        cv2.imwrite(str(out_dir / f"{path.stem}_tray.jpg"), canvas,
                    [cv2.IMWRITE_JPEG_QUALITY, 92])

    print(f"\nหาเจอ {found}/{len(paths)} ภาพ  ->  เซฟไว้ที่ {out_dir}/")
    if found < len(paths):
        print("ภาพที่หาไม่เจอจะถูกประมวลผลแบบไม่กรอง (ปลอดภัยกว่าการทิ้งทั้งภาพ)")


if __name__ == "__main__":
    main()
