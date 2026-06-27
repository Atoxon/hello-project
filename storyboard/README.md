# storyboard — Tự dựng timeline video từ kịch bản + ảnh

Bạn đưa vào **1 file kịch bản JSON** (gồm: ảnh + lời thoại + thời lượng cho từng cảnh),
công cụ sẽ **tự sắp xếp timeline** và xuất ra **video MP4** hoàn chỉnh.

Đúng quy trình bạn mô tả: *có kịch bản → có prompt tạo ảnh → tạo ra ảnh → công cụ tự dựng video.*

> Đây chính là phần OpenCut **không** làm được (OpenCut chỉ dựng tay). Công cụ này là 1 CLI riêng,
> chạy bằng **FFmpeg**, không phụ thuộc OpenCut.

## Tính năng

- ⏱️ **Tự tính thời lượng mỗi cảnh** theo voiceover (TTS) hoặc theo số giây cố định.
- 🗣️ **Voiceover tiếng Việt (TTS)** — backend `edge-tts` (tự nhiên, miễn phí) hoặc `gTTS`.
- 💬 **Phụ đề** — ghi đè lên video (burn) hoặc xuất file `.srt` riêng. Hỗ trợ dấu tiếng Việt.
- 🎵 **Nhạc nền** — tự lặp theo độ dài video, chỉnh âm lượng.
- 🎞️ **Ken Burns** — zoom/pan nhẹ cho ảnh tĩnh đỡ nhàm.
- 🔀 **Chuyển cảnh** — fade (mượt) hoặc cắt cứng.
- 📐 **Khung hình** — 9:16, 16:9, 1:1, 4:5 hoặc kích thước tuỳ ý (`1080x1920`).

## Cài đặt

```bash
cd storyboard
pip install -r requirements.txt
```

- **FFmpeg**: nếu máy đã có `ffmpeg` thì dùng luôn; nếu chưa, gói `imageio-ffmpeg` kèm sẵn 1 bản.
- **TTS** chỉ cần khi `tts.enabled = true` và cần **internet** (mọi backend đều gọi dịch vụ online).

## Giọng đọc (TTS) & API key

Có 5 backend, chọn ở `tts.backend`:

| backend      | API key? | Biến môi trường            | Ghi chú                                   |
|--------------|----------|----------------------------|-------------------------------------------|
| `edge`       | Không    | —                          | Mặc định. Giọng VN tự nhiên, `pip install edge-tts` |
| `gtts`       | Không    | —                          | Google Translate TTS, `pip install gTTS`  |
| `openai`     | Có       | `OPENAI_API_KEY`           | Giọng: alloy, echo, nova, shimmer...      |
| `elevenlabs` | Có       | `ELEVENLABS_API_KEY`       | `voice` = voice_id; chất lượng cao        |
| `azure`      | Có       | `AZURE_SPEECH_KEY` (+ `AZURE_SPEECH_REGION`) | Giọng `vi-VN-HoaiMyNeural`... |

### Cách cung cấp API key (cho backend trả phí)

Thứ tự ưu tiên khi lấy key:

1. **Khai báo thẳng trong kịch bản**: `tts.api_key` (tiện nhưng đừng commit lên git).
2. **Biến môi trường / file `.env`**:
   ```bash
   cp .env.example .env      # rồi điền key vào .env
   # hoặc: export OPENAI_API_KEY=sk-...
   ```
   `.env` được tự nạp từ: file truyền qua `--env`, rồi `.env` cạnh kịch bản, rồi `.env` ở thư mục hiện tại.
3. **Hỏi nhập trực tiếp**: nếu chạy ở terminal mà chưa tìm thấy key, công cụ sẽ
   **hỏi nhập key** (ẩn ký tự) và cho phép **lưu vào `.env`** để lần sau khỏi nhập lại.

> `.env` đã được thêm vào `.gitignore` — sẽ không bị commit.

Có thể đổi tên biến môi trường bằng `tts.api_key_env`. Ví dụ kịch bản dùng OpenAI:

```jsonc
"tts": {
  "enabled": true,
  "backend": "openai",
  "voice": "nova",
  "model": "gpt-4o-mini-tts"
  // key lấy từ OPENAI_API_KEY trong .env, hoặc sẽ được hỏi khi chạy
}
```

## Dùng nhanh

```bash
# 1) Tạo file kịch bản mẫu
python3 storyboard.py --init kichban.json

# 2) Sửa kichban.json: trỏ đúng đường dẫn ảnh + điền lời thoại

# 3) Xem trước timeline (không render)
python3 storyboard.py kichban.json --dry-run

# 4) Render ra video
python3 storyboard.py kichban.json -o video.mp4
```

Đường dẫn ảnh/nhạc trong kịch bản được hiểu **tương đối so với chính file kịch bản**.

## Định dạng file kịch bản

```jsonc
{
  "title": "Tên video",         // dùng đặt tên file nếu không truyền -o
  "aspect": "9:16",              // 9:16 | 16:9 | 1:1 | 4:5 | "1080x1920"
  "fps": 30,
  "motion": "kenburns",         // kenburns | none
  "transition": "fade",         // fade | none
  "transition_duration": 0.5,   // giây, dùng khi transition = fade
  "default_duration": 4.0,      // giây mặc định khi cảnh không có duration & không có TTS

  "tts": {
    "enabled": true,
    "backend": "edge",          // edge | gtts
    "voice": "vi-VN-HoaiMyNeural",
    "rate": "+0%",              // tốc độ đọc, vd "+10%", "-10%"
    "lead": 0.3,                // im lặng đầu cảnh (giây)
    "tail": 0.6                 // đệm cuối cảnh (giây)
  },

  "subtitles": {
    "enabled": true,
    "burn": true,               // true: ghi lên video | false: chỉ xuất .srt
    "font_size": 48             // tính theo pixel của khung hình
  },

  "background_music": {          // bỏ khoá này nếu không cần nhạc nền
    "path": "music.mp3",
    "volume": 0.12              // 0.0 - 1.0
  },

  "scenes": [
    {
      "image": "images/scene1.png",
      "prompt": "prompt bạn dùng để tạo ảnh (chỉ để ghi chú, không bắt buộc)",
      "narration": "Lời thoại cảnh này — dùng cho TTS và phụ đề.",
      "duration": null,         // (tuỳ chọn) ép thời lượng cố định, giây
      "subtitle": null          // (tuỳ chọn) chữ phụ đề khác với narration
    }
  ]
}
```

### Quy tắc tính thời lượng mỗi cảnh

1. `tts.enabled = true` và cảnh có `narration` → thời lượng = thời gian đọc + `lead` + `tail`
   (và không nhỏ hơn `duration` nếu có khai báo).
2. Ngược lại → dùng `duration` của cảnh; nếu không có thì dùng `default_duration`.

> Khi dùng `transition: "fade"`, tổng thời lượng video sẽ ngắn hơn tổng các cảnh
> một chút vì các cảnh chồng lên nhau khi fade (mỗi mối nối bớt `transition_duration` giây).

## Giọng đọc tiếng Việt (edge-tts) thường dùng

- `vi-VN-HoaiMyNeural` (nữ)
- `vi-VN-NamMinhNeural` (nam)

Liệt kê toàn bộ giọng: `edge-tts --list-voices | grep vi-VN`

## Gợi ý workflow hoàn chỉnh

1. Viết kịch bản, chia thành các cảnh (mỗi cảnh 1 câu/ý + 1 prompt ảnh).
2. Dùng công cụ tạo ảnh (Gemini/SD/Midjourney...) sinh ảnh theo từng prompt, lưu vào `images/`.
3. Điền `image` + `narration` cho từng cảnh trong file kịch bản.
4. `python3 storyboard.py kichban.json -o video.mp4`.

## Ví dụ

Xem `examples/scenario.example.json`. Có sẵn 3 ảnh demo trong `examples/images/`.

```bash
# Demo nhanh (tắt TTS, dùng thời lượng cố định) - không cần internet:
python3 storyboard.py examples/scenario.example.json --dry-run
```
