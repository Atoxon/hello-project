import TurndownService from 'turndown';
import { gfm } from 'turndown-plugin-gfm';

export function createTurndown(): TurndownService {
  const td = new TurndownService({
    headingStyle: 'atx',
    codeBlockStyle: 'fenced',
    bulletListMarker: '-',
    emDelimiter: '*',
  });
  td.use(gfm);
  return td;
}

export function htmlToMarkdown(html: string): string {
  return createTurndown().turndown(html).trim() + '\n';
}
