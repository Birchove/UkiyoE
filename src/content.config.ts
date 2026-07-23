import { glob } from 'astro/loaders';
import { defineCollection, z } from 'astro:content';

/**
 * 条目内容集合(content collection)。
 * 每个条目 = 一个 Markdown 文件:正文是「记事」(白话、客观),
 * 「微言」(半白半文言的评语)放在 frontmatter 的 `weiyan` 字段里,
 * 以便在页面上以独立的"笺纸/印章"样式呈现。
 *
 * 文件名即条目的 slug / id(如 zhangxuefeng.md → /entries/zhangxuefeng/)。
 */
const entries = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/entries' }),
  schema: z.object({
    /** 条目标题,可适度文言化 */
    title: z.string(),
    /** 版面分类 */
    category: z.enum(['figures', 'events', 'customs', 'humor']),
    /** 标签 */
    tags: z.array(z.string()).default([]),
    /** 事件发生时间 / 时间跨度(自由文本,如 "2023-2026") */
    event_date: z.string(),
    /** 收录(撰写)日期,YYYY-MM-DD */
    recorded_date: z.string(),
    /** 信息来源,务求可追溯 */
    sources: z
      .array(
        z.object({
          name: z.string(),
          url: z.string().optional(),
          date: z.string().optional(),
          note: z.string().optional(),
        }),
      )
      .default([]),
    /** 涉及人物 */
    figures: z.array(z.string()).default([]),
    /** 是否含争议;若为 true,记事须并列多方观点 */
    controversial: z.boolean().default(false),
    /** 稿件状态:draft / review / published。仅 published 会上站 */
    status: z.enum(['draft', 'review', 'published']).default('published'),
    /** 一句话提要,用于列表卡片 */
    summary: z.string().default(''),
    /** 执笔者(站主)笔名;由 scripts/roll-by.py 以真随机抽取并落盘,贡献稿可留空 */
    by: z.string().default(''),
    /** 微言(评语)正文,半白半文言,无需自带"微言曰"前缀 */
    weiyan: z.string(),
  }),
});

export const collections = { entries };
