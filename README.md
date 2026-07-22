# 浮世微言 (UkiyoE)

> 现代民间史 · 笔记体网站 —— 为后人留一部当代之《世说新语》《笑林广记》。

记当下之人、之事、之风物与笑语;每一条目分「记事」与「微言」两部分:

- **记事**:白话,客观克制,不挟情绪;有争议则并列各方说法。
- **微言**:仿「太史公曰」,以「微言曰」领起,半白半文言,可褒贬、寓感慨。

一句话:**记事求其真,微言见其义。**

---

## 目录结构

```
浮世微言/
├── src/
│   ├── content.config.ts        # 内容集合 schema(字段校验)
│   ├── content/entries/         # ✅ 已确认、会上站的条目(Markdown),提交入库
│   │   └── _template.md.txt     #    条目模板(复制后改为 .md 使用)
│   ├── layouts/  components/    # 版面布局与组件(Header / EntryCard / Weiyan …)
│   ├── styles/global.css        # 古典风格样式
│   ├── lib/categories.ts        # 四栏定义:人物/时事/风物/笑语
│   └── pages/                   # 首页 / [category] / entries/[slug] / about
├── public/                      # 静态资源(favicon 等)
├── _drafts/                     # 🚫 本地草稿区(已 git 忽略,不入库)
├── data/                        # 🚫 爬取候选 JSON / 审核清单(已 git 忽略,不入库)
└── astro.config.mjs
```

## 本地运行

需要 Node.js ≥ 18.17(本项目在 Node 22 上验证)。

```bash
npm install
npm run dev        # 本地预览 http://localhost:4321
npm run build      # 构建静态站到 dist/
npm run preview    # 预览构建产物
```

## 内容工作流(写稿 → 审核 → 发布)

1. **写稿**:复制 `src/content/entries/_template.md.txt` 为 `<slug>.md`,
   先写在本地草稿区 `_drafts/`(已被 git 忽略,不会进仓库)。
2. **审核**:对照发布前自检清单(见 `PLAN.md` 5.2):记事是否客观、争议是否多视角、
   微言是否半白半文言、来源是否齐备。
3. **发布**:确认无误后,把条目移入 `src/content/entries/`,
   并将 frontmatter 中 `status` 设为 `published`(仅 published 会出现在网站上)。
4. **构建**:`npm run build` 后部署(见下)。

> ⚠️ 仓库里**只保留网站必备资源**。爬取返回的候选 JSON(`data/`)与
> 尚未确认的稿件(`_drafts/`)均已通过 `.gitignore` 排除,**不会**上传到 GitHub。

## 部署到 GitHub Pages(手动)

本站不使用任何自动更新流程,全程手动推送:

1. 在 `astro.config.mjs` 中填入你的仓库信息:
   ```js
   site: 'https://<用户名>.github.io',
   base: '/UkiyoE',
   ```
2. `npm run build` 生成 `dist/`。
3. 把 `dist/` 内容推送到仓库的 `gh-pages` 分支,并在仓库 Settings → Pages
   中选择该分支作为站点来源。
   (下一轮会提供一键 `npm run deploy` 脚本完成第 2、3 步。)

## 素材来源与合规

素材取自各平台热搜与公开媒体报道,经筛选(过滤花边、政治、无意义热搜)后,
由执笔者考据撰写、审核发布。引用均注来源,以备查考。详见 `PLAN.md` 与 `filter_rules.txt`。

## 许可

- 文字内容:CC BY-NC-SA 4.0(署名-非商业性使用-相同方式共享)。
- 站点代码:MIT。
