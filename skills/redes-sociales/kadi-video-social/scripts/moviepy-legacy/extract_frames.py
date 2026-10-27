import os
import json
import cv2

def extract_frames():
    BASE_DIR = os.environ.get("KADI_VIDEOS_SOURCE", "./videos_source")
    report_path = os.path.join(BASE_DIR, "visual_activity_report.json")
    frames_dir = os.path.join(BASE_DIR, "extracted_frames")
    
    os.makedirs(frames_dir, exist_ok=True)
    
    if not os.path.exists(report_path):
        print("No se encontró visual_activity_report.json")
        return
        
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for video in data:
        video_name = video["file"]
        video_path = os.path.join(BASE_DIR, video_name)
        
        if not os.path.exists(video_path):
            continue
            
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Take the top 3 timestamps
        top_ts = video.get("top_timestamps", [])[:3]
        
        for idx, ts_info in enumerate(top_ts):
            sec = ts_info["timestamp_sec"]
            frame_num = int(sec * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if ret:
                # Resize if too large to save space and processing time
                h, w = frame.shape[:2]
                if max(w, h) > 1920:
                    scale = 1920 / max(w, h)
                    frame = cv2.resize(frame, (0,0), fx=scale, fy=scale)
                
                out_name = f"{video_name}_ts_{sec:.2f}.jpg"
                out_path = os.path.join(frames_dir, out_name)
                cv2.imwrite(out_path, frame)
                print(f"Extraído: {out_name}")
                
        cap.release()

if __name__ == "__main__":
    extract_frames()
