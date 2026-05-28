<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/9784f8c3-80d2-4ea7-9876-43e604974f8e

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`

## Document → Markdown converter (CLI)

A standalone CLI under `scripts/` converts text-based documents into Markdown.
It is designed to be invoked by an AI agent and emits a JSON report on stdout.

### Usage

```bash
npm run convert --silent -- <path-to-file-or-folder>
```

- If `<path>` is a file, only that file is converted.
- If `<path>` is a folder, the folder is walked **recursively** and every supported file is converted.
- Each output `.md` is written next to the source file with the same base name.
- If the target name already exists, a suffix is appended (`name-1.md`, `name-2.md`, …) — no overwrite.

### Supported formats

`.docx`, `.doc`, `.odt`, `.rtf`, `.html`, `.htm`, `.xml`, `.txt`, `.md`,
`.pdf`, `.xlsx`, `.xls`, `.csv`, `.tsv`, `.epub`.

Spreadsheets are rendered as GitHub-flavored Markdown tables (multi-sheet workbooks become one section per sheet).

### Output (stdout)

```json
{
  "success": true,
  "summary": { "total": 3, "converted": 3, "failed": 0, "skipped": 0 },
  "results": [
    { "input": "/abs/path/a.docx", "output": "/abs/path/a.md", "status": "converted" }
  ]
}
```

### Exit codes

- `0` — all files converted (or zero supported files found)
- `1` — at least one file failed conversion
- `2` — usage error / path not accessible

### Security hardening (enterprise)

The converter is designed to be safe to run on untrusted documents but it executes parsers from the npm ecosystem. The following safeguards ship by default:

- **Per-file size limit** (`CONVERT_MAX_FILE_SIZE_MB`, default `50`): files larger than this are rejected before parsing.
- **Per-file timeout** (`CONVERT_FILE_TIMEOUT_MS`, default `30000`): each conversion is wrapped in a hard timeout to bound DoS exposure.
- **Error isolation**: a failure on one file does not abort the batch; each file gets its own try/catch and a structured `failed` entry in the JSON output.
- **No network calls** from any converter — they are pure parsers reading the input file.
- **No script execution**: `jsdom` is used without `runScripts`, `.doc`/`.docx` parsers only read text streams (no VBA macro execution).
- **`uuid` overridden to `^11.1.1`** in `package.json` to patch the known buffer-bounds advisory pulled in via `exceljs`.

#### CI audit gate

Run `npm run audit:ci` — fails the build on any **high** or **critical** advisory:

```bash
npm run audit:ci
```

Configured via `audit-ci.json`. Currently reports `0 vulnerabilities`.

#### Sandboxed container

`Dockerfile.convert` builds a hardened runtime image. Recommended run flags:

```bash
docker build -f Dockerfile.convert -t doc2md .
docker run --rm \
  --network=none --read-only --tmpfs /tmp \
  --cap-drop=ALL --security-opt no-new-privileges \
  --memory=512m --pids-limit=128 \
  -v /host/path/to/docs:/work \
  doc2md /work
```

This blocks outbound network, drops Linux capabilities, prevents privilege escalation, and caps memory/PIDs — so even an RCE in a parser cannot reach the network or persist.
