import { convertDocx } from './docx.ts';
import { convertDoc } from './doc.ts';
import { convertOdt } from './odt.ts';
import { convertRtf } from './rtf.ts';
import { convertHtml } from './html.ts';
import { convertXml } from './xml.ts';
import { convertTxt } from './txt.ts';
import { convertPdf } from './pdf.ts';
import { convertSpreadsheet } from './spreadsheet.ts';
import { convertEpub } from './epub.ts';

export type Converter = (filePath: string) => Promise<string>;

const REGISTRY: Record<string, Converter> = {
  '.docx': convertDocx,
  '.doc': convertDoc,
  '.odt': convertOdt,
  '.rtf': convertRtf,
  '.html': convertHtml,
  '.htm': convertHtml,
  '.xml': convertXml,
  '.txt': convertTxt,
  '.md': convertTxt,
  '.pdf': convertPdf,
  '.xlsx': convertSpreadsheet,
  '.xls': convertSpreadsheet,
  '.csv': convertSpreadsheet,
  '.tsv': convertSpreadsheet,
  '.epub': convertEpub,
};

export const SUPPORTED_EXTS: ReadonlySet<string> = new Set(Object.keys(REGISTRY));

export function getConverter(ext: string): Converter | undefined {
  return REGISTRY[ext.toLowerCase()];
}
