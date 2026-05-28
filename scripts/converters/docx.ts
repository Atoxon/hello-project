import mammoth from 'mammoth';
import { htmlToMarkdown } from './turndown-setup.ts';

export async function convertDocx(filePath: string): Promise<string> {
  const result = await mammoth.convertToHtml({ path: filePath });
  return htmlToMarkdown(result.value);
}
