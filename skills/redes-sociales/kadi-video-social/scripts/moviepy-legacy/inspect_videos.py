import os
import json
from pathlib import Path

try:
    from moviepy.editor import VideoFileClip
except ImportError:
    from moviepy import VideoFileClip

def inspect_video_sources(folder_path: str) -> list[dict]:
    folder = Path(folder_path)
    supported_extensions = {'.mp4', '.webm'}
    results = []

    if not folder.exists():
        raise FileNotFoundError(f"La carpeta {folder_path} no existe.")

    for file_path in sorted(folder.iterdir()):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            file_info = {
                "nombre": file_path.name,
                "ruta_completa": str(file_path),
                "size_bytes": file_path.stat().st_size
            }
            try:
                clip = VideoFileClip(str(file_path))
                
                file_info.update({
                    "duration_segundos": round(float(clip.duration), 3),
                    "fps": round(float(clip.fps), 2) if clip.fps else None,
                    "resolucion": f"{clip.w}x{clip.h}",
                    "ancho": clip.w,
                    "alto": clip.h,
                    "status": "OK"
                })
                clip.close()
            except Exception as err:
                file_info.update({
                    "duration_segundos": None,
                    "fps": None,
                    "resolucion": None,
                    "error": str(err),
                    "status": "ERROR"
                })
            
            results.append(file_info)

    return results

if __name__ == "__main__":
    target_directory = os.environ.get("KADI_VIDEOS_SOURCE", "./videos_source")
    report = inspect_video_sources(target_directory)
    
    output_json = Path(target_directory) / "video_durations_report.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Reporte guardado exitosamente en: {output_json}")
