import { readFile } from 'node:fs/promises';
import { extname } from 'node:path';
import xlsx from 'xlsx';
import { parse as parseCsv } from 'csv-parse/sync';

const { readFile: xlsxReadFile, utils: xlsxUtils } = xlsx;

function escapeCell(value: unknown): string {
  if (value === null || value === undefined) return '';
  const s = String(value);
  return s.replace(/\|/g, '\\|').replace(/\r?\n/g, ' ');
}

function rowsToMarkdownTable(rows: unknown[][]): string {
  if (rows.length === 0) return '';
  const maxCols = rows.reduce((m, r) => Math.max(m, r.length), 0);
  if (maxCols === 0) return '';

  const norm = rows.map((r) => {
    const filled = [...r];
    while (filled.length < maxCols) filled.push('');
    return filled.map(escapeCell);
  });

  const [header, ...body] = norm;
  const headerLine = `| ${header.join(' | ')} |`;
  const separator = `| ${header.map(() => '---').join(' | ')} |`;
  const bodyLines = body.map((r) => `| ${r.join(' | ')} |`);
  return [headerLine, separator, ...bodyLines].join('\n');
}

export async function convertSpreadsheet(filePath: string): Promise<string> {
  const ext = extname(filePath).toLowerCase();

  if (ext === '.csv' || ext === '.tsv') {
    const raw = await readFile(filePath, 'utf8');
    const delimiter = ext === '.tsv' ? '\t' : ',';
    const rows = parseCsv(raw, { delimiter, relax_column_count: true, skip_empty_lines: true }) as unknown[][];
    const table = rowsToMarkdownTable(rows);
    return (table || '') + '\n';
  }

  const workbook = xlsxReadFile(filePath);
  const parts: string[] = [];
  const multi = workbook.SheetNames.length > 1;
  for (const name of workbook.SheetNames) {
    const sheet = workbook.Sheets[name];
    const rows = xlsxUtils.sheet_to_json<unknown[]>(sheet, { header: 1, blankrows: false, defval: '' });
    const table = rowsToMarkdownTable(rows);
    if (!table) continue;
    if (multi) parts.push(`## ${name}\n\n${table}`);
    else parts.push(table);
  }
  return parts.join('\n\n') + '\n';
}
