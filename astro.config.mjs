import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://birchove.github.io',
  base: '/UkiyoE',
  trailingSlash: 'ignore',
  markdown: {
    shikiConfig: { theme: 'rose-pine' },
  },
});