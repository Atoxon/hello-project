#!/usr/bin/env python3
"""
storyboard - Tự dựng timeline video từ kịch bản + ảnh.

Đầu vào: 1 file kịch bản JSON mô tả từng cảnh (ảnh, lời thoại, thời lượng).
Đầu ra : 1 file video MP4 đã ghép sẵn timeline.

Tính năng:
  - Tự tính thời lượng mỗi cảnh theo voiceover (TTS) hoặc theo số giây cố định.
  - TTS tiếng Việt (backend: edge-tts hoặc gTTS).
  - Phụ đề: ghi đè lên video (burn) hoặc xuất file .srt riêng.
  - Nhạc nền (tự lặp, chỉnh âm lượng).
  - Hiệu ứng Ken Burns (zoom/pan nhẹ cho ảnh tĩnh).
  - Chuyển cảnh fade (xfade) hoặc cắt cứng.
  - Khung 9:16 / 16:9 / 1:1 hoặc kích thước tuỳ ý.

Cách dùng:
    python3 storyboard.py kichban.json
    python3 storyboard.py kichban.json -o video.mp4
    python3 storyboard.py kichban.json --dry-run      # chỉ in timeline, không render
    python3 storyboard.py --init kichban.json         # tạo file kịch bản mẫu

Xem README.md để biết định dạng file kịch bản.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave
import contextlib

# --------------------------------------------------------------------------- #
# Tìm ffmpeg / ffprobe
# --------------------------------------------------------------------------- #

def find_ffmpeg():
    """Trả về (ffmpeg, ffprobe). Ưu tiên ffmpeg hệ thống, sau đó imageio-ffmpeg."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg:
        return ffmpeg, ffprobe  # ffprobe có thể None -> dùng fallback đo wav
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe(), None
    except Exception:
        sys.exit(
            "Không tìm thấy ffmpeg.\n"
            "  - Cài hệ thống:  apt install ffmpeg  (hoặc brew install ffmpeg)\n"
            "  - Hoặc:          pip install imageio-ffmpeg"
        )


FFMPEG, FFPROBE = find_ffmpeg()


def run(cmd, **kw):
    """Chạy lệnh, raise nếu lỗi, trả về CompletedProcess."""
    proc = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if proc.returncode != 0:
        sys.stderr.write("\n[LỖI] Lệnh thất bại:\n  " + " ".join(cmd) + "\n")
        sys.stderr.write(proc.stderr[-4000:] + "\n")
        raise SystemExit(1)
    return proc


# --------------------------------------------------------------------------- #
# Khung hình
# --------------------------------------------------------------------------- #

ASPECT_PRESETS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
}


def parse_size(aspect):
    if aspect in ASPECT_PRESETS:
        return ASPECT_PRESETS[aspect]
    if "x" in aspect.lower():
        w, h = aspect.lower().split("x")
        return int(w), int(h)
    raise ValueError(f"Tỉ lệ khung không hợp lệ: {aspect!r} "
                     f"(dùng {', '.join(ASPECT_PRESETS)} hoặc 'WxH' vd 1080x1920)")


# --------------------------------------------------------------------------- #
# TTS (text-to-speech)
# --------------------------------------------------------------------------- #

def tts_generate(text, out_path, backend, voice, rate):
    """Tạo file audio voiceover từ text. Trả về True nếu thành công."""
    text = (text or "").strip()
    if not text:
        return False
    if backend == "edge":
        return _tts_edge(text, out_path, voice, rate)
    if backend == "gtts":
        return _tts_gtts(text, out_path)
    raise ValueError(f"TTS backend không hỗ trợ: {backend!r} (dùng 'edge' hoặc 'gtts')")


def _tts_edge(text, out_path, voice, rate):
    try:
        import edge_tts
    except ImportError:
        sys.exit("Cần edge-tts cho TTS backend 'edge':  pip install edge-tts")
    import asyncio

    async def _go():
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
        await communicate.save(out_path)

    asyncio.run(_go())
    return os.path.exists(out_path) and os.path.getsize(out_path) > 0


def _tts_gtts(text, out_path):
    try:
        from gtts import gTTS
    except ImportError:
        sys.exit("Cần gTTS cho TTS backend 'gtts':  pip install gTTS")
    gTTS(text=text, lang="vi").save(out_path)
    return os.path.exists(out_path) and os.path.getsize(out_path) > 0


# --------------------------------------------------------------------------- #
# Đo thời lượng audio
# --------------------------------------------------------------------------- #

def audio_duration(path):
    """Đo thời lượng (giây) của 1 file audio."""
    if FFPROBE:
        proc = run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", path])
        return float(proc.stdout.strip())
    # Fallback: decode sang wav tạm rồi đọc header
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = tmp.name
    try:
        run([FFMPEG, "-y", "-i", path, wav])
        with contextlib.closing(wave.open(wav, "rb")) as w:
            return w.getnframes() / float(w.getframerate())
    finally:
        if os.path.exists(wav):
            os.remove(wav)


