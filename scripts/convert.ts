import { writeFile, stat, readdir } from 'node:fs/promises';
import { resolve, extname, basename, dirname, join } from 'node:path';
import { getConverter, SUPPORTED_EXTS } from './converters/index.ts';
import { findAvailableOutputPath } from './converters/paths.ts';

interface ResultEntry {
  input: string;
  output: string | null;
  status: 'converted' | 'failed' | 'skipped';
  error?: string;
}

async function collectFiles(target: string): Promise<string[]> {
  const s = await stat(target);
  if (s.isFile()) return [target];
  if (!s.isDirectory()) return [];

  const out: string[] = [];
  const entries = await readdir(target, { withFileTypes: true, recursive: true });
  for (const e of entries) {
    if (!e.isFile()) continue;
    const ext = extname(e.name).toLowerCase();
    if (ext === '.md') continue;
    if (!SUPPORTED_EXTS.has(ext)) continue;
    const parent = (e as { parentPath?: string; path?: string }).parentPath
      ?? (e as { path?: string }).path
      ?? target;
    out.push(join(parent, e.name));
  }
  return out;
}

async function convertOne(filePath: string): Promise<ResultEntry> {
  const ext = extname(filePath).toLowerCase();
  const converter = getConverter(ext);
  if (!converter) {
    return { input: filePath, output: null, status: 'skipped', error: `Unsupported extension: ${ext}` };
  }
  try {
    const markdown = await converter(filePath);
    const dir = dirname(filePath);
    const base = basename(filePath, ext);
    const outputPath = findAvailableOutputPath(dir, base);
    await writeFile(outputPath, markdown, 'utf8');
    return { input: filePath, output: outputPath, status: 'converted' };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { input: filePath, output: null, status: 'failed', error: message };
  }
}

async function main(): Promise<void> {
  const argv = process.argv.slice(2);
  if (argv.length === 0) {
    process.stdout.write(JSON.stringify({
      success: false,
      error: 'Usage: npm run convert -- <file_or_folder_path>',
      supported: [...SUPPORTED_EXTS].sort(),
    }) + '\n');
    process.exit(2);
  }

  const target = resolve(argv[0]);

  let files: string[];
  try {
    files = await collectFiles(target);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    process.stdout.write(JSON.stringify({
      success: false,
      error: `Cannot access ${target}: ${message}`,
    }) + '\n');
    process.exit(2);
  }

  if (files.length === 0) {
    process.stdout.write(JSON.stringify({
      success: true,
      summary: { total: 0, converted: 0, failed: 0, skipped: 0 },
      results: [],
      note: 'No supported files found',
    }) + '\n');
    process.exit(0);
  }

  const results: ResultEntry[] = [];
  for (const file of files) {
    results.push(await convertOne(file));
  }

  const summary = {
    total: results.length,
    converted: results.filter((r) => r.status === 'converted').length,
    failed: results.filter((r) => r.status === 'failed').length,
    skipped: results.filter((r) => r.status === 'skipped').length,
  };

  const output = {
    success: summary.failed === 0,
    summary,
    results,
  };
  process.stdout.write(JSON.stringify(output, null, 2) + '\n');
  process.exit(summary.failed > 0 ? 1 : 0);
}

main().catch((err) => {
  const message = err instanceof Error ? err.stack ?? err.message : String(err);
  process.stdout.write(JSON.stringify({ success: false, error: message }) + '\n');
  process.exit(2);
});
