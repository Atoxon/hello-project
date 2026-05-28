import { readFile } from 'node:fs/promises';

export async function convertTxt(filePath: string): Promise<string> {
  const raw = await readFile(filePath, 'utf8');
  const normalized = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  return normalized.endsWith('\n') ? normalized : normalized + '\n';
}