# --------------------------------------------------------------------------- #
# Phụ đề (.srt)
# --------------------------------------------------------------------------- #

def fmt_ts(seconds):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(scenes, path):
    """Mỗi cảnh = 1 dòng phụ đề kéo dài suốt cảnh đó (file .srt chuẩn)."""
    lines = []
    t = 0.0
    idx = 1
    for sc in scenes:
        text = (sc.get("subtitle") or sc.get("narration") or "").strip()
        dur = sc["_duration"]
        if text:
            lines.append(str(idx))
            lines.append(f"{fmt_ts(t)} --> {fmt_ts(t + dur)}")
            lines.append(text)
            lines.append("")
            idx += 1
        t += dur
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def fmt_ass_ts(seconds):
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def write_ass(scenes, path, w, h, font_size):
    """Sinh file .ass với PlayRes đúng khung hình -> FontSize tính theo pixel thật."""
    margin_v = max(40, int(h * 0.06))
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {w}\nPlayResY: {h}\n"
        "WrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,DejaVu Sans,{font_size},&H00FFFFFF,&H00000000,&H00000000,"
        f"1,0,0,0,100,100,0,0,1,3,1,2,80,80,{margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = []
    t = 0.0
    for sc in scenes:
        text = (sc.get("subtitle") or sc.get("narration") or "").strip()
        dur = sc["_duration"]
        if text:
            text = text.replace("\n", "\\N")
            events.append(
                f"Dialogue: 0,{fmt_ass_ts(t)},{fmt_ass_ts(t + dur)},Default,,0,0,0,,{text}")
        t += dur
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")


# --------------------------------------------------------------------------- #
# Dựng video
# --------------------------------------------------------------------------- #

def scene_video_filter(w, h, fps, dur, motion, idx):
    """Filter biến 1 ảnh tĩnh thành đoạn video w x h dài `dur` giây."""
    frames = max(1, int(round(dur * fps)))
    if motion == "kenburns":
        # Phóng to nguồn lên để zoom mượt, rồi zoompan zoom-in / zoom-out xen kẽ.
        if idx % 2 == 0:
            z = "min(zoom+0.0012,1.20)"          # zoom in
        else:
            z = "if(eq(on,0),1.20,max(zoom-0.0012,1.0))"  # zoom out
        return (
            f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
            f"crop={w*2}:{h*2},"
            f"zoompan=z='{z}':d={frames}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s={w}x{h}:fps={fps},"
            f"setsar=1,format=yuv420p"
        )
    # Không chuyển động: scale vừa khung + viền đen.
    return (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"fps={fps},setsar=1,format=yuv420p"
    )


def render_scene_clip(scene, w, h, fps, motion, out_path):
    """Render 1 cảnh (ảnh + audio nếu có) ra 1 file mp4 trung gian."""
    dur = scene["_duration"]
    img = scene["image"]
    if not os.path.exists(img):
        sys.exit(f"Không tìm thấy ảnh: {img}")

    vf = scene_video_filter(w, h, fps, dur, motion, scene["_index"])
    audio = scene.get("_audio")

    # --- INPUTS (phải đứng trước mọi output option) ---
    cmd = [FFMPEG, "-y", "-loop", "1", "-t", f"{dur:.3f}", "-i", img]
    if audio:
        cmd += ["-i", audio]
    else:
        # Track im lặng để mọi clip đồng nhất (dễ concat / mix).
        cmd += ["-f", "lavfi", "-t", f"{dur:.3f}",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]

    # --- OUTPUT OPTIONS ---
    cmd += ["-vf", vf, "-r", str(fps), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]

    if audio:
        # Đệm im lặng đầu cảnh, cắt/đệm audio cho khớp đúng thời lượng cảnh.
        lead = scene.get("_lead", 0.0)
        cmd += ["-af",
                f"adelay={int(lead*1000)}|{int(lead*1000)},"
                f"apad,atrim=0:{dur:.3f},aresample=44100"]

    cmd += ["-t", f"{dur:.3f}", out_path]
    run(cmd)


