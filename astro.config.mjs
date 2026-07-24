import { defineConfig } from 'astro/config';

// 部署到 GitHub Pages 项目站点时(例如 https://<用户名>.github.io/UkiyoE/),
// 请取消下面两行的注释并填入你的仓库信息,否则资源路径会不对:
//   site: 'https://<用户名>.github.io',
//   base: '/UkiyoE',
export default defineConfig({
  site: 'https://<用户名>.github.io',
  base: '/UkiyoE',
  trailingSlash: 'ignore',
  markdown: {
    shikiConfig: { theme: 'rose-pine' },
  },
});
