import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';

export async function convertXml(filePath: string): Promise<string> {
  const raw = await readFile(filePath, 'utf8');
  const dom = new JSDOM(raw, { contentType: 'text/xml' });
  const text = dom.window.document.documentElement?.textContent ?? '';
  const cleaned = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
    .join('\n\n');
  return cleaned + '\n';
}
