// URL slugs for university/department public pages. Names come from the
// backend; slugs must be stable and reversible by re-slugifying candidates.
export function slugify(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}
