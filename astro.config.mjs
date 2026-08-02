import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://ukiyoe.top',
  base: '/',
  trailingSlash: 'ignore',
  markdown: {
    shikiConfig: { theme: 'rose-pine' },
  },
});