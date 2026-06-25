# Nghiên cứu: gstack (garrytan/gstack)

> Repo: https://github.com/garrytan/gstack
> Tác giả: Garry Tan (President & CEO của Y Combinator)
> License: MIT
> Ngày nghiên cứu: 2026-06-25

## 1. gstack là gì?

**gstack** là một bộ công cụ ("software factory") mã nguồn mở biến **Claude Code**
thành một **đội ngũ kỹ thuật ảo** (virtual engineering team). Thay vì chỉ prompt
rời rạc, gstack cung cấp một tập hợp các **slash-command skills** đóng vai trò như
các thành viên trong team:

- **CEO** — rà soát lại phạm vi & sản phẩm
- **Eng Manager** — chốt kiến trúc & luồng dữ liệu
- **Designer** — bắt lỗi "AI slop" về thiết kế
- **Reviewer (Staff Engineer)** — tìm bug production
- **QA Lead** — mở trình duyệt thật để test luồng
- **Security Officer (CSO)** — audit OWASP + STRIDE
- **Release Engineer** — tạo PR & ship

Mô tả chính thức của repo: *"Use Garry Tan's exact Claude Code setup: 23
opinionated tools that serve as CEO, Designer, Eng Manager, Release Manager,
Doc Engineer, and QA."*

> Lưu ý: số lượng "tools/skills" được nhắc tới khác nhau giữa các nguồn (23 trong
> tiêu đề repo, một số bài báo nói 31, một bản fork nói 15). Con số này thay đổi
> theo phiên bản — coi "~23–31 skills" là khoảng đáng tin.

## 2. Triết lý cốt lõi

gstack tổ chức xoay quanh một quy trình sprint:

```
Think → Plan → Build → Review → Test → Ship → Reflect
```

Mỗi giai đoạn có một "chuyên gia AI" phụ trách, và **output của skill này trở
thành input của skill kế tiếp** (ví dụ: design doc từ `/office-hours` được dùng
cho các bước review phía sau). Mục tiêu là không để công việc "lọt khe".

gstack được thiết kế để chống lại 4 kiểu thất bại khi code bằng AI (theo Andrej
Karpathy):
1. **Giả định sai** → giải quyết bằng `/office-hours`
2. **Phức tạp hóa quá mức** → bằng `/review`
3. **Sửa lung tung không liên quan (orthogonal edits)** → bằng `freeze`/`guard`
4. **Imperative thay vì declarative** → bằng `/ship` hướng mục tiêu

## 3. Danh sách skills tiêu biểu

### Lập kế hoạch & Kiến trúc
- `/office-hours` — "thẩm vấn" sản phẩm bằng các câu hỏi ép buộc làm rõ
- `/plan-ceo-review` — quyết định chiến lược về phạm vi
- `/plan-eng-review` — kiểm tra kiến trúc & luồng dữ liệu
- `/plan-design-review` — đánh giá chất lượng thiết kế
- `/plan-devex-review` — tối ưu trải nghiệm lập trình viên

### Triển khai (Build)
- `/design-consultation` — xây dựng design system hoàn chỉnh
- `/design-shotgun` — tạo nhiều mockup để khám phá hình ảnh
- `/design-html` — sinh markup/component sẵn sàng production
- `/autoplan` — pipeline review tự động

### Đảm bảo chất lượng (QA / Review)
- `/review` — phát hiện bug production (staff-engineer feedback)
- `/qa` — test bằng trình duyệt thật, tự sửa & commit fix
- `/cso` — audit bảo mật (OWASP + STRIDE)
- `/investigate` — debug truy vết nguyên nhân gốc
- `/codex` — review độc lập bằng model của OpenAI

### Ship & Tài liệu
- `/ship` — tự động tạo PR & test
- `/land-and-deploy` — merge → production & verify
- `/document-release`, `/document-generate` — cập nhật tài liệu tự động
- `/retro` — retrospective theo team

### Công cụ nâng cao & An toàn
- `/browse` — điều khiển Chromium thật
- `/pair-agent` — phối hợp đa AI (Claude + OpenClaw + khác)
- `/careful` — cảnh báo trước lệnh phá hủy
- `/freeze` / `/unfreeze` / `/guard` — giới hạn phạm vi sửa file

## 4. Tech stack

- **Ngôn ngữ**: TypeScript (~79%), Go Template (~11%), Shell (~6%), còn lại JS/CSS/HTML
- **Runtime**: **Bun** v1.0+ (Node.js trên Windows)
- **Trình duyệt**: Playwright + Chromium (có chống bot/stealth)
- **Database / Knowledge**: Supabase (cloud, tùy chọn) hoặc **PGLite** (local)
- **Testing**: tự sinh regression test

## 5. Kiến trúc (điểm đáng chú ý)