def concat_plain(clips, out_path):
    """Ghép các clip bằng concat demuxer (cắt cứng, nhanh)."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        listfile = f.name
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    try:
        run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", listfile,
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
             "-c:a", "aac", "-b:a", "192k", out_path])
    finally:
        os.remove(listfile)


def concat_xfade(clips, durations, fps, td, out_path):
    """Ghép với chuyển cảnh fade (xfade video + acrossfade audio)."""
    inputs = []
    for c in clips:
        inputs += ["-i", c]

    n = len(clips)
    fc = []
    # Chuẩn hoá từng input
    for i in range(n):
        fc.append(f"[{i}:v]settb=AVTB,fps={fps}[v{i}]")
        fc.append(f"[{i}:a]aresample=44100,asetpts=PTS-STARTPTS[a{i}]")

    # Chuỗi xfade: offset cộng dồn, trừ thời lượng fade.
    vcur = "v0"
    acur = "a0"
    offset = durations[0] - td
    for i in range(1, n):
        vout = f"vx{i}"
        aout = f"ax{i}"
        fc.append(f"[{vcur}][v{i}]xfade=transition=fade:duration={td}:offset={offset:.3f}[{vout}]")
        fc.append(f"[{acur}][a{i}]acrossfade=d={td}[{aout}]")
        vcur, acur = vout, aout
        if i < n - 1:
            offset += durations[i] - td

    cmd = [FFMPEG, "-y"] + inputs + [
        "-filter_complex", ";".join(fc),
        "-map", f"[{vcur}]", "-map", f"[{acur}]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", out_path]
    run(cmd)


def add_background_music(video, music, volume, out_path):
    """Trộn nhạc nền (lặp vô hạn, cắt theo video) vào audio sẵn có."""
    run([FFMPEG, "-y", "-i", video, "-stream_loop", "-1", "-i", music,
         "-filter_complex",
         f"[1:a]volume={volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[a]",
         "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out_path])


def burn_subtitles(video, ass_path, out_path):
    """Ghi phụ đề (file .ass) lên video. FontSize/PlayRes đã tính sẵn trong file."""
    ass_esc = ass_path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    run([FFMPEG, "-y", "-i", video,
         "-vf", f"ass='{ass_esc}'",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
         "-c:a", "copy", out_path])


# --------------------------------------------------------------------------- #
# Quy trình chính
# --------------------------------------------------------------------------- #

def resolve_durations(cfg, workdir):
    """Tính thời lượng mỗi cảnh, sinh TTS nếu cần."""
    tts = cfg.get("tts", {})
    tts_on = tts.get("enabled", False)
    backend = tts.get("backend", "edge")
    voice = tts.get("voice", "vi-VN-HoaiMyNeural")
    rate = tts.get("rate", "+0%")
    lead = float(tts.get("lead", 0.3))   # im lặng đầu cảnh
    tail = float(tts.get("tail", 0.6))   # đệm cuối cảnh
    default_dur = float(cfg.get("default_duration", 4.0))

    base_dir = cfg.get("_base_dir", ".")
    for i, sc in enumerate(cfg["scenes"]):
        sc["_index"] = i
        # Đường dẫn ảnh tương đối so với file kịch bản
        if not os.path.isabs(sc["image"]):
            sc["image"] = os.path.join(base_dir, sc["image"])

        explicit = sc.get("duration")
        if tts_on and (sc.get("narration") or "").strip():
            audio_path = os.path.join(workdir, f"tts_{i:03d}.mp3")
            ok = tts_generate(sc["narration"], audio_path, backend, voice, rate)
            if ok:
                spoken = audio_duration(audio_path)
                sc["_audio"] = audio_path
                sc["_lead"] = lead
                sc["_duration"] = max(explicit or 0.0, lead + spoken + tail)
                continue
        # Không TTS: dùng duration khai báo hoặc mặc định
        sc["_duration"] = float(explicit) if explicit else default_dur

    return cfg


def build(cfg, out_path, dry_run=False):
    w, h = parse_size(cfg.get("aspect", "9:16"))
    fps = int(cfg.get("fps", 30))
    motion = cfg.get("motion", "kenburns")
    transition = cfg.get("transition", "fade")
    td = float(cfg.get("transition_duration", 0.5))
    subs = cfg.get("subtitles", {})

    workdir = tempfile.mkdtemp(prefix="storyboard_")
    try:
        resolve_durations(cfg, workdir)
        scenes = cfg["scenes"]

        # In timeline
        print(f"\n  Khung: {w}x{h} @ {fps}fps | chuyển cảnh: {transition} "
              f"| motion: {motion}")
        print("  " + "-" * 56)
        t = 0.0
        for sc in scenes:
            d = sc["_duration"]
            tag = "♪" if sc.get("_audio") else " "
            txt = (sc.get("narration") or sc.get("subtitle") or "")[:38]
            print(f"  {tag} [{t:6.1f}s → {t+d:6.1f}s] ({d:4.1f}s) "
                  f"{os.path.basename(sc['image']):<18} {txt}")
            t += d
        print("  " + "-" * 56)
        print(f"  Tổng thời lượng: {t:.1f}s ({len(scenes)} cảnh)\n")

        if dry_run:
            print("  (--dry-run: chỉ hiển thị timeline, không render)")
            return

        # Render từng cảnh
        clips = []
        for i, sc in enumerate(scenes):
            clip = os.path.join(workdir, f"clip_{i:03d}.mp4")
            print(f"  Đang dựng cảnh {i+1}/{len(scenes)} ...")
            render_scene_clip(sc, w, h, fps, motion, clip)
            clips.append(clip)

        # Ghép
        merged = os.path.join(workdir, "merged.mp4")
        durations = [sc["_duration"] for sc in scenes]
        if transition == "fade" and len(clips) > 1:
            print("  Đang ghép (fade) ...")
            concat_xfade(clips, durations, fps, td, merged)
        else:
            print("  Đang ghép (cắt) ...")
            concat_plain(clips, merged)

        current = merged

        # Nhạc nền
        bg = cfg.get("background_music")
        if bg and bg.get("path"):
            music = bg["path"]
            if not os.path.isabs(music):
                music = os.path.join(cfg.get("_base_dir", "."), music)
            if os.path.exists(music):
                print("  Đang trộn nhạc nền ...")
                withmusic = os.path.join(workdir, "withmusic.mp4")
                add_background_music(current, music, float(bg.get("volume", 0.15)),
                                     withmusic)
                current = withmusic
            else:
                print(f"  [Cảnh báo] Không tìm thấy nhạc nền: {music} (bỏ qua)")

        # Phụ đề
        if subs.get("enabled"):
            srt_path = os.path.splitext(out_path)[0] + ".srt"
            write_srt(scenes, srt_path)
            print(f"  Đã ghi phụ đề: {srt_path}")
            if subs.get("burn", True):
                print("  Đang ghi phụ đề lên video ...")
                ass_path = os.path.join(workdir, "subs.ass")
                write_ass(scenes, ass_path, w, h, int(subs.get("font_size", 48)))
                final = os.path.join(workdir, "final.mp4")
                burn_subtitles(current, ass_path, final)
                current = final

        shutil.move(current, out_path)
        print(f"\n  ✅ Xong: {out_path}\n")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Kịch bản mẫu
# --------------------------------------------------------------------------- #

SAMPLE = {
    "title": "Video demo",
    "aspect": "9:16",
    "fps": 30,
    "motion": "kenburns",
    "transition": "fade",
    "transition_duration": 0.5,
    "default_duration": 4.0,
    "tts": {
        "enabled": True,
        "backend": "edge",
        "voice": "vi-VN-HoaiMyNeural",
        "rate": "+0%",
        "lead": 0.3,
        "tail": 0.6
    },
    "subtitles": {"enabled": True, "burn": True, "font_size": 48},
    "background_music": {"path": "music.mp3", "volume": 0.12},
    "scenes": [
        {
            "image": "images/scene1.png",
            "prompt": "(prompt tạo ảnh của bạn - chỉ để ghi chú)",
            "narration": "Ngày xửa ngày xưa, ở một ngôi làng nhỏ ven rừng..."
        },
        {
            "image": "images/scene2.png",
            "prompt": "...",
            "narration": "Có một cô bé luôn mơ ước được khám phá thế giới."
        },
        {
            "image": "images/scene3.png",
            "narration": "Và rồi một ngày, cuộc phiêu lưu của cô bắt đầu.",
            "duration": 5.0
        }
    ]
}


def init_scenario(path):
    if os.path.exists(path):
        sys.exit(f"File đã tồn tại: {path}")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(SAMPLE, f, ensure_ascii=False, indent=2)
    print(f"Đã tạo kịch bản mẫu: {path}")
    print("Sửa lại đường dẫn ảnh + lời thoại rồi chạy:")
    print(f"    python3 storyboard.py {path}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser(
        description="Tự dựng timeline video từ kịch bản JSON + ảnh.")
    ap.add_argument("scenario", help="File kịch bản JSON")
    ap.add_argument("-o", "--output", help="File video đầu ra (mặc định: <title>.mp4)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Chỉ in timeline, không render")
    ap.add_argument("--init", action="store_true",
                    help="Tạo file kịch bản mẫu tại đường dẫn `scenario`")
    args = ap.parse_args()

    if args.init:
        init_scenario(args.scenario)
        return

    if not os.path.exists(args.scenario):
        sys.exit(f"Không tìm thấy kịch bản: {args.scenario}\n"
                 f"(Tạo mẫu:  python3 storyboard.py --init {args.scenario})")

    with open(args.scenario, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["_base_dir"] = os.path.dirname(os.path.abspath(args.scenario))

    if not cfg.get("scenes"):
        sys.exit("Kịch bản không có cảnh nào (thiếu khoá 'scenes').")

    out = args.output
    if not out:
        title = cfg.get("title", "output")
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title).strip()
        out = (safe or "output") + ".mp4"

    build(cfg, out, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
