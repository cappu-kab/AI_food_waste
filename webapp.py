"""
เว็บสำหรับลองระบบด้วยตัวเอง: ลากรูปถาดเข้าไป → เห็น mask ทับภาพ + % ที่เหลือของแต่ละชนิด

รัน:
    docker compose up web            # แล้วเปิด http://localhost:8899
    python webapp.py --model runs/tray_waste/yolov8s_seg_v1/weights/best.pt --port 8899

ถ้าไม่ระบุ --model จะไล่หา best.pt ที่ใหม่ที่สุดใน runs/ ให้อัตโนมัติ
เว็บนี้ใช้ตรรกะเดียวกับ estimate_waste.py / visualize_prediction.py ทุกอย่าง
(เรียกฟังก์ชันชุดเดียวกัน) ตัวเลขที่เห็นบนเว็บจึงตรงกับที่รันบน command line
"""

import argparse
import base64
import os
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request, send_from_directory

from tray_common import (
    CLASS_COLORS_BGR,
    CLASS_NAMES,
    CLASS_NAMES_TH,
    class_area_fractions,
    cm2_per_pixel,
    estimate_weight_g,
    format_model_report,
    fraction_to_px,
    inspect_model,
    load_model,
    load_reference,
    no_detection_notice,
    predict_one,
    remaining_percent,
    resolve_conf,
    resolve_density,
    resolve_device,
    resolve_min_overlap,
    resolve_model_path,
    resolve_sure_conf,
    resolve_height_cm,
    resolve_tray_crop,
    resolve_tray_diameter_cm,
)
from tray_detect import detect_tray_region, draw_tray_circle
from visualize_prediction import draw_masks, draw_panel

MAX_UPLOAD_MB = 32
DISPLAY_MAX_WIDTH = 1400        # ย่อภาพผลลัพธ์ก่อนส่งกลับ เบราว์เซอร์จะได้ไม่อืด
# Free hosts (Render 512MB) OOM on full-res + imgsz=640; keep real model but smaller tensors
INFER_MAX_SIDE = int(os.environ.get("INFER_MAX_SIDE", "960"))
INFER_IMGSZ = int(os.environ.get("INFER_IMGSZ", "416"))
DEMO_DIR = Path("samples/demo")  # รูปสำหรับปุ่ม "ลองด้วยรูปตัวอย่าง"
DEMO_LIMIT = int(os.environ.get("DEMO_LIMIT", "2"))

# เว็บ static ของโปรเจกต์ AI Food Waste Lab — เสิร์ฟจาก Flask ตัวเดียวกัน
# ทำแบบนี้เพื่อให้หน้า scan.html เรียก /api/predict ได้ตรง ๆ โดยไม่ติด CORS
# และผู้ใช้เข้าเว็บเดียวจบ ไม่ต้องรัน http.server แยกอีกตัว
SITE_DIR = Path("AI_food_waste-main")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

# state ของเซิร์ฟเวอร์ — โหลดโมเดลครั้งเดียวตอนเริ่ม ไม่ใช่ทุก request
STATE: dict = {"model": None, "model_path": None, "reference": {}, "ref_src": "", "device": "cpu"}


