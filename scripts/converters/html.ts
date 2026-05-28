import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';
import { htmlToMarkdown } from './turndown-setup.ts';

export async function convertHtml(filePath: string): Promise<string> {
  const raw = await readFile(filePath, 'utf8');
  const looksFull = /<html[\s>]/i.test(raw) || /<body[\s>]/i.test(raw);
  if (looksFull) {
    const dom = new JSDOM(raw);
    return htmlToMarkdown(dom.window.document.body?.innerHTML ?? raw);
  }
  return htmlToMarkdown(raw);
}
