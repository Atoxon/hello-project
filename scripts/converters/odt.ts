import AdmZip from 'adm-zip';
import { JSDOM } from 'jsdom';

function nodeText(node: Element): string {
  return (node.textContent ?? '').replace(/\s+/g, ' ').trim();
}

export async function convertOdt(filePath: string): Promise<string> {
  const zip = new AdmZip(filePath);
  const entry = zip.getEntry('content.xml');
  if (!entry) throw new Error('Not a valid ODT (missing content.xml)');
  const xml = entry.getData().toString('utf8');

  const dom = new JSDOM(xml, { contentType: 'text/xml' });
  const doc = dom.window.document;

  const parts: string[] = [];
  const elements = doc.getElementsByTagName('*');
  for (let i = 0; i < elements.length; i++) {
    const el = elements[i];
    const tag = el.tagName.replace(/^.*:/, '');
    if (tag === 'h') {
      const level = parseInt(el.getAttribute('text:outline-level') ?? '1', 10) || 1;
      const t = nodeText(el);
      if (t) parts.push(`${'#'.repeat(Math.min(level, 6))} ${t}`);
    } else if (tag === 'p') {
      const parentTag = el.parentElement?.tagName.replace(/^.*:/, '');
      if (parentTag === 'h') continue;
      const t = nodeText(el);
      if (t) parts.push(t);
    } else if (tag === 'list-item') {
      const t = nodeText(el);
      if (t) parts.push(`- ${t}`);
    }
  }
  const md = parts.join('\n\n').trim();
  if (!md) throw new Error('No extractable text content in ODT');
  return md + '\n';
}
