"""Render reproducible con MoviePy 1.0.3, Pillow y FFmpeg. No escribe en Core."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from moviepy.editor import VideoClip
import numpy as np
import argparse, bisect, hashlib, json, math, subprocess, wave
from audio_contract import validate_voice_import
from publication import stage_validate_publish

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/video-kadi"
PUBLIC = ROOT / "src/assets/videos"
SOURCE = Path(__import__("os").environ.get("KADI_SCREENSHOTS_DIR", "./screenshots"))
STORY_PATH = ROOT/"scripts/video/storyboard.json"
STORY = json.loads(STORY_PATH.read_text(encoding="utf-8"))

def preview_timeline():
    cursor=0.65; scenes=[]
    for i,scene in enumerate(STORY["scenes"]):
        length=max(6.0,len(scene["voice"].split())/2.8)
        voice_start=cursor
        scenes.append({**scene,"start":0.0 if i==0 else voice_start-.35,"voiceStart":voice_start,
                       "voiceDuration":length,"end":voice_start+length+.35,"words":[]})
        cursor+=length+.75
    scenes[-1]["end"]+=2.1
    for i in range(len(scenes)-1): scenes[i]["end"]=scenes[i+1]["start"]
    return {**STORY,"duration":scenes[-1]["end"],"scenes":scenes}

PREVIEW_ONLY = "--preview-only" in sys.argv
DATA = preview_timeline() if PREVIEW_ONLY else json.loads((OUT/"timeline.json").read_text(encoding="utf-8"))
W,H,FPS = DATA["width"],DATA["height"],DATA["fps"]
PUBLIC.mkdir(parents=True,exist_ok=True)
FONT = Path(r"C:\Windows\Fonts")
fonts = {}
def font(size,bold=False):
    key=(size,bold)
    if key not in fonts: fonts[key]=ImageFont.truetype(str(FONT/("segoeuib.ttf" if bold else "segoeui.ttf")),size)
    return fonts[key]

NAVY=(10,18,32); GOLD=(226,199,102); WHITE=(246,248,251); MUTED=(180,196,218)
X,Y=np.meshgrid(np.linspace(0,1,W),np.linspace(0,1,H))
light=np.exp(-(((X-.8)/.65)**2+((Y-.4)/.8)**2)*2)
bg=np.zeros((H,W,3),dtype=np.uint8)
for i,(a,b) in enumerate(zip(NAVY,(21,38,61))): bg[:,:,i]=(a+(b-a)*light).astype(np.uint8)
BACKGROUND=Image.fromarray(bg)
draw=ImageDraw.Draw(BACKGROUND)
for x in range(0,W,80): draw.line((x,0,x,H),fill=(21,31,44),width=1)
for y in range(0,H,80): draw.line((0,y,W,y),fill=(21,31,44),width=1)
LOGO=Image.open(ROOT/"src/assets/logo-kadi.png").convert("RGBA")
LOGO=ImageOps.contain(LOGO,(145,62),Image.Resampling.LANCZOS)
shots={name:Image.open(SOURCE/name).convert("RGB") for s in DATA["scenes"] for name in s["screens"]}
source_manifest=[{"file":name,"size":list(im.size),"sha256":hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()} for name,im in shots.items()]
(OUT/"source-manifest.json").write_text(json.dumps(source_manifest,indent=2),encoding="utf-8")

def ease(v):
    v=max(0,min(1,v)); return 1-(1-v)**3

def wrap(text,f,maxw):
    d=ImageDraw.Draw(Image.new("RGB",(1,1)));lines=[]
    for para in text.split("\n"):
        line=""
        for word in para.split():
            candidate=(line+" "+word).strip()
            if line and d.textlength(candidate,font=f)>maxw: lines.append(line);line=word
            else: line=candidate
        if line:lines.append(line)
    return lines

def text_block(im, text, pos, size, width, color=WHITE, bold=False, gap=1.15, center=False):
    d=ImageDraw.Draw(im); f=font(size,bold); y=pos[1]
    for line in wrap(text,f,width):
        x=pos[0] if not center else (W-d.textlength(line,font=f))/2
        d.text((x+1,y+2),line,font=f,fill=(0,0,0,90))
        d.text((x,y),line,font=f,fill=color)
        y+=round(size*gap)
    return y

def plate(name,size,progress,anchor=(.52,.12)):
    if Path(name).name=="01_onboarding_paso0_modelo.png":
        # Keep all three model choices visible together in the first onboarding step.
        im=shots[name]; fitted=ImageOps.contain(im,size,Image.Resampling.LANCZOS)
        canvas=Image.new("RGB",size,(246,248,251))
        canvas.paste(fitted,((size[0]-fitted.width)//2,(size[1]-fitted.height)//2))
        return canvas
    # Ken Burns 1.00x -> 1.08x, sobre píxeles de la captura real.
    im=shots[name]; zoom=1+.08*ease(progress)
    scale=max(size[0]/im.width,size[1]/im.height)*zoom
    sw,sh=round(im.width*scale),round(im.height*scale)
    scaled=im.resize((sw,sh),Image.Resampling.BICUBIC)
    left=int((sw-size[0])*anchor[0]);top=int((sh-size[1])*anchor[1])
    return scaled.crop((left,top,left+size[0],top+size[1]))

def add_screen(im,name,box,p):
    x,y,w,h=box
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((x-8,y-36,x+w+8,y+h+9),radius=16,fill=(6,12,23),outline=(62,81,111),width=1)
    for k,c in enumerate([(226,116,124),(226,199,102),(125,180,160)]):d.ellipse((x+8+k*15,y-23,x+16+k*15,y-15),fill=c)
    d.text((x+65,y-29),"KADI  /  ENTORNO DE DEMOSTRACIÓN",font=font(12),fill=MUTED)
    screen=plate(name,(w,h),p)
    mask=Image.new("L",(w,h),0);ImageDraw.Draw(mask).rounded_rectangle((0,0,w,h),radius=4,fill=255)
    im.paste(screen,(x,y),mask)

def scene_frame(s,t):
    im=BACKGROUND.copy()
    local=t-s["start"]; duration=s["end"]-s["start"]
    u=max(0,min(.9999,local/duration))
    d=ImageDraw.Draw(im)
    im.paste(LOGO,(62,32),LOGO)
    d.text((1000,49),"SOFTWARE VETERINARIO",font=font(15,True),fill=MUTED)
    d.line((64,108,1216,108),fill=(49,62,78),width=1)
    index=min(len(s["screens"])-1,int(u*len(s["screens"])))
    shot_local=(u*len(s["screens"]))%1
    if s["id"]=="01":
        index=0 if local<2 else 1
        shot_local=local/2 if index==0 else (local-2)/(duration-2)
    name=s["screens"][index]
    motion=int(16*(1-ease(local/.7)))
    if s["layout"]=="outro":
        d.text((64,133),s["eyebrow"],font=font(19,True),fill=GOLD)
        text_block(im,s["headline"][0],(0,213+motion),65,1160,bold=True,center=True)
        text_block(im,s["headline"][1],(0,294+motion),57,1160,color=GOLD,bold=True,center=True)
        text_block(im,"kadi.technology",(0,404),48,1100,bold=True,center=True)
        d.rounded_rectangle((448,492,832,551),radius=10,fill=GOLD)
        text_block(im,"AGENDA TU DEMO",(0,502),26,900,color=NAVY,bold=True,center=True)
        text_block(im,"Acceso inicial · Conoce el producto y resuelve tus dudas",(0,569),20,1100,color=MUTED,center=True)
    else:
        d.text((64,134),s["eyebrow"],font=font(17,True),fill=GOLD)
        if s["layout"]=="hook":
            headline="¿La cuenta\nrefleja toda\nla atención?"
            end=text_block(im,headline,(64,212+motion),58,390,bold=True)
            text_block(im,"El desorden también\ntiene un costo.",(66,end+28),25,355,color=MUTED)
        else:
            end=text_block(im,"\n".join(s["headline"]),(64,211+motion),50 if s["id"]=="03" else 54,355,bold=True)
            d.line((66,end+24,125,end+24),fill=GOLD,width=4)
            text_block(im,s["support"],(64,end+45),24,340,color=MUTED)
        x,y,w,h=470,205+motion,746,426
        add_screen(im,name,(x,y,w,h),shot_local)
        if index>0 and shot_local<.065:
            # Disolvencia breve entre capturas de la misma secuencia.
            previous=BACKGROUND.copy()
            add_screen(previous,s["screens"][index-1],(x,y,w,h),1)
            area=previous.crop((x-8,y-36,x+w+9,y+h+10))
            current=im.crop((x-8,y-36,x+w+9,y+h+10))
            im.paste(Image.blend(area,current,ease(shot_local/.065)),(x-8,y-36))
    # Identificación de demostración permanece visible y separada del mensaje comercial.
    d=ImageDraw.Draw(im)
    d.text((66,665),"CAPTURAS REALES · DATOS DE DEMOSTRACIÓN",font=font(12),fill=MUTED)
    d.text((1162,665),s["id"]+" / 06",font=font(13),fill=GOLD)
    return im

# Subtítulos por grupos de palabras de TTS, con temporización real.
captions=[]
for s in DATA["scenes"]:
    words=[dict(w) for w in s["words"]]
    original=s["voice"].split()
    if len(original)==len(words):
        for w,token in zip(words,original):w["text"]=token
    group=[]
    for j,w in enumerate(words):
        group.append(w)
        text=" ".join(z["text"] for z in group)
        if len(group)>=8 or len(text)>64 or w["text"].endswith((".", "?", "!", ":")) or j==len(words)-1:
            start=s["voiceStart"]+group[0]["offset"]
            end=s["voiceStart"]+group[-1]["offset"]+group[-1]["duration"]
            captions.append({"start":start,"end":min(end+.08,s["end"]),"text":text})
            group=[]
for i in range(len(captions)-1):
    captions[i]["end"]=min(captions[i]["end"],captions[i+1]["start"])

def stamp(sec,decimal="."):
    ms=round(sec*1000);h=ms//3600000;m=ms//60000%60;s=ms//1000%60
    return f"{h:02d}:{m:02d}:{s:02d}{decimal}{ms%1000:03d}"

vtt="WEBVTT\n\n"+"\n\n".join(f"{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}" for c in captions)+"\n"

def write_captions_to(directory):
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"kadi-en-accion.es.vtt").write_text(vtt,encoding="utf-8")
    (directory/"kadi-en-accion-transcripcion.txt").write_text("\n\n".join(s["voice"] for s in DATA["scenes"]),encoding="utf-8")
    (directory/"captions.json").write_text(json.dumps(captions,ensure_ascii=False,indent=2),encoding="utf-8")

starts=[s["start"] for s in DATA["scenes"]]

def validate_sol_import():
    if STORY.get("voice") != "Narrador (grabación importada)":
        raise RuntimeError("El storyboard no solicita una grabación importada de Narrador.")
    try:
        validate_voice_import(STORY_PATH,OUT/"timeline.json",OUT/"voice-narrador","Narrador")
    except (ValueError,FileNotFoundError) as error:
        raise RuntimeError(f"{error} No se modificó el MP4 ni sus companions públicos; importa una toma auténtica de Narrador antes de renderizar.") from None
def make_frame(t,subtitles=True):
    idx=max(0,bisect.bisect_right(starts,t)-1)
    s=DATA["scenes"][idx]
    im=scene_frame(s,t)
    if idx and t-s["start"]<.32:
        prev=scene_frame(DATA["scenes"][idx-1],s["start"]-.01)
        im=Image.blend(prev,im,ease((t-s["start"])/.32))
    if subtitles:
        cap=next((c for c in captions if c["start"]<=t<c["end"]),None)
        if cap:
            f=font(25,True);lines=wrap(cap["text"],f,1100)
            layer=Image.new("RGBA",(W,H),(0,0,0,0));d=ImageDraw.Draw(layer)
            top=624 if len(lines)==1 else 593
            d.rounded_rectangle((64,top-5,1216,top+len(lines)*31+10),radius=8,fill=(5,10,19,242))
            for j,line in enumerate(lines):
                width=d.textlength(line,font=f);d.text(((W-width)/2,top+j*31),line,font=f,fill=WHITE)
            im=Image.alpha_composite(im.convert("RGBA"),layer).convert("RGB")
    d=ImageDraw.Draw(im)
    d.rectangle((0,H-4,W*(t/DATA["duration"]),H),fill=GOLD)
    return np.array(im)

def make_music():
    sr=48000; duration=DATA["duration"];n=int(math.ceil(duration*sr))
    music=np.zeros((n,2),np.float32);beat=60/96;bar=4*beat
    chords=[[57,60,64,67],[53,57,60,64],[48,55,60,64],[55,59,62,67]]
    def hz(note):return 440*2**((note-69)/12)
    def add(start,length,notes,kind,amp,pan=.5):
        a=int(start*sr);count=min(int(length*sr),n-a)
        if count<=0:return
        t=np.arange(count,dtype=np.float32)/sr
        sig=np.zeros(count,np.float32)
        for note in notes:
            f=hz(note)
            if kind=="pad":
                env=np.minimum(t/.55,1)*np.minimum((length-t)/.75,1)
                tone=(np.sin(2*np.pi*f*t)+.22*np.sin(2*np.pi*f*2*t)+.08*np.sin(2*np.pi*f*3*t))
                sig+=tone*env/len(notes)
            else:
                env=(1-np.exp(-t*60))*np.exp(-t*5.2)*np.minimum((length-t)/.08,1)
                sig+=(np.sin(2*np.pi*f*t)+.16*np.sin(2*np.pi*f*2*t))*env/len(notes)
        music[a:a+count,0]+=sig*amp*math.sqrt(1-pan)
        music[a:a+count,1]+=sig*amp*math.sqrt(pan)
    for b in range(math.ceil(duration/bar)):
        chord=chords[b%4];start=b*bar
        add(start,bar+.7,chord,"pad",.22)
        add(start,bar,[chord[0]-12],"pad",.17,.5)
        for step in range(8):
            add(start+step*beat/2,1.1,[chord[[0,2,1,3,2,1,2,3][step]]+12],"pluck",.13,.32 if step%2==0 else .68)
    music/=max(float(np.max(np.abs(music))),.001)
    music*=.3
    tt=np.arange(n)/sr;gain=np.full(n,10**(-8/20),np.float32)
    voice=np.zeros(n,np.float32)
    for s in DATA["scenes"]:
        a=s["voiceStart"];b=a+s["voiceDuration"]
        active=np.minimum(np.clip((tt-(a-.12))/.12,0,1),np.clip(((b+.32)-tt)/.32,0,1))
        gain=np.minimum(gain,10**(-8/20)+(10**(-16/20)-10**(-8/20))*active)
        raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(OUT/"voice-narrador"/("voice-"+s["id"]+".mp3")),"-f","f32le","-ac","1","-ar",str(sr),"-"])
        samples=np.frombuffer(raw,np.float32).copy()
        rms=np.sqrt(np.mean(samples*samples));level=min(.16/max(rms,.001),.82/max(np.max(np.abs(samples)),.001))
        samples*=level;start=int(a*sr);count=min(len(samples),n-start);voice[start:start+count]+=samples[:count]
    music*=gain[:,None]
    fade=np.minimum(np.clip(tt/1.2,0,1),np.clip((duration-tt)/1.8,0,1))
    music*=fade[:,None]
    mixed=music+voice[:,None]
    mixed*=min(1,.94/max(float(np.max(np.abs(mixed))),.001))
    for name,array in [("mix.wav",mixed),("music-original-ducked.wav",music),("voice-full.wav",np.repeat(voice[:,None],2,axis=1))]:
        with wave.open(str(OUT/name),"wb") as audio:
            audio.setnchannels(2);audio.setsampwidth(2);audio.setframerate(sr);audio.writeframes((np.clip(array,-1,1)*32767).astype("<i2").tobytes())
    (OUT/"audio-mix.json").write_text(json.dumps({"music":"Original synthesis: 96 BPM, pad, pluck and bass; no third-party recording","sampleRate":sr,"musicGainDuringVoiceDb":-16,"musicGainOutsideVoiceDb":-8,"voice":"Narrador (grabación importada)","sourceSha256":json.loads((OUT/"voice-narrador"/"import-manifest.json").read_text(encoding="utf-8"))["sourceSha256"],"peakBeforeMaster":float(np.max(np.abs(mixed)))}),encoding="utf-8")

def previews(poster_path=None):
    frames=[]
    for s in DATA["scenes"]:
        t=s["start"]+min(4,(s["end"]-s["start"])/2)
        frame=Image.fromarray(make_frame(t));frame.save(OUT/("frame-"+s["id"]+".jpg"),quality=94)
        frames.append(ImageOps.contain(frame,(640,360)))
    sheet=Image.new("RGB",(1280,1080));[sheet.paste(im,((i%2)*640,(i//2)*360)) for i,im in enumerate(frames)]
    sheet.save(OUT/"storyboard-preview.jpg",quality=95)
    # Public poster generation is written into the same temporary bundle as the MP4.
    if poster_path is not None:
        poster=scene_frame(DATA["scenes"][0],4)
        d=ImageDraw.Draw(poster);d.rounded_rectangle((66,568,335,618),radius=8,fill=GOLD)
        d.text((85,580),"KADI EN ACCIÓN",font=font(20,True),fill=NAVY)
        poster.save(poster_path,format="WEBP",quality=90,method=6)

def validate_staged_bundle(stage):
    video=stage/"kadi-en-accion.mp4"
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,codec_name,width,height","-of","json",str(video)],text=True))
    duration=float(probe["format"]["duration"])
    streams=probe["streams"]
    if not 60<=duration<=85 or not any(s.get("codec_type")=="video" for s in streams) or not any(s.get("codec_type")=="audio" for s in streams):
        raise RuntimeError("El MP4 temporal no cumple duración o pistas requeridas.")
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(video),"-f","null","NUL"],check=True)
    transcript=(stage/"kadi-en-accion-transcripcion.txt").read_text(encoding="utf-8")
    expected="\n\n".join(scene["voice"] for scene in STORY["scenes"])
    if transcript!=expected or (stage/"kadi-en-accion.es.vtt").read_text(encoding="utf-8").count(" --> ")<6:
        raise RuntimeError("La transcripción o subtítulos temporales no corresponden a las seis escenas.")
    with Image.open(stage/"kadi-en-accion-poster.webp") as poster:
        poster.verify()

def encode_video_stage(stage,picture_encoder=None,audio_encoder=None):
    silent=stage/"kadi-picture.mp4"
    if picture_encoder is None:
        VideoClip(make_frame,duration=DATA["duration"]).write_videofile(str(silent),fps=FPS,codec="libx264",audio=False,preset="medium",threads=4,ffmpeg_params=["-crf","20","-pix_fmt","yuv420p"],logger=None)
    else:
        picture_encoder(silent)
    if not silent.is_file():
        raise RuntimeError("El encoder no produjo el video temporal.")
    target=stage/"kadi-en-accion.mp4"
    if audio_encoder is None:
        subprocess.run(["ffmpeg","-y","-v","warning","-i",str(silent),"-i",str(OUT/"mix.wav"),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-ar","48000","-b:a","160k","-af","loudnorm=I=-16:TP=-1.5:LRA=11","-movflags","+faststart","-shortest",str(target)],check=True)
    else:
        audio_encoder(silent,target)
    return target

def build_public_bundle(stage):
    previews(stage/"kadi-en-accion-poster.webp")
    make_music()
    write_captions_to(stage)
    encode_video_stage(stage)

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--preview-only",action="store_true");args=parser.parse_args()
    if not args.preview_only:
        validate_sol_import()
        if not 60<=DATA["duration"]<=85:raise ValueError("Duración fuera del brief.")
        stage_parent=ROOT/"output"/"temporal"
        outputs={
            "kadi-en-accion.mp4":PUBLIC/"kadi-en-accion.mp4",
            "kadi-en-accion.es.vtt":PUBLIC/"kadi-en-accion.es.vtt",
            "kadi-en-accion-transcripcion.txt":PUBLIC/"kadi-en-accion-transcripcion.txt",
            "kadi-en-accion-poster.webp":PUBLIC/"kadi-en-accion-poster.webp",
            "captions.json":OUT/"captions.json",
        }
        stage_validate_publish(stage_parent,outputs,build_public_bundle,validate_staged_bundle)
        print("RENDER_COMPLETE",outputs["kadi-en-accion.mp4"].stat().st_size,round(DATA["duration"],2),flush=True)
    else:
        previews()
