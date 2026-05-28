import EPub from 'epub2';
import { htmlToMarkdown } from './turndown-setup.ts';

interface ChapterRef {
  id: string;
  title?: string;
}

export async function convertEpub(filePath: string): Promise<string> {
  const epub: any = await new Promise((resolve, reject) => {
    const e = new EPub(filePath);
    e.on('error', reject);
    e.on('end', () => resolve(e));
    e.parse();
  });

  const flow: ChapterRef[] = epub.flow ?? [];
  const sections: string[] = [];

  for (const chap of flow) {
    const html: string = await new Promise((resolve, reject) => {
      epub.getChapter(chap.id, (err: Error | null, text: string) => {
        if (err) reject(err);
        else resolve(text ?? '');
      });
    });
    const md = htmlToMarkdown(html).trim();
    if (md) sections.push(md);
  }

  if (sections.length === 0) throw new Error('No chapters extracted from EPUB');
  return sections.join('\n\n---\n\n') + '\n';
}
