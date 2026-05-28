import { readFile } from 'node:fs/promises';
import { extname } from 'node:path';
import ExcelJS from 'exceljs';
import { parse as parseCsv } from 'csv-parse/sync';

function escapeCell(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (value instanceof Date) return value.toISOString();
  if (typeof value === 'object') {
    const obj = value as { text?: string; result?: unknown; richText?: Array<{ text: string }> };
    if (obj.richText) return obj.richText.map((r) => r.text).join('');
    if (typeof obj.text === 'string') return obj.text;
    if (obj.result !== undefined) return escapeCell(obj.result);
    return String(value);
  }
  return String(value).replace(/\|/g, '\\|').replace(/\r?\n/g, ' ');
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
    const rows = parseCsv(raw, {
      delimiter,
      relax_column_count: true,
      skip_empty_lines: true,
    }) as unknown[][];
    return (rowsToMarkdownTable(rows) || '') + '\n';
  }

  const workbook = new ExcelJS.Workbook();
  if (ext === '.xls') {
    throw new Error('Legacy .xls (BIFF) is not supported by exceljs; convert to .xlsx first');
  }
  await workbook.xlsx.readFile(filePath);

  const parts: string[] = [];
  const sheets = workbook.worksheets;
  const multi = sheets.length > 1;

  for (const sheet of sheets) {
    const rows: unknown[][] = [];
    sheet.eachRow({ includeEmpty: false }, (row) => {
      const values = row.values as unknown[];
      rows.push(values.slice(1));
    });
    const table = rowsToMarkdownTable(rows);
    if (!table) continue;
    if (multi) parts.push(`## ${sheet.name}\n\n${table}`);
    else parts.push(table);
  }
  return parts.join('\n\n') + '\n';
}
