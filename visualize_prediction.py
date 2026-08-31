"""
วาดผลทำนายทับภาพ เพื่อตรวจด้วยตาว่าโมเดลแยกชนิดอาหารถูกไหม

    python visualize_prediction.py test.jpg --model best.pt
    python visualize_prediction.py samples/ --model best.pt --out runs/vis

สิ่งที่วาด:
  - ระบายสี mask ตาม class (โปร่งแสง) + ตีเส้นขอบให้เห็นรูปร่างชัด
  - แผงสรุปมุมซ้ายบน: สีของ class, ชื่อ, % ที่เหลือ, confidence

หมายเหตุ: ตัวหนังสือบนภาพใช้ภาษาอังกฤษ เพราะ cv2.putText วาดฟอนต์ไทยไม่ได้
          (ส่วนที่พิมพ์ลง terminal เป็นภาษาไทยปกติ)
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

from tray_common import (
    CLASS_COLORS_BGR,
    CLASS_NAMES,
    CLASS_NAMES_TH,
    DEFAULT_MIN_TRAY_OVERLAP,
    circle_mask,
    class_area_fractions,
    format_model_report,
    inspect_model,
    iter_images,
    load_model,
    load_reference,
    no_detection_notice,
    predict_one,
    remaining_percent,
    resolve_conf,
    resolve_device,
    resolve_min_overlap,
    resolve_model_path,
    resolve_tray_crop,
)
from tray_detect import detect_tray_region, draw_tray_circle

MASK_ALPHA = 0.45          # ความทึบของสีที่ระบายทับ
PANEL_ALPHA = 0.65         # ความทึบของพื้นหลังแผงสรุป


def parse_args():
    p = argparse.ArgumentParser(description="overlay mask + % เหลือ ลงบนภาพ")
    p.add_argument("images", help="ไฟล์ภาพ หรือโฟลเดอร์")
    p.add_argument("--model", default=None,
                   help="ไม่ใส่ = ใช้ env MODEL_PATH > models/current.pt > best.pt ล่าสุดใน runs/")
    p.add_argument("--reference", default="reference.json")
    p.add_argument("--conf", type=float, default=None,
                   help="ไม่ใส่ = ใช้ env CONF_THRESHOLD (default 0.15)")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default=None, help="'0' / 'cpu' (ไม่ใส่ = auto)")
    p.add_argument("--out", default="runs/vis", help="โฟลเดอร์เซฟภาพผลลัพธ์")
    p.add_argument("--no-panel", action="store_true", help="ไม่ต้องวาดแผงสรุป")
    p.add_argument("--no-tray-crop", action="store_true",
                   help="ปิดการกรอง detection นอกวงถาด (เท่ากับ TRAY_CROP=false)")
    return p.parse_args()


def draw_masks(image: np.ndarray, result, tray=None,
               min_overlap: float = DEFAULT_MIN_TRAY_OVERLAP) -> np.ndarray:
    """
    ระบายสี mask ทุกชิ้นทับภาพ + ตีเส้นขอบ

    ถ้าส่ง tray มาด้วย จะวาดเฉพาะชิ้นที่ผ่านการกรอง (และตัดส่วนที่ล้นนอกถาดออก)
    ให้ตรงกับตัวเลข % ที่รายงาน — ภาพกับตัวเลขต้องเล่าเรื่องเดียวกัน
    """
    canvas = image.copy()
    if result.masks is None or len(result.masks) == 0:
        return canvas

    masks = result.masks.data.cpu().numpy()
    classes = result.boxes.cls.cpu().numpy().astype(int)
    model_names = dict(getattr(result, "names", {}) or {})

    tray_mask = None
    if tray is not None:
        tray_mask = circle_mask(canvas.shape[:2], tray)

    # ชั้นสีแยกต่างหาก แล้วค่อย blend ทีเดียว — สีจะไม่เข้มขึ้นเรื่อย ๆ ตรงที่ mask ซ้อนกัน
    color_layer = np.zeros_like(canvas)
    painted = np.zeros(canvas.shape[:2], dtype=bool)
    outlines = []                       # เก็บไว้วาดหลัง blend เส้นจะได้ไม่จาง

    for mask, cls_id in zip(masks, classes):
        name = model_names.get(int(cls_id))
        if name is None:
            name = CLASS_NAMES[cls_id] if 0 <= cls_id < len(CLASS_NAMES) else None
        if name not in CLASS_COLORS_BGR:
            continue
        binary = (mask > 0.5)

        # mask อาจคนละขนาดกับภาพ (ถ้าไม่ได้ใช้ retina_masks) → ย่อ/ขยายให้ตรงก่อน
        if binary.shape != canvas.shape[:2]:
            binary = cv2.resize(binary.astype(np.uint8),
                                (canvas.shape[1], canvas.shape[0]),
                                interpolation=cv2.INTER_NEAREST).astype(bool)

        # กรองแบบเดียวกับตอนคิดพื้นที่ ไม่งั้นภาพจะโชว์ mask ที่ไม่ได้ถูกนับ
        if tray_mask is not None:
            area = int(binary.sum())
            inside = binary & tray_mask
            if not area or int(inside.sum()) / area < min_overlap:
                continue
            binary = inside

        color_layer[binary] = CLASS_COLORS_BGR[name]
        painted |= binary

        contours, _ = cv2.findContours(binary.astype(np.uint8),
                                       cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        outlines.append((contours, CLASS_COLORS_BGR[name]))

    canvas[painted] = cv2.addWeighted(canvas, 1 - MASK_ALPHA, color_layer, MASK_ALPHA, 0)[painted]

    # ตีเส้นขอบทับทีหลัง ให้เห็นว่าแต่ละชิ้นแยกกันตรงไหน
    for contours, color in outlines:
        cv2.drawContours(canvas, contours, -1, color, 2)
    return canvas


def draw_panel(canvas: np.ndarray, fractions, confs, counts, reference) -> np.ndarray:
    """วาดแผงสรุป % เหลือ มุมซ้ายบน"""
    h, w = canvas.shape[:2]
    scale = max(0.5, min(w, h) / 1200.0)          # ปรับขนาดตัวอักษรตามขนาดภาพ
    font = cv2.FONT_HERSHEY_SIMPLEX
    line_h = int(34 * scale)
    pad = int(14 * scale)
    panel_w = int(430 * scale)
    panel_h = pad * 2 + line_h * (len(CLASS_NAMES) + 1)

    overlay = canvas.copy()
    cv2.rectangle(overlay, (pad, pad), (pad + panel_w, pad + panel_h), (30, 30, 30), -1)
    canvas = cv2.addWeighted(overlay, PANEL_ALPHA, canvas, 1 - PANEL_ALPHA, 0)

    y = pad + line_h
    cv2.putText(canvas, "REMAINING (est.)", (pad * 2, y), font, 0.72 * scale, (255, 255, 255),
                max(1, int(2 * scale)), cv2.LINE_AA)

    for name in CLASS_NAMES:
        y += line_h
        # กล่องสีประจำ class
        cv2.rectangle(canvas, (pad * 2, y - int(15 * scale)),
                      (pad * 2 + int(24 * scale), y), CLASS_COLORS_BGR[name], -1)

        ref = reference.get(name, 0.0)
        pct = remaining_percent(fractions[name], ref)
        if ref <= 0:
            text = f"{name:11s} n/a (no ref)"
        elif counts[name] == 0:
            text = f"{name:11s}   0%  (none)"
        else:
            text = f"{name:11s} {pct:5.1f}%  c={confs[name]:.2f}"

        cv2.putText(canvas, text, (pad * 2 + int(34 * scale), y), font, 0.62 * scale,
                    (240, 240, 240), max(1, int(2 * scale)), cv2.LINE_AA)
    return canvas


def visualize_one(model, image_path: Path, reference, conf, imgsz, no_panel, device,
                  out_dir: Path, tray_crop: bool, min_overlap: float) -> Path:
    image = cv2.imread(str(image_path))
    if image is None:
        raise SystemExit(f"อ่านภาพไม่ได้: {image_path}")

    region = detect_tray_region(image) if tray_crop else None
    tray = region.crop if region else None      # None = โหมด full-frame ไม่กรอง
    result = predict_one(model, str(image_path), conf=conf, imgsz=imgsz, device=device)

    stats = class_area_fractions(result, tray=tray, min_overlap=min_overlap)
    canvas = draw_masks(image, result, tray=tray, min_overlap=min_overlap)
    if region and region.circle:
        # วาดวงเสมอ แต่ถ้าไม่ได้ใช้กรอง จะวาดสีส้มพร้อมกำกับไว้
        canvas = draw_tray_circle(canvas, region.circle, used=region.is_full_tray)
    if not no_panel:
        canvas = draw_panel(canvas, stats.fractions, stats.confs, stats.counts, reference)

    out_path = out_dir / f"{image_path.stem}_pred.jpg"
    cv2.imwrite(str(out_path), canvas, [cv2.IMWRITE_JPEG_QUALITY, 92])

    # สรุปลง terminal เป็นภาษาไทย
    parts = []
    for name in CLASS_NAMES:
        if stats.counts[name] == 0:
            continue
        pct = remaining_percent(stats.fractions[name], reference.get(name, 0.0))
        pct_txt = "ไม่ทราบ" if pct is None else f"{pct:.0f}%"
        parts.append(f"{CLASS_NAMES_TH[name]} {pct_txt}")
    if region is None:
        tray_txt = "ปิด tray crop"
    elif region.is_full_tray:
        tray_txt = f"crop วงถาด ({region.circle.method} r={region.circle.r})"
    else:
        tray_txt = f"full-frame — {region.reason}"
    n_out = sum(stats.outside_tray.values())
    if n_out:
        tray_txt += f", กรองนอกถาดทิ้ง {n_out} ชิ้น"
    print(f"  {image_path.name} -> {out_path.name}  [{tray_txt}]  |  "
          + (", ".join(parts) if parts else "ไม่เจออาหารในภาพ"))

    if stats.in_liquid:
        detail = ", ".join(f"{CLASS_NAMES_TH.get(k, k)} {v}" for k, v in sorted(stats.in_liquid.items()))
        print(f"      [ในน้ำซุป] {detail} (ประมาณจากผิวที่เห็น)")
    notice = no_detection_notice(stats, conf)
    if notice:
        print(f"      [!] {notice}")
    return out_path


def main():
    args = parse_args()
    device = resolve_device(args.device)

    image_paths = iter_images(args.images)
    if not image_paths:
        raise SystemExit(f"ไม่พบไฟล์ภาพใน {args.images}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path, model_source = resolve_model_path(args.model)
    if not model_path:
        raise SystemExit("ยังไม่มีโมเดล — รัน `python train_smoke.py` หรือ `python train.py` ก่อน")
    conf, conf_source = resolve_conf(args.conf)

    reference, ref_src = load_reference(args.reference)
    model = load_model(model_path)
    print(format_model_report(inspect_model(model, model_path, model_source)))
    tray_crop = resolve_tray_crop(False if args.no_tray_crop else None)
    min_overlap = resolve_min_overlap()
    print(f"[visualize] {len(image_paths)} ภาพ  device={device}  conf={conf:.2f} ({conf_source})")
    print(f"[visualize] reference: {ref_src}")
    print(f"[visualize] tray crop: {'เปิด' if tray_crop else 'ปิด'} "
          f"(min_overlap={min_overlap:.2f})\n")

    for path in image_paths:
        visualize_one(model, path, reference, conf, args.imgsz, args.no_panel, device,
                      out_dir, tray_crop, min_overlap)

    print(f"\nเซฟภาพผลลัพธ์ไว้ที่: {out_dir}/")


if __name__ == "__main__":
    main()
