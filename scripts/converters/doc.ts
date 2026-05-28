import WordExtractor from 'word-extractor';

export async function convertDoc(filePath: string): Promise<string> {
  const extractor = new WordExtractor();
  const doc = await extractor.extract(filePath);
  const body = (doc.getBody() ?? '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();
  if (!body) throw new Error('Empty document or unreadable .doc binary');
  return body + '\n';
}
