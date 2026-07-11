/** sandbox iframe 渲染生成物。剥离可能的 ```html 包裹;注入 PROJECT_SLUG/API_BASE 供存储 skill 读写后端 database.md。 */
function extractHtml(s: string): string {
  if (!s) return "";

  // 1. 尝试提取 ```html ... ``` 代码块
  const m = s.match(/```(?:html)?\s*([\s\S]*?)```/);
  if (m) return m[1].trim();

  // 2. 尝试提取 <html>...</html> 片段（即使前后有多余文本）
  const htmlBlock = s.match(
    /(<!doctype[\s\S]*?<\/html>|<html[\s\S]*?<\/html>)/i,
  );
  if (htmlBlock) return htmlBlock[1].trim();

  // 3. 如果整体以 <!doctype 或 <html 开头，直接使用
  const t = s.trim();
  if (/^<!doctype|^<html/i.test(t)) return t;

  // 4. 包含 <body> 标签的片段，包裹成完整 HTML
  if (/<body[\s>]/i.test(t)) {
    return `<!DOCTYPE html><html><head><meta charset="utf-8"></head>${t}</html>`;
  }

  // 5. 包含块级 HTML 元素（div/section/main/header 等），包裹为 body
  if (
    /<(div|section|main|header|footer|nav|article|form|table)[\s>]/i.test(t)
  ) {
    return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{font-family:system-ui,-apple-system,sans-serif;margin:0;padding:16px;color:#1a1a1a;}</style></head><body>${t}</body></html>`;
  }

  // 6. 纯文本/markdown 兜底：美化显示
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{font-family:system-ui,-apple-system,sans-serif;margin:0;padding:24px;color:#374151;line-height:1.6;background:#fafafa;}pre{white-space:pre-wrap;word-break:break-word;}</style></head><body><pre>${t.replace(/[<>&]/g, (c) => (c === "<" ? "&lt;" : c === ">" ? "&gt;" : "&amp;"))}</pre></body></html>`;
}

/** 视觉设计基线：当生成的 HTML 缺少自定义样式时，注入现代化 CSS 基线 */
const DESIGN_BASELINE = `<style data-baseline="true">
/* 仅在页面无自定义 style/link[stylesheet] 时生效 */
:root{--primary:#2563eb;--primary-hover:#1d4ed8;--bg:#ffffff;--surface:#f8fafc;--border:#e2e8f0;--text:#1e293b;--text-muted:#64748b;--radius:8px;--shadow:0 1px 3px rgba(0,0,0,.08),0 1px 2px rgba(0,0,0,.04);}
*{box-sizing:border-box;}
body{font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;margin:0;padding:0;color:var(--text);background:var(--bg);line-height:1.6;-webkit-font-smoothing:antialiased;}
h1,h2,h3,h4{margin:0 0 .5em;font-weight:600;line-height:1.3;}
h1{font-size:1.875rem;}h2{font-size:1.5rem;}h3{font-size:1.25rem;}
button,input,select,textarea{font:inherit;border-radius:var(--radius);}
button{cursor:pointer;border:none;padding:.5rem 1rem;background:var(--primary);color:#fff;font-weight:500;transition:background .15s;}
button:hover{background:var(--primary-hover);}
input,textarea,select{border:1px solid var(--border);padding:.5rem .75rem;outline:none;transition:border-color .15s;}
input:focus,textarea:focus,select:focus{border-color:var(--primary);box-shadow:0 0 0 3px rgba(37,99,235,.1);}
a{color:var(--primary);text-decoration:none;}a:hover{text-decoration:underline;}
table{border-collapse:collapse;width:100%;}
th,td{padding:.5rem .75rem;border:1px solid var(--border);text-align:left;}
th{background:var(--surface);font-weight:600;}
.card{background:var(--bg);border:1px solid var(--border);border-radius:var(--radius);padding:1.25rem;box-shadow:var(--shadow);}
</style>`;

/** 判断 HTML 是否已有自定义样式 */
function hasCustomStyles(html: string): boolean {
  return /<style[\s>]/i.test(html) || /<link[^>]+stylesheet/i.test(html);
}

/** 注入运行时环境变量到 HTML,让生成物里的 MarkdownStore 能读写后端 database.md。
 * 有 slug → 后端 API 模式(真文件持久);无 slug(生成中预览)→ MarkdownStore 自动降级 localStorage。
 * 同时在缺少自定义样式时注入视觉设计基线。 */
function injectEnv(html: string, slug: string, apiBase: string): string {
  const script = `<script>window.PROJECT_SLUG=${JSON.stringify(slug)};window.API_BASE=${JSON.stringify(apiBase)};</script>`;
  const h = extractHtml(html);
  // 如果 HTML 没有自定义样式，注入设计基线
  const baseline = hasCustomStyles(h) ? "" : DESIGN_BASELINE;
  const injection = baseline + script;
  if (/<head[^>]*>/i.test(h))
    return h.replace(/<head[^>]*>/i, (m) => m + injection);
  if (/<html[^>]*>/i.test(h))
    return h.replace(/<html[^>]*>/i, (m) => m + injection);
  return injection + h;
}

export default function PreviewFrame({
  html,
  slug = "",
}: {
  html: string;
  slug?: string;
}) {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8010";
  return (
    <iframe
      srcDoc={injectEnv(html, slug, apiBase)}
      // allow-same-origin:让生成物的 localStorage 可用 + fetch 后端 API 不被拦。
      sandbox="allow-scripts allow-same-origin"
      className="w-full h-full border-0 bg-white"
      title="preview"
    />
  );
}