@app.after_request
def add_cors_headers(response):
    """Allow the Vercel static site (and local preview) to call /api/* cross-origin."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/api/predict", methods=["OPTIONS"])
@app.route("/api/demo", methods=["OPTIONS"])
@app.route("/api/config", methods=["OPTIONS"])
@app.route("/api/health", methods=["OPTIONS"])
def api_cors_preflight():
    return ("", 204)


def encode_jpg(image: np.ndarray) -> str:
    """ndarray -> data URL สำหรับแปะใน <img> ตรง ๆ ไม่ต้องเซฟไฟล์"""
    h, w = image.shape[:2]
    if w > DISPLAY_MAX_WIDTH:
        scale = DISPLAY_MAX_WIDTH / w
        image = cv2.resize(image, (DISPLAY_MAX_WIDTH, int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise RuntimeError("encode ภาพไม่สำเร็จ")
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode()


def bgr_to_hex(bgr) -> str:
    b, g, r = bgr
    return f"#{r:02x}{g:02x}{b:02x}"


def shrink_for_infer(image: np.ndarray) -> np.ndarray:
    """Downscale long side so YOLO fits in small free-tier RAM."""
    h, w = image.shape[:2]
    side = max(h, w)
    if side <= INFER_MAX_SIDE:
        return image
    scale = INFER_MAX_SIDE / side
    return cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def analyse(image: np.ndarray, conf: float, show_panel: bool) -> dict:
    """รัน 1 ภาพ → คืน dict ที่หน้าเว็บเอาไปแสดงได้เลย"""
    image = shrink_for_infer(image)
    # หาพื้นที่ทำงานก่อน: ถ้าเห็นถาดเต็มวงจะ crop ตามวง ถ้าถ่ายใกล้จนถาดล้นเฟรม
    # จะถอยไปโหมด full-frame (ไม่กรองอะไรทิ้ง) ดีกว่าเผลอตัด detection ทิ้งหมด
    region = detect_tray_region(image) if STATE["tray_crop"] else None
    tray = region.crop if region else None

    # ต้องส่ง device ทุกครั้ง ไม่งั้น ultralytics จะเลือก GPU 0 เองตาม default
    # ทำให้ค่า DEVICE/--device ที่ตั้งไว้ไม่มีผลจริง (log บอกอย่าง แต่รันอีกอย่าง)
    result = predict_one(
        STATE["model"], image, conf=conf, imgsz=STATE["imgsz"], device=STATE["device"]
    )
    stats = class_area_fractions(result, tray=tray, min_overlap=STATE["min_overlap"])
    reference = STATE["reference"]

    # ไม้บรรทัดแปลงพิกเซล -> ตร.ซม. ใช้วงถาดเป็นตัวเทียบ
    # โหมด full-frame ไม่มีวงถาด -> px2cm2 เป็น None แล้วเราจะไม่รายงาน ตร.ซม./กรัม เลย
    px2cm2 = cm2_per_pixel(tray)

    rows = []
    for name in CLASS_NAMES:
        ref = reference.get(name, 0.0)
        pct = remaining_percent(stats.fractions[name], ref)

        # ตรรกะเดียวกับ estimate_waste.py: แยก "ไม่รู้" ออกจาก "ไม่มี" ให้ชัด
        if ref <= 0:
            status = "no_reference"
        elif stats.counts[name] == 0:
            status, pct = "empty", 0.0
        elif stats.confs[name] < STATE["sure_conf"]:
            status = "uncertain"
        else:
            status = "ok"

        area_px = fraction_to_px(stats.fractions[name], result)
        area_cm2 = round(area_px * px2cm2, 1) if px2cm2 is not None else None
        weight_g = (round(estimate_weight_g(area_cm2, name), 1)
                    if area_cm2 is not None else None)

        rows.append({
            "name": name,
            "name_th": CLASS_NAMES_TH[name],
            "color": bgr_to_hex(CLASS_COLORS_BGR[name]),
            "percent": None if pct is None else round(pct, 1),
            "confidence": round(stats.confs[name], 2),
            "instances": stats.counts[name],
            "area_px": area_px,
            "area_cm2": area_cm2,
            "weight_g": weight_g,
            "status": status,
        })

    overlay = draw_masks(image, result, tray=tray, min_overlap=STATE["min_overlap"])
    if region and region.circle:
        overlay = draw_tray_circle(overlay, region.circle, label=False,
                                   used=region.is_full_tray)
    if show_panel:
        overlay = draw_panel(overlay, stats.fractions, stats.confs, stats.counts, reference)

    n_outside = sum(stats.outside_tray.values())
    return {
        "image": encode_jpg(overlay),
        "rows": rows,
        "size": [int(result.orig_shape[1]), int(result.orig_shape[0])],
        "conf_used": round(conf, 2),
        # ถ้าไม่เจออะไรเลย ส่งคำอธิบายไปให้หน้าเว็บแสดง แทนที่จะโชว์ 0% เฉย ๆ
        "notice": no_detection_notice(stats, conf),
        "tray": None if not (region and region.circle) else {
            "cx": region.circle.cx, "cy": region.circle.cy, "r": region.circle.r,
            "method": region.circle.method, "score": round(region.circle.score, 2),
            "used": region.is_full_tray,
        },
        "tray_mode": region.mode if region else "off",
        "tray_reason": region.reason if region else "ปิดการกรองไว้",
        "tray_crop": STATE["tray_crop"],
        "has_scale": px2cm2 is not None,
        "tray_diameter_cm": resolve_tray_diameter_cm(),
        "height_cm": resolve_height_cm(),
        "in_liquid": [
            {"name": k, "name_th": CLASS_NAMES_TH.get(k, k), "n": v,
             "fraction": round(stats.in_liquid_fraction.get(k, 0.0), 5)}
            for k, v in sorted(stats.in_liquid.items())
        ],
        "outside_tray": n_outside,
        "outside_detail": ", ".join(f"{k} ({v})" for k, v in sorted(stats.outside_tray.items())),
    }


def demo_images() -> list[Path]:
    from tray_common import IMAGE_SUFFIXES

    if not DEMO_DIR.is_dir():
        return []
    files = sorted(f for f in DEMO_DIR.iterdir() if f.suffix.lower() in IMAGE_SUFFIXES)
    return files[:DEMO_LIMIT]


# ---------------------------------------------------------------------------
# เสิร์ฟเว็บ static ของ Food Waste Lab
# ---------------------------------------------------------------------------
@app.route("/site/")
@app.route("/site/<path:filename>")
def site(filename: str = "index.html"):
    """เว็บ static เดิม (index/dashboard/kitchen/...) เสิร์ฟจาก Flask ตัวเดียวกัน"""
    if not SITE_DIR.is_dir():
        return "ไม่พบโฟลเดอร์เว็บ AI_food_waste-main", 404
    return send_from_directory(SITE_DIR.resolve(), filename)


@app.route("/api/health")
def api_health():
    """Lightweight readiness check for the hosted ML API."""
    ok = STATE.get("model") is not None and not (STATE.get("info") and STATE["info"].problems)
    return jsonify({
        "ok": bool(ok),
        "model_path": STATE.get("model_path"),
        "device": STATE.get("device"),
    }), (200 if ok else 503)


@app.route("/api/config")
def api_config():
    """
    ค่าตั้งต้นสำหรับหน้า scan.html (ซึ่งเป็น static ล้วน ไม่ผ่าน Jinja)

    แยกออกมาเป็น API เพื่อให้เว็บ Food Waste Lab ยังเป็น static ทั้งชุดตามดีไซน์เดิม
    ไม่ต้องแปลงหน้าไหนเป็น template
    """
    info = STATE["info"]
    return jsonify({
        "model_path": STATE["model_path"],
        "model_classes": [str(v) for v in info.names.values()],
        "model_trained_on": info.trained_on,
        "model_ok": info.is_project_model and not info.problems,
        "model_problems": info.problems,
        "device": STATE["device"],
        "conf": STATE["conf"],
        "sure_conf": STATE["sure_conf"],
        "tray_crop": STATE["tray_crop"],
        "tray_diameter_cm": resolve_tray_diameter_cm(),
        "height_cm": resolve_height_cm(),
        "calibrated": "default" not in STATE["ref_src"],
        "ref_src": STATE["ref_src"],
        "max_mb": MAX_UPLOAD_MB,
        "has_demo": bool(demo_images()),
        "density": {c: resolve_density(c) for c in CLASS_NAMES},
    })


@app.route("/")
def index():
    info = STATE["info"]
    return render_template(
        "index.html",
        model_path=STATE["model_path"],
        model_source=info.source,
        model_classes=", ".join(str(v) for v in list(info.names.values())[:12]),
        model_n_classes=len(info.names),
        model_trained_on=info.trained_on,
        model_problems=info.problems,
        model_warnings=info.warnings,
        model_is_project=info.is_project_model and not info.problems,
        ref_src=STATE["ref_src"],
        calibrated="default" not in STATE["ref_src"],
        device=STATE["device"],
        default_conf=STATE["conf"],
        sure_conf=STATE["sure_conf"],
        tray_crop=STATE["tray_crop"],
        min_overlap=STATE["min_overlap"],
        classes=[{"name": c, "name_th": CLASS_NAMES_TH[c],
                  "color": bgr_to_hex(CLASS_COLORS_BGR[c])} for c in CLASS_NAMES],
        max_mb=MAX_UPLOAD_MB,
        has_demo=bool(demo_images()),
    )


@app.route("/api/demo")
def api_demo():
    """ลองด้วยรูปใน samples/demo/ — ไว้กดดูผลได้เลยโดยไม่ต้องหารูปเอง"""
    files = demo_images()
    if not files:
        return jsonify({"error": f"ไม่มีรูปตัวอย่างใน {DEMO_DIR}/"}), 404

    conf = float(request.args.get("conf", STATE["conf"]))
    show_panel = request.args.get("panel") == "1"

    results = []
    for path in files:
        image = cv2.imread(str(path))
        if image is None:
            continue
        out = analyse(image, conf, show_panel)
        out["filename"] = str(path)
        results.append(out)
    return jsonify({"results": results})


@app.route("/api/predict", methods=["POST"])
def api_predict():
    files = request.files.getlist("images")
    if not files:
        return jsonify({"error": "ไม่ได้แนบไฟล์ภาพมา"}), 400

    conf = float(request.form.get("conf", STATE["conf"]))
    show_panel = request.form.get("panel") == "1"

    results = []
    for f in files:
        data = np.frombuffer(f.read(), np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if image is None:
            results.append({"filename": f.filename, "error": "อ่านไฟล์ภาพนี้ไม่ได้"})
            continue
        out = analyse(image, conf, show_panel)
        out["filename"] = f.filename
        results.append(out)

    return jsonify({"results": results})


@app.errorhandler(413)
def too_large(_e):
    return jsonify({"error": f"ไฟล์ใหญ่เกิน {MAX_UPLOAD_MB} MB"}), 413


def parse_args():
    p = argparse.ArgumentParser(description="เว็บทดสอบระบบวัดอาหารเหลือ")
    p.add_argument("--model", default=None,
                   help="ไม่ใส่ = ใช้ env MODEL_PATH > models/current.pt > best.pt ล่าสุดใน runs/")
    p.add_argument("--reference", default="reference.json")
    p.add_argument("--conf", type=float, default=None,
                   help="ไม่ใส่ = ใช้ env CONF_THRESHOLD (default 0.15)")
    p.add_argument("--sure-conf", type=float, default=None,
                   help="ต่ำกว่านี้จะขึ้นป้าย 'ไม่แน่ใจ' (env SURE_CONF)")
    p.add_argument("--device", default=None, help="'0' / 'cpu' (ไม่ใส่ = auto)")
    p.add_argument("--no-tray-crop", action="store_true",
                   help="ปิดการกรอง detection นอกวงถาด (เท่ากับ TRAY_CROP=false)")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8899)
    return p.parse_args()


def main():
    args = parse_args()
    model_path, model_source = resolve_model_path(args.model)
    if not model_path:
        raise SystemExit(
            "ยังไม่มีโมเดลให้ใช้ — ทำอย่างใดอย่างหนึ่ง:\n"
            "  1) พิสูจน์ว่า loop ทำงาน : python train_smoke.py\n"
            "  2) เทรนกับข้อมูลจริง     : python train.py\n"
            "  3) ชี้ไปที่ weight ที่มีอยู่ : MODEL_PATH=path/to/best.pt python webapp.py"
        )
    if not Path(model_path).exists():
        raise SystemExit(f"ไม่พบไฟล์โมเดล: {model_path}  (มาจาก {model_source})")

    conf, conf_source = resolve_conf(args.conf)

    STATE["device"] = resolve_device(args.device)
    STATE["model_path"] = model_path
    STATE["model"] = load_model(model_path)
    STATE["reference"], STATE["ref_src"] = load_reference(args.reference)
    STATE["sure_conf"] = resolve_sure_conf(args.sure_conf)
    STATE["conf"] = conf
    STATE["info"] = inspect_model(STATE["model"], model_path, model_source)
    STATE["tray_crop"] = resolve_tray_crop(False if args.no_tray_crop else None)
    STATE["min_overlap"] = resolve_min_overlap()
    STATE["imgsz"] = INFER_IMGSZ

    # ---- log ตอน start ให้เห็นครบว่าเสิร์ฟอะไรอยู่ จะได้ไม่ต้องเดาเวลาผลออกมา 0 ----
    print("\n[web] กำลังเริ่มเซิร์ฟเวอร์")
    print(format_model_report(STATE["info"]))
    print(f"  device     : {STATE['device']}")
    print(f"  conf       : {conf:.2f}  (จาก {conf_source})")
    print(f"  sure_conf  : {STATE['sure_conf']:.2f}")
    print(f"  reference  : {STATE['ref_src']}")
    print(f"  imgsz      : {STATE['imgsz']}  (max side {INFER_MAX_SIDE})")
    print(f"  tray crop  : {'เปิด' if STATE['tray_crop'] else 'ปิด'} "
          f"(min_overlap={STATE['min_overlap']:.2f}) — กรอง detection นอกวงถาดทิ้ง")
    # Hosted platforms (Render, etc.) inject PORT
    port = int(os.environ.get("PORT", args.port))
    print(f"  เปิดที่     : http://localhost:{port}\n")

    # Single-threaded on tiny free instances — concurrent YOLO OOMs easily
    threaded = os.environ.get("FLASK_THREADED", "0") == "1"
    app.run(host=args.host, port=port, debug=False, threaded=threaded)


if __name__ == "__main__":
    main()
