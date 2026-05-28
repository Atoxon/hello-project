import { readFile } from 'node:fs/promises';
import rtfToHTML from '@iarna/rtf-to-html';
import { JSDOM } from 'jsdom';
import { htmlToMarkdown } from './turndown-setup.ts';

export async function convertRtf(filePath: string): Promise<string> {
  const buf = await readFile(filePath);
  const html: string = await new Promise((resolve, reject) => {
    rtfToHTML.fromString(buf.toString('utf8'), (err: Error | null, out: string) => {
      if (err) reject(err);
      else resolve(out);
    });
  });
  const dom = new JSDOM(html);
  dom.window.document.querySelectorAll('style, script').forEach((el) => el.remove());
  const bodyHtml = dom.window.document.body?.innerHTML ?? html;
  return htmlToMarkdown(bodyHtml);
}
