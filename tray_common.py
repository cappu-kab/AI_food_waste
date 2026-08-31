"""
ฟังก์ชันกลางที่ใช้ร่วมกันระหว่าง calibrate_reference.py / estimate_waste.py / visualize_prediction.py

หัวใจของไฟล์นี้คือ "หน่วยวัดพื้นที่" ที่ใช้ทั้งระบบ:
เราไม่เก็บพื้นที่เป็น "จำนวนพิกเซลดิบ" เพราะ mask ที่ YOLO คืนมาอาจมี resolution
ไม่เท่าภาพต้นฉบับ (และมีแถบ letterbox ปนมาด้วย) ทำให้ค่าพิกเซลของภาพคนละขนาด
เทียบกันไม่ได้ → เราเก็บเป็น **area fraction** = พื้นที่ mask / พื้นที่เฟรมทั้งภาพ
ซึ่งเป็นค่า 0.0-1.0 ที่ไม่ขึ้นกับ resolution ของภาพเลย
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import NamedTuple

import numpy as np

# ลำดับต้องตรงกับ names ใน data.yaml เป๊ะ ๆ (index 0-4)
CLASS_NAMES = ["rice", "vegetable", "meat", "mixed_dish", "liquid"]

# ชื่อไทยไว้พิมพ์ให้คนอ่านเข้าใจ
CLASS_NAMES_TH = {
    "rice": "ข้าว",
    "vegetable": "ผัก",
    "meat": "เนื้อสัตว์",
    "mixed_dish": "เมนูผสม",
    "liquid": "น้ำ/น้ำแกง",
}

# สีสำหรับวาด overlay (BGR ตามแบบ OpenCV)
CLASS_COLORS_BGR = {
    "rice": (255, 255, 255),      # ขาว
    "vegetable": (60, 200, 60),   # เขียว
    "meat": (60, 60, 220),        # แดง
    "mixed_dish": (0, 165, 255),  # ส้ม
    "liquid": (230, 180, 60),     # ฟ้า
}

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

REFERENCE_FILE = "reference.json"

# ตำแหน่งมาตรฐานของ "โมเดลที่ใช้เสิร์ฟอยู่ตอนนี้" — train_smoke.py จะ copy best.pt มาไว้ที่นี่
DEFAULT_MODEL_PATH = "models/current.pt"

# ค่า default ตอนทดสอบตั้งไว้ต่ำ (0.15) ตั้งใจ:
# โมเดลที่เพิ่งเทรนหรือเทรนน้อยจะให้ confidence ต่ำ ถ้าใช้ 0.40 จะโดนกรองทิ้งหมด
# จนดูเหมือน "ระบบพัง" ทั้งที่จริงแค่ threshold สูงไป
# พอโมเดลนิ่งแล้วค่อยขยับขึ้นด้วย env CONF_THRESHOLD
DEFAULT_CONF = 0.15
DEFAULT_SURE_CONF = 0.60

# ---- การกรอง detection ให้เหลือเฉพาะในวงถาด ----
# detection ต้องซ้อนทับวงถาดอย่างน้อยเท่านี้ถึงจะนับ (0.5 = ครึ่งหนึ่งของ mask อยู่ในถาด)
DEFAULT_MIN_TRAY_OVERLAP = 0.5

# ============================================================================
# การประมาณ "ตารางเซนติเมตร" และ "กรัม"
#
# *** นี่คือการประมาณ ไม่ใช่การวัดจริง — เป็น design decision ที่ตั้งใจ ***
#
# ข้อเท็จจริง: ภาพถ่ายมุมบนให้ได้แค่ "พื้นที่ผิวที่มองเห็น" เราวัดความสูงของกอง
# อาหารไม่ได้เลยจากภาพ 2D ใบเดียว (ข้าวกองสูงกับข้าวเกลี่ยแบนให้พื้นที่เท่ากัน)
# ทางเลือกมีสองทาง:
#   (ก) ไม่รายงานหน่วยน้ำหนักเลย  -> ผู้ใช้เอาไปใช้ต่อไม่ได้
#   (ข) รายงานค่าประมาณ + ติดป้ายกำกับให้ชัดว่าเป็นค่าประมาณ
# เราเลือก (ข) โดยสมมติว่าอาหารมี "ความสูงคงที่" ค่าหนึ่ง แล้วคูณความหนาแน่น
#
#   น้ำหนัก(กรัม) = พื้นที่(ตร.ซม.) x ความสูงสมมติ(ซม.) x ความหนาแน่น(ก./ลบ.ซม.)
#
# ค่าที่ได้จึงคลาดเคลื่อนได้มาก โดยเฉพาะกองที่สูงหรือแบนผิดปกติ
# ห้ามเอาไปอ้างเป็นน้ำหนักจริง ทุกที่ที่แสดงผลต้องมีป้ายกำกับกำกับเสมอ
#
# ถ้าต้องการความแม่นจริง ต้องใช้กล้อง depth (RGB-D) วัดปริมาตร — อยู่นอก scope
# ============================================================================

#: เส้นผ่านศูนย์กลางถาดจริง (ซม.) — วัดถาดที่ใช้จริงแล้วแก้ผ่าน env TRAY_DIAMETER_CM
DEFAULT_TRAY_DIAMETER_CM = 30.0

#: ความสูงของกองอาหารที่สมมติ (ซม.) — env HEIGHT_ASSUMPTION_CM
DEFAULT_HEIGHT_ASSUMPTION_CM = 1.0

#: ความหนาแน่นโดยประมาณต่อชนิดอาหาร (กรัม/ลบ.ซม.) — env DENSITY_<CLASS> เช่น DENSITY_RICE
DENSITY_G_PER_CM3 = {
    "rice": 0.80,        # ข้าวสวยหุงแล้ว มีช่องอากาศระหว่างเม็ด
    "vegetable": 0.55,   # ผักลวก/ผัด โปร่งกว่าเพื่อน
    "meat": 1.00,        # เนื้อสัตว์ใกล้เคียงน้ำ
    "mixed_dish": 0.90,  # เมนูผสม อยู่กลาง ๆ
    "liquid": 1.00,      # น้ำแกง/ซุป ~ น้ำ
}

# ค่า fallback เผื่อยังไม่ได้ calibrate — **เป็นแค่ค่าเดา อย่าใช้ตัดสินใจจริง**
# หน่วย = สัดส่วนพื้นที่ต่อทั้งเฟรม (ดูคำอธิบายหัวไฟล์)
DEFAULT_FULL_REFERENCE = {
    "rice": 0.090,
    "vegetable": 0.030,
    "meat": 0.026,
    "mixed_dish": 0.045,
    "liquid": 0.022,
}


# --------------------------------------------------------------------------
# หาโมเดล / ค่า config (env var override ได้ ไม่ต้องแก้โค้ด)
# --------------------------------------------------------------------------
def resolve_model_path(explicit: str | None = None) -> tuple[str | None, str]:
    """
    หาว่าจะใช้ weight ตัวไหน ตามลำดับความสำคัญนี้ (คืน path พร้อม "ที่มา" ไว้ log)

      1. argument --model ที่ส่งมาตรง ๆ
      2. env var MODEL_PATH          <- วิธีสลับโมเดลโดยไม่ต้องแก้โค้ด
      3. models/current.pt           <- ที่ที่ train_smoke.py วางไว้ให้
      4. best.pt ที่ใหม่ที่สุดใน runs/
      5. ./best.pt

    คืน (None, เหตุผล) ถ้าหาไม่เจอเลย
    """
    if explicit:
        return explicit, "argument --model"

    env_path = os.environ.get("MODEL_PATH")
    if env_path:
        return env_path, "env MODEL_PATH"

    if Path(DEFAULT_MODEL_PATH).exists():
        return DEFAULT_MODEL_PATH, f"ไฟล์ {DEFAULT_MODEL_PATH}"

    runs = sorted(Path("runs").glob("**/weights/best.pt"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    if runs:
        return str(runs[0]), "best.pt ที่ใหม่ที่สุดใน runs/"

    if Path("best.pt").exists():
        return "best.pt", "ไฟล์ ./best.pt"

    return None, "หาไม่เจอ"


def resolve_conf(explicit: float | None = None) -> tuple[float, str]:
    """confidence threshold: argument > env CONF_THRESHOLD > DEFAULT_CONF"""
    if explicit is not None:
        return explicit, "argument --conf"
    env_conf = os.environ.get("CONF_THRESHOLD")
    if env_conf:
        try:
            return float(env_conf), "env CONF_THRESHOLD"
        except ValueError:
            print(f"  [warn] CONF_THRESHOLD='{env_conf}' ไม่ใช่ตัวเลข — ใช้ค่า default แทน")
    return DEFAULT_CONF, "default"


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def resolve_tray_crop(explicit: bool | None = None) -> bool:
    """เปิด/ปิดการกรอง detection นอกวงถาด — env TRAY_CROP (default: เปิด)"""
    if explicit is not None:
        return explicit
    return _env_flag("TRAY_CROP", True)


def resolve_min_overlap() -> float:
    """detection ต้องซ้อนวงถาดอย่างน้อยเท่าไรถึงจะนับ — env TRAY_MIN_OVERLAP"""
    try:
        return float(os.environ.get("TRAY_MIN_OVERLAP") or DEFAULT_MIN_TRAY_OVERLAP)
    except ValueError:
        return DEFAULT_MIN_TRAY_OVERLAP


def resolve_sure_conf(explicit: float | None = None) -> float:
    """เกณฑ์ 'มั่นใจพอ' — ต่ำกว่านี้รายงานว่าไม่แน่ใจ"""
    if explicit is not None:
        return explicit
    try:
        return float(os.environ.get("SURE_CONF", DEFAULT_SURE_CONF))
    except ValueError:
        return DEFAULT_SURE_CONF


# --------------------------------------------------------------------------
# ตรวจสุขภาพโมเดล — จับเคส "เสิร์ฟโมเดลผิดตัว" ให้เจอตั้งแต่ตอน start
# --------------------------------------------------------------------------
class ModelInfo(NamedTuple):
    path: str
    source: str                 # มาจากไหน (argument / env / auto)
    names: dict                 # {index: ชื่อ class} ของโมเดลจริง ๆ
    trained_on: str | None      # dataset ที่ใช้เทรน (อ่านจาก checkpoint)
    trained_epochs: int | None
    trained_date: str | None
    problems: list[str]         # ปัญหาร้ายแรง — ผลลัพธ์จะเป็น 0 หมด
    warnings: list[str]         # น่าสงสัย แต่ยังพอใช้ได้
    is_project_model: bool      # class ตรงกับ 5 class ของโปรเจกต์ครบไหม


def inspect_model(model, path: str, source: str) -> ModelInfo:
    """
    ดึงข้อมูลจริงจากโมเดลที่โหลดมาแล้ว + วินิจฉัยว่ามันตรงกับโปรเจกต์นี้ไหม

    เคสที่จับได้:
      - โมเดล COCO ตัว stock (80 class: person/bicycle/car...) -> ตรวจอาหารเราไม่เจอแน่นอน
      - จำนวน/ชื่อ class ไม่ตรงกับ 5 class ของเรา
      - ชื่อตรงแต่ "ลำดับ index" ไม่ตรง -> อันตรายที่สุด เพราะผลจะสลับ class แบบเงียบ ๆ
      - เทรนมาจาก dataset คนละชุด (อ่าน train_args.data จาก checkpoint)
    """
    names = dict(getattr(model, "names", {}) or {})
    ckpt = getattr(model, "ckpt", None) or {}
    train_args = ckpt.get("train_args") or {}

    info = dict(
        path=path, source=source, names=names,
        trained_on=train_args.get("data"),
        trained_epochs=train_args.get("epochs"),
        trained_date=ckpt.get("date"),
        problems=[], warnings=[], is_project_model=False,
    )

    values = [str(v) for v in names.values()]
    expected = list(CLASS_NAMES)
    info["is_project_model"] = set(values) == set(expected)

    if len(names) == 80 and "person" in values:
        info["problems"].append(
            "โมเดลนี้เป็น YOLO ตัว stock ที่เทรนกับ COCO (80 class: person/car/bowl/...) "
            "ยังไม่ได้เทรนกับ 5 class ของโปรเจกต์ — ผลจะเป็น 0 ทั้งหมด"
        )
    elif values != expected:
        missing = [c for c in expected if c not in values]
        extra = [v for v in values if v not in expected]
        if missing:
            info["problems"].append(
                f"โมเดลไม่มี class เหล่านี้: {', '.join(missing)} "
                f"(โมเดลมี {len(names)} class: {', '.join(values[:8])}) — class ที่ขาดจะได้ 0 เสมอ"
            )
        elif extra:
            info["warnings"].append(f"โมเดลมี class เกินมา: {', '.join(extra)} (จะถูกข้าม)")
        else:
            # ชื่อครบแต่ลำดับสลับ — ระบบยังอ่านผลถูกเพราะ map ด้วยชื่อ ไม่ใช่ index
            info["warnings"].append(
                f"ลำดับ class ในโมเดลไม่ตรงกับ data.yaml (โมเดล: {', '.join(values)}) "
                "— ระบบ map ด้วยชื่อให้แล้ว แต่ควรแก้ data.yaml ให้ตรงกัน"
            )

    return ModelInfo(**info)


def format_model_report(info: ModelInfo) -> str:
    """ข้อความสรุปสภาพโมเดลสำหรับ log ตอน start — ให้เห็นปัญหาโดยไม่ต้องเดา"""
    # แสดงชื่อ class "ทั้งหมด" แต่ตัดบรรทัดไม่ให้ยาวเกินอ่าน (COCO มี 80 ตัว)
    all_names = [str(v) for v in info.names.values()]
    wrapped, line = [], "  class       : "
    for i, name in enumerate(all_names):
        piece = name + (", " if i < len(all_names) - 1 else "")
        if len(line) + len(piece) > 88:
            wrapped.append(line)
            line = " " * 16 + piece
        else:
            line += piece
    wrapped.append(line)

    lines = [
        "─" * 72,
        f"  โมเดล      : {info.path}",
        f"  ที่มาของ path: {info.source}",
        f"  จำนวน class : {len(info.names)}",
        *wrapped,
    ]
    if info.trained_on:
        lines.append(f"  เทรนจาก     : {info.trained_on}"
                     + (f"  ({info.trained_epochs} epochs)" if info.trained_epochs else ""))
    if info.trained_date:
        lines.append(f"  เทรนเมื่อ    : {info.trained_date}")

    if info.is_project_model and not info.problems:
        lines.append("  สถานะ       : ✅ โมเดล fine-tuned ของโปรเจกต์ (class ตรงครบทั้ง 5)")

    for w in info.warnings:
        lines += ["", f"  [warn] {w}"]

    for p in info.problems:
        lines += [
            "",
            "  " + "!" * 68,
            "  !!  โมเดลนี้ยังไม่ได้เทรนกับ 5 class ของโปรเจกต์ — ผลจะเป็น 0 ทั้งหมด  !!",
            "  " + "!" * 68,
            f"  เหตุผล: {p}",
            "  วิธีแก้: เทรนก่อน (python train.py) แล้วชี้ MODEL_PATH ไปที่ best.pt ที่ได้",
            "          หรือรัน python train_smoke.py เพื่อพิสูจน์ว่า loop ทำงานครบ",
        ]

    lines.append("─" * 72)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# โมเดล / การ predict
# --------------------------------------------------------------------------
def load_model(model_path: str):
    """โหลดโมเดล YOLO (import ข้างในฟังก์ชันเพื่อให้ --help เร็วและไม่พังถ้ายังไม่มี torch)"""
    from ultralytics import YOLO

    if not Path(model_path).exists():
        raise FileNotFoundError(
            f"ไม่พบไฟล์โมเดล: {model_path}\n"
            "  → เทรนก่อนด้วย `python train.py` แล้ว weight จะอยู่ที่ "
            "runs/<project>/<name>/weights/best.pt"
        )
    return YOLO(model_path)


def predict_one(model, image, conf: float = 0.40, imgsz: int = 640, device: str | None = None):
    """
    รัน inference 1 ภาพ

    สำคัญ: ใช้ retina_masks=True เพื่อให้ mask ที่ได้มี resolution เท่ากับภาพต้นฉบับ
    (ไม่ถูกย่อลงเหลือ 640 และไม่มีแถบ letterbox ปน) → นับพื้นที่แล้วตรงกับความจริง
    """
    kwargs = dict(conf=conf, imgsz=imgsz, retina_masks=True, verbose=False)
    if device is not None:
        kwargs["device"] = device
    return model.predict(image, **kwargs)[0]


# --------------------------------------------------------------------------
# การนับพื้นที่ mask
# --------------------------------------------------------------------------
class TrayCircle(NamedTuple):
    """วงถาดที่ตรวจเจอ — พิกัดอยู่ในระบบพิกัดของภาพต้นฉบับ"""
    cx: int
    cy: int
    r: int
    method: str        # 'hough' | 'contour' — วิธีที่หาเจอ
    score: float       # 0-1 ความน่าเชื่อถือแบบ heuristic


def circle_mask(shape: tuple[int, int], circle: TrayCircle) -> np.ndarray:
    """
    สร้าง mask วงกลม (bool) ขนาด shape=(h, w)

    รับ shape มาแยกต่างหากเพราะ mask ของ YOLO อาจคนละ resolution กับภาพต้นฉบับ
    → จะ scale พิกัดวงให้ตรงกับ shape ที่ขอมาโดยอัตโนมัติ (ต้องส่ง orig_shape มาด้วย
    ผ่าน scale_circle ถ้าจำเป็น) ที่นี่ถือว่า circle อยู่ในระบบพิกัดเดียวกับ shape แล้ว
    """
    h, w = shape
    yy, xx = np.ogrid[:h, :w]
    return (xx - circle.cx) ** 2 + (yy - circle.cy) ** 2 <= circle.r ** 2


def scale_circle(circle: TrayCircle, from_shape: tuple[int, int],
                 to_shape: tuple[int, int]) -> TrayCircle:
    """แปลงพิกัดวงถาดจาก resolution หนึ่งไปอีก resolution หนึ่ง"""
    if from_shape == to_shape:
        return circle
    sy = to_shape[0] / from_shape[0]
    sx = to_shape[1] / from_shape[1]
    return circle._replace(cx=int(round(circle.cx * sx)), cy=int(round(circle.cy * sy)),
                           r=int(round(circle.r * (sx + sy) / 2)))


#: class ที่ "ลอย/จมอยู่ในน้ำได้" — ใช้ตรวจว่ามีเนื้อ/ผักเหลือในน้ำซุปไหม
FLOATS_IN_LIQUID = ("meat", "vegetable", "mixed_dish")


class FrameStats(NamedTuple):
    """ผลสรุปของ 1 ภาพ — ทุก dict ใช้ชื่อ class เป็น key"""
    fractions: dict[str, float]   # สัดส่วนพื้นที่ต่อทั้งเฟรม (0.0-1.0)
    confs: dict[str, float]       # confidence สูงสุดของ class นั้น (0.0 ถ้าไม่เจอ)
    counts: dict[str, int]        # จำนวน instance ที่เจอ (หลังกรองนอกถาดแล้ว)
    unknown: dict[str, int]       # class ที่โมเดลเจอแต่ไม่ใช่ของโปรเจกต์ -> จำนวน
    n_detections: int             # จำนวน detection ทั้งหมดที่ผ่าน conf (รวม unknown)
    outside_tray: dict[str, int]  # detection ที่ถูกทิ้งเพราะอยู่นอกวงถาด -> จำนวน
    in_liquid: dict[str, int]     # instance ที่ลอยอยู่ในโซน liquid -> จำนวน
    in_liquid_fraction: dict[str, float]  # พื้นที่ "ที่มองเห็นบนผิวน้ำ" ของ class นั้น


def class_area_fractions(result, tray: TrayCircle | None = None,
                         min_overlap: float = DEFAULT_MIN_TRAY_OVERLAP) -> FrameStats:
    """
    สรุปผล 1 ภาพ

    การ map class ใช้ "ชื่อ" จาก result.names ไม่ใช่ index ตรง ๆ:
    ถ้าลำดับ class ในโมเดลไม่ตรงกับ data.yaml การเชื่อด้วย index จะทำให้ผลสลับ
    class แบบเงียบ ๆ (ข้าวไปโผล่เป็นเนื้อ) ซึ่งหาสาเหตุยากมาก — map ด้วยชื่อปลอดภัยกว่า
    ส่วน class ที่ไม่ใช่ของโปรเจกต์ (เช่นเสิร์ฟโมเดล COCO ผิดตัว) จะถูกเก็บไว้ใน
    `unknown` เพื่อให้บอกผู้ใช้ได้ว่า "เจอของ แต่เป็นคนละ class" ไม่ใช่ "ไม่เจออะไรเลย"

    ถ้าส่ง `tray` มาด้วย จะกรอง detection ที่อยู่นอกวงถาดทิ้ง (แก้ปัญหา mask ไปเกาะ
    พื้นหลัง/เสื้อนักเรียน/ขอบภาพ) ด้วยเกณฑ์ 2 ชั้น:
      1. ถ้าพื้นที่ mask ซ้อนกับวงถาดน้อยกว่า min_overlap -> ทิ้งทั้งชิ้น
      2. ชิ้นที่ผ่าน จะถูก "ตัด" ให้เหลือเฉพาะส่วนที่อยู่ในวง ก่อนนำไปคิดพื้นที่
    ชั้นที่ 2 สำคัญ: ชิ้นที่ล้นออกนอกถาดนิดหน่อยจะไม่เอาส่วนที่ล้นมาคิดเป็นอาหาร
    ส่ง tray=None (โหมด full-frame) = ไม่กรองอะไรเลย ใช้ทั้งภาพเป็นพื้นที่ทำงาน

    *** เรื่องของที่อยู่ในน้ำซุป ***
    เราจงใจ **ไม่บังคับว่า 1 พิกเซล = 1 class** — mask ของ meat/vegetable ซ้อนทับ
    พื้นที่ liquid ได้ (YOLO-seg รองรับ overlap อยู่แล้ว) และตอนคิดพื้นที่เรา
    **ไม่หักส่วนที่ซ้อนออกจาก liquid** เพราะน้ำที่อยู่ใต้เนื้อก็ยังเป็นน้ำอยู่
    ผลลัพธ์จึงรายงานแยกกัน: liquid X% และ "ในนั้นเห็นเนื้อ/ผักเท่านี้"

    ข้อจำกัดที่ต้องรู้: ตัวเลข in_liquid_fraction คือ **พื้นที่ที่โผล่พ้นผิวน้ำเท่านั้น**
    ของที่จมมิดอยู่ใต้น้ำเรามองไม่เห็นและ **ไม่พยายามเดา** — ตัวเลขนี้จึงเป็น
    ค่าต่ำกว่าความจริงเสมอ ห้ามเอาไปตีความว่า "วัดปริมาณเนื้อในซุปได้ครบ"

    จุดที่ต้องระวัง: ถ้ามีหลาย instance ของ class เดียวกันแล้ว mask ซ้อนกัน
    การ "บวกพื้นที่ตรง ๆ" จะนับซ้ำ → เราใช้ union (OR) ต่อ class แทน
    """
    fractions = {c: 0.0 for c in CLASS_NAMES}
    confs = {c: 0.0 for c in CLASS_NAMES}
    counts = {c: 0 for c in CLASS_NAMES}
    unknown: dict[str, int] = {}
    outside: dict[str, int] = {}
    in_liquid: dict[str, int] = {}
    in_liquid_frac: dict[str, float] = {}

    if result.masks is None or len(result.masks) == 0:
        return FrameStats(fractions, confs, counts, unknown, 0, outside,
                          in_liquid, in_liquid_frac)

    masks = result.masks.data.cpu().numpy()          # (N, H, W) ค่า 0.0/1.0
    classes = result.boxes.cls.cpu().numpy().astype(int)
    scores = result.boxes.conf.cpu().numpy()
    model_names = dict(getattr(result, "names", {}) or {})

    n, mask_h, mask_w = masks.shape
    frame_area = float(mask_h * mask_w)

    # เตือนถ้า mask resolution ไม่ตรงภาพต้นฉบับ (ปกติ retina_masks=True จะตรง)
    orig_h, orig_w = result.orig_shape
    if (mask_h, mask_w) != (orig_h, orig_w):
        print(
            f"  [warn] mask resolution ({mask_h}x{mask_w}) ไม่เท่าภาพต้นฉบับ "
            f"({orig_h}x{orig_w}) — ยังใช้ได้เพราะเราคิดเป็นสัดส่วน แต่ควรเช็ก retina_masks"
        )

    # วงถาดอยู่ในพิกัดภาพต้นฉบับ ต้อง scale ให้ตรงกับ resolution ของ mask ก่อน
    tray_area_mask = None
    if tray is not None:
        scaled = scale_circle(tray, (orig_h, orig_w), (mask_h, mask_w))
        tray_area_mask = circle_mask((mask_h, mask_w), scaled)

    # ---- รอบที่ 1: เก็บ instance ที่ผ่านการกรองนอกถาดแล้ว ----
    kept: list[tuple[str, np.ndarray]] = []
    for i in range(n):
        cls_id = int(classes[i])
        # ชื่อจากโมเดลก่อน ถ้าโมเดลไม่มีชื่อค่อย fallback ไปที่ลำดับใน data.yaml
        name = model_names.get(cls_id)
        if name is None:
            name = CLASS_NAMES[cls_id] if 0 <= cls_id < len(CLASS_NAMES) else f"class_{cls_id}"

        if name not in fractions:
            unknown[name] = unknown.get(name, 0) + 1
            continue

        binary = masks[i] > 0.5
        if tray_area_mask is not None:
            area = int(binary.sum())
            inside = binary & tray_area_mask
            ratio = int(inside.sum()) / area if area else 0.0
            if ratio < min_overlap:
                outside[name] = outside.get(name, 0) + 1
                continue
            binary = inside          # ตัดส่วนที่ล้นออกนอกถาดทิ้ง

        kept.append((name, binary))
        counts[name] += 1
        confs[name] = max(confs[name], float(scores[i]))

    # ---- รอบที่ 2: รวมเป็น union ต่อ class (ไม่หักพื้นที่ที่ซ้อนกันข้าม class) ----
    unions = {c: np.zeros((mask_h, mask_w), dtype=bool) for c in CLASS_NAMES}
    for name, binary in kept:
        unions[name] |= binary
    for name in CLASS_NAMES:
        fractions[name] = float(unions[name].sum()) / frame_area

    # ---- รอบที่ 3: หาว่ามีเนื้อ/ผักชิ้นไหน "อยู่ในโซนน้ำ" บ้าง ----
    liquid_mask = unions.get("liquid")
    if liquid_mask is not None and liquid_mask.any():
        for name, binary in kept:
            if name not in FLOATS_IN_LIQUID or not binary.any():
                continue
            ys, xs = np.nonzero(binary)
            cy, cx = int(ys.mean()), int(xs.mean())
            # ใช้ centroid เป็นเกณฑ์ว่า "ชิ้นนี้อยู่ในน้ำ" — ง่ายและตีความตรงไปตรงมา
            # (ถ้าใช้สัดส่วนพื้นที่ซ้อน ชิ้นที่แค่ขอบแตะน้ำจะถูกนับด้วย ซึ่งไม่ใช่)
            if liquid_mask[cy, cx]:
                in_liquid[name] = in_liquid.get(name, 0) + 1
                # พื้นที่เฉพาะส่วนที่ทับโซนน้ำ = ส่วนที่ "เห็นโผล่บนผิวน้ำ"
                overlap = float((binary & liquid_mask).sum()) / frame_area
                in_liquid_frac[name] = in_liquid_frac.get(name, 0.0) + overlap

    return FrameStats(fractions, confs, counts, unknown, n, outside,
                      in_liquid, in_liquid_frac)


def no_detection_notice(stats: FrameStats, conf: float) -> str | None:
    """
    ข้อความอธิบายเมื่อ "ไม่ได้อะไรเลย" — กันผู้ใช้เข้าใจผิดว่าระบบพัง
    คืน None ถ้าเจอของในโปรเจกต์ตามปกติ
    """
    if sum(stats.counts.values()) > 0:
        return None

    if stats.unknown:
        found = ", ".join(f"{k} ({v})" for k, v in sorted(stats.unknown.items()))
        return (f"เจอวัตถุ {stats.n_detections} ชิ้น แต่เป็น class นอกโปรเจกต์: {found} "
                "— แปลว่าโมเดลที่เสิร์ฟอยู่ไม่ใช่โมเดลของงานนี้ (น่าจะเป็น YOLO ตัว stock)")

    return (f"ไม่พบวัตถุเลยที่ conf ≥ {conf:.2f} — อาจเป็นเพราะโมเดลยังไม่ได้เทรนกับ class เหล่านี้ "
            "หรือเทรนมาจากภาพคนละแบบ ลองลด confidence ลงก่อน ถ้ายังไม่เจอให้ตรวจว่าเสิร์ฟโมเดลถูกตัวไหม")


def resolve_tray_diameter_cm() -> float:
    """เส้นผ่านศูนย์กลางถาดจริงเป็น ซม. — env TRAY_DIAMETER_CM"""
    try:
        return float(os.environ.get("TRAY_DIAMETER_CM") or DEFAULT_TRAY_DIAMETER_CM)
    except ValueError:
        return DEFAULT_TRAY_DIAMETER_CM


def resolve_height_cm() -> float:
    """ความสูงกองอาหารที่สมมติ — env HEIGHT_ASSUMPTION_CM"""
    try:
        return float(os.environ.get("HEIGHT_ASSUMPTION_CM") or DEFAULT_HEIGHT_ASSUMPTION_CM)
    except ValueError:
        return DEFAULT_HEIGHT_ASSUMPTION_CM


def resolve_density(name: str) -> float:
    """ความหนาแน่นของ class นั้น — override ได้ด้วย env เช่น DENSITY_RICE=0.75"""
    env = os.environ.get(f"DENSITY_{name.upper()}")
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    return DENSITY_G_PER_CM3.get(name, 1.0)


def cm2_per_pixel(tray: TrayCircle | None, diameter_cm: float | None = None) -> float | None:
    """
    หา "กี่ ตร.ซม. ต่อ 1 พิกเซล" โดยใช้วงถาดเป็นไม้บรรทัด

    ต้องรู้ขนาดจริงของของบางอย่างในภาพถึงจะแปลงหน่วยได้ — เราใช้ "ถาด" เพราะเป็น
    ของชิ้นเดียวในภาพที่ขนาดคงที่และวัดได้ง่าย

    คืน None ถ้าไม่มีวงถาด (โหมด full-frame) — กรณีนั้น **ห้ามเดา** เพราะไม่มี
    อะไรให้เทียบขนาดเลย รายงานเป็นพิกเซลอย่างเดียว
    """
    if tray is None or tray.r <= 0:
        return None
    d = diameter_cm if diameter_cm is not None else resolve_tray_diameter_cm()
    cm_per_px = (d / 2.0) / float(tray.r)     # รัศมีจริง(ซม.) ต่อ รัศมี(พิกเซล)
    return cm_per_px ** 2


def estimate_weight_g(area_cm2: float, name: str, height_cm: float | None = None) -> float:
    """
    ประมาณน้ำหนักจากพื้นที่ผิว — ดูคำอธิบายข้อจำกัดที่หัวไฟล์

    สมมติว่าอาหารเป็นแท่งความสูงคงที่: ปริมาตร = พื้นที่ x ความสูง
    แล้วคูณความหนาแน่นของอาหารชนิดนั้น
    """
    h = height_cm if height_cm is not None else resolve_height_cm()
    return area_cm2 * h * resolve_density(name)


def fraction_to_px(fraction: float, result) -> int:
    """แปลงสัดส่วนพื้นที่กลับเป็นจำนวนพิกเซลของภาพต้นฉบับ (ไว้พิมพ์ให้คนดูเฉย ๆ)"""
    orig_h, orig_w = result.orig_shape
    return int(round(fraction * orig_h * orig_w))


def remaining_percent(fraction: float, ref_fraction: float) -> float | None:
    """
    % ที่เหลือ = พื้นที่ที่วัดได้ / พื้นที่ตอนถาดเต็ม * 100
    คืน None ถ้ายังไม่มีค่า reference (จะได้ไม่เผลอรายงานเลข 0% ทั้งที่แค่ไม่รู้)
    """
    if not ref_fraction or ref_fraction <= 0:
        return None
    return min(fraction / ref_fraction * 100.0, 100.0)


# --------------------------------------------------------------------------
# ไฟล์ / path helper
# --------------------------------------------------------------------------
def iter_images(path: str) -> list[Path]:
    """รับได้ทั้งไฟล์เดียวหรือทั้งโฟลเดอร์ → คืน list ของ path ภาพ (เรียงชื่อแล้ว)"""
    p = Path(path)
    if p.is_file():
        return [p]
    if p.is_dir():
        return sorted(f for f in p.rglob("*") if f.suffix.lower() in IMAGE_SUFFIXES)
    raise FileNotFoundError(f"ไม่พบ path: {path}")


def load_reference(path: str = REFERENCE_FILE) -> tuple[dict[str, float], str]:
    """
    โหลดค่า FULL_REFERENCE จาก reference.json (สร้างโดย calibrate_reference.py)
    ถ้าไม่มีไฟล์ → ใช้ค่า default พร้อมบอกที่มา เพื่อให้ผู้ใช้รู้ว่ายังไม่ได้ calibrate
    """
    f = Path(path)
    if not f.exists():
        return dict(DEFAULT_FULL_REFERENCE), "default (ยังไม่ได้ calibrate!)"

    data = json.loads(f.read_text(encoding="utf-8"))
    ref = {c: float(data.get("full_reference", {}).get(c, 0.0)) for c in CLASS_NAMES}
    src = f"{f} (calibrate เมื่อ {data.get('created_at', '?')}, {data.get('n_images', '?')} ภาพ)"
    return ref, src


def save_reference(ref: dict[str, float], meta: dict, path: str = REFERENCE_FILE) -> None:
    """เซฟค่า calibration ลงไฟล์ JSON ให้สคริปต์อื่นอ่านต่อได้"""
    payload = {
        "unit": "area_fraction_of_frame",
        "note": "พื้นที่ mask หารด้วยพื้นที่ทั้งเฟรม — ไม่ขึ้นกับ resolution ของภาพ",
        "full_reference": {c: round(float(ref.get(c, 0.0)), 6) for c in CLASS_NAMES},
        **meta,
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_device(device: str | None) -> str:
    """
    เลือก device: argument > env DEVICE > auto (มี CUDA → '0', ไม่มี → 'cpu')

    เครื่องที่มีหลายการ์ดควรระบุเอง เช่น --device 1 หรือ DEVICE=1
    เพราะ GPU 0 อาจมีงานอื่นใช้อยู่จนเต็มแล้วพังเป็น CUDA out of memory
    """
    if device:
        return device
    env_device = os.environ.get("DEVICE")
    if env_device:
        return env_device
    if os.environ.get("TRAY_FORCE_CPU"):
        return "cpu"
    try:
        import torch

        return "0" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"
