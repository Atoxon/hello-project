import { readFile } from 'node:fs/promises';
import { PDFParse } from 'pdf-parse';

export async function convertPdf(filePath: string): Promise<string> {
  const buf = await readFile(filePath);
  const parser = new PDFParse({ data: buf });
  try {
    const result = await parser.getText();
    const text = (result.text ?? '').trim();
    if (!text) throw new Error('No extractable text (PDF may be image-only, needs OCR)');
    const normalized = text.replace(/\r\n/g, '\n').replace(/\n{3,}/g, '\n\n');
    return normalized + '\n';
  } finally {
    await parser.destroy();
  }
}