**Cấu trúc skill.** Mỗi skill là một prompt Claude theo template `SKILL.md`, kết
hợp prose do người viết + tham chiếu lệnh được auto-generate từ source code (để
docs không bị "trôi" khỏi implementation). Skill có thể phân cấp — ví dụ `/ship`
điều phối `/qa`, `/review` và logic deploy.

**GBrain (lớp tri thức bền vững).** Được tiêm vào các skill qua placeholder như
`{{GBRAIN_CONTEXT_LOAD}}` / `{{GBRAIN_SAVE_RESULTS}}`. Skill trích keyword từ ý
định người dùng, tìm trong "brain" các quan hệ thực thể liên quan, rồi lưu lại
kết quả → cho phép **học xuyên phiên** (cross-session learning). Có chính sách
trust theo từng repo (read-write / read-only / deny).

**lib/** chứa tiện ích dùng chung: registry lệnh, error wrapper, ref system,
security classifier, logging.

**Browser daemon.** Một Chromium daemon sống lâu, CLI nói chuyện qua HTTP
localhost. Lần đầu khởi động ~3s; các lệnh sau ~100–200ms nhờ tái dùng tab,
cookie, session — tránh overhead 40s+ khi mở trình duyệt mỗi lệnh.

**Ref system (`@e1`, `@e2`).** Map phần tử trang qua Playwright Locator dựng từ
accessibility tree, tránh xung đột DOM/CSP/hydration. Ref tự xóa khi điều hướng.

**Bảo mật.** Kiến trúc dual-listener tách port local và port tunnel ở tầng TCP
(ngrok chỉ forward port tunnel). Có bearer token theo scope, classifier chống
prompt-injection (BERT+DeBERTa), canary token. Cookie giải mã trong tiến trình
bằng PBKDF2+AES, không ghi plaintext ra đĩa.

**Quyết định thiết kế chính:** Bun thay Node (binary biên dịch, SQLite native);
mô hình daemon thay vì mở browser mỗi lệnh; HTTP thay vì WebSocket/MCP (đơn giản,
debug bằng curl); commit sẵn `SKILL.md` thay vì generate lúc runtime (CI validate
được, có git blame).

## 6. Cài đặt & sử dụng

Cài nhanh (~30 giây) trong Claude Code:

```bash
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git \
  ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup
```

Chế độ team (tự cập nhật):

```bash
(cd ~/.claude/skills/gstack && ./setup --team) && \
  ~/.claude/skills/gstack/bin/gstack-team-init required && \
  git add .claude/ CLAUDE.md && \
  git commit -m "require gstack for AI-assisted work"
```

Hỗ trợ nhiều AI agent ngoài Claude Code: OpenAI Codex, Cursor, Factory Droid, v.v.
Hỗ trợ macOS, Linux, Windows 11 (WSL/Git Bash).

## 7. Tuyên bố về năng suất (cần kiểm chứng)

Garry Tan công bố các con số ấn tượng khi dùng gstack (vẫn điều hành YC full-time):
- ~810× năng suất (thay đổi code logic, 2026 so với 2013)
- 600.000+ dòng code production trong ~60 ngày dùng bán thời gian (~10–20k dòng/ngày)
- ~35% test coverage duy trì xuyên suốt

> ⚠️ Đây là tuyên bố tự báo cáo (self-reported) mang tính marketing. Các con số
> sao (stars) cũng được nhắc tới rất khác nhau giữa các nguồn (từ "10.000 sao
> trong 48 giờ đầu" tới các con số lớn hơn nhiều). Nên kiểm chứng trực tiếp trên
> trang GitHub trước khi trích dẫn chính thức.

## 8. Đánh giá nhanh — gstack có gì đáng học?

**Điểm mạnh / ý tưởng hay:**
- Biến quy trình phát triển phần mềm thành các "vai trò" có thể tái dùng → buộc
  AI đi qua các bước kiểm tra (plan → review → QA → security → ship).
- Cơ chế **skill nối skill** (output làm input) là một pattern orchestration tốt.
- **Freeze/guard** và **careful** là cách thực dụng để hạn chế AI sửa lung tung.
- Browser daemon + ref system: giải pháp kỹ thuật thông minh cho QA bằng trình
  duyệt thật với latency thấp.

**Điểm cần cân nhắc:**
- Các con số năng suất là marketing, không phải benchmark độc lập.
- Phụ thuộc khá nhiều vào hệ sinh thái riêng (GBrain, GStack Browser).
- Phù hợp nhất với solo builder / team nhỏ muốn "đóng khung" quy trình AI-coding.

## Nguồn

- Repo chính: https://github.com/garrytan/gstack
- README, ARCHITECTURE.md của repo
- Augment Code: https://www.augmentcode.com/learn/garry-tan-gstack-claude-code
- SitePoint: https://www.sitepoint.com/gstack-garry-tan-claude-code/
- MindStudio: https://www.mindstudio.ai/blog/what-is-gstack-gary-tan-claude-code-framework
- explainx.ai: https://explainx.ai/blog/gstack-garry-tan-claude-code-skills-factory
