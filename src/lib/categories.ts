/** 版面(栏目)定义:四栏 —— 人物 / 时事 / 风物 / 笑语 */
export const CATEGORIES = {
  figures: { label: '人物', desc: '时代人物小传,褒贬俱录,以见其人。' },
  events: { label: '时事', desc: '事件现象之记录,多方并陈,以存其真。' },
  customs: { label: '风物', desc: '风俗文化与网络奇观,以小见大,以观其变。' },
  humor: { label: '笑语', desc: '诙谐笑谈与市井段子,谑而不虐,以会其趣。' },
} as const;

export type CategoryKey = keyof typeof CATEGORIES;

export const CATEGORY_KEYS = Object.keys(CATEGORIES) as CategoryKey[];

export function categoryLabel(key: string): string {
  return (CATEGORIES as Record<string, { label: string }>)[key]?.label ?? key;
}
