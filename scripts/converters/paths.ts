import { existsSync } from 'node:fs';
import { join } from 'node:path';

export function findAvailableOutputPath(dir: string, baseName: string): string {
  const direct = join(dir, `${baseName}.md`);
  if (!existsSync(direct)) return direct;

  for (let i = 1; i < 10_000; i++) {
    const candidate = join(dir, `${baseName}-${i}.md`);
    if (!existsSync(candidate)) return candidate;
  }
  throw new Error(`Could not find available output path under ${dir} for ${baseName}`);
}
