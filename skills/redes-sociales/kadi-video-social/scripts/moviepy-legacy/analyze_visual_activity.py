import os
import glob
import cv2
import numpy as np
import json

VIDEOS_DIR = os.environ.get("KADI_VIDEOS_SOURCE", "./videos_source")
SAMPLE_INTERVAL_SEC = 10
TOP_N = 10

def analyze_video(video_path, sample_interval_sec=10, top_n=10):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] No se pudo abrir el archivo: {video_path}")
        return None

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if total_frames > 0 else 0
    step_frames = max(1, int(sample_interval_sec * fps))

    results = []
    current_frame = 0

    while current_frame < total_frames - 1:
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret1, frame1 = cap.read()
        ret2, frame2 = cap.read()

        if not ret1 or not ret2:
            break

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(gray1, gray2)
        score = float(np.mean(diff))

        timestamp_sec = round(current_frame / fps, 2)
        results.append({
            "timestamp_sec": timestamp_sec,
            "activity_score": round(score, 4)
        })

        current_frame += step_frames

    cap.release()
    results.sort(key=lambda x: x["activity_score"], reverse=True)
    top_results = results[:top_n]

    return {
        "file": os.path.basename(video_path),
        "fps": round(fps, 2),
        "duration_sec": round(duration_sec, 2),
        "top_timestamps": top_results
    }

def main():
    video_extensions = ("*.mp4", "*.webm")
    video_files = []
    for ext in video_extensions:
        video_files.extend(glob.glob(os.path.join(VIDEOS_DIR, ext)))

    all_reports = []
    for video_file in video_files:
        report = analyze_video(video_file, sample_interval_sec=SAMPLE_INTERVAL_SEC, top_n=TOP_N)
        if report:
            all_reports.append(report)

    output_json = os.path.join(VIDEOS_DIR, "visual_activity_report.json")
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, indent=2, ensure_ascii=False)
    print(f"Reporte completo guardado en: {output_json}")

if __name__ == "__main__":
    main()
