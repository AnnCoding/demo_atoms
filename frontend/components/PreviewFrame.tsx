/** 只允许完整 HTML 进入 iframe。流式半成品和模型解释文本留在缓冲区。 */
export type HtmlValidation = {
  ok: boolean;
  html: string;
  error?: string;
  kind?: "empty" | "streaming" | "incomplete" | "invalid" | "ok";
};

export function validateRenderableHtml(source: string): HtmlValidation {
  if (!source.trim())
    return { ok: false, html: "", error: "等待代码生成", kind: "empty" };

  let value = source.trim();
  const fenced = value.match(/```(?:html)?\s*([\s\S]*?)```/i);
  if (fenced) value = fenced[1].trim();

  const lower = value.toLowerCase();
  const doctypeStart = lower.indexOf("<!doctype");
  const htmlStart = lower.indexOf("<html");
  const start = doctypeStart >= 0 ? doctypeStart : htmlStart;
  const end = lower.lastIndexOf("</html>");
  if (start < 0)
    return {
      ok: false,
      html: "",
      error: "尚未生成 HTML 根节点",
      kind: "invalid",
    };
  if (end < start)
    // 有 <html 开头但缺 </html>:可能是流式生成中,也可能是已落库但被 max_tokens 截断
    // —— 组件按 slug 区分:slug 空=生成中(spinner);slug 非空=历史截断(警告)
    return {
      ok: false,
      html: "",
      error: "HTML 仍在生成，尚未闭合",
      kind: "streaming",
    };

  const html = value.slice(start, end + "</html>".length).trim();
  if (!/<body[\s>]/i.test(html) || !/<\/body>/i.test(html)) {
    return {
      ok: false,
      html: "",
      error: "HTML body 尚未完整",
      kind: "incomplete",
    };
  }
  for (const tag of ["script", "style"]) {
    const opens = html.match(new RegExp(`<${tag}[\\s>]`, "gi"))?.length || 0;
    const closes = html.match(new RegExp(`</${tag}>`, "gi"))?.length || 0;
    if (opens !== closes) {
      return {
        ok: false,
        html: "",
        error: `${tag} 标签尚未闭合`,
        kind: "incomplete",
      };
    }
  }
  return { ok: true, html, kind: "ok" };
}

function extractHtml(source: string): string {
  const result = validateRenderableHtml(source);
  return result.ok ? result.html : "";
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
  const validation = validateRenderableHtml(html);
  if (!validation.ok) {
    // 已落库作品(slug 非空)却校验失败:多半是历史截断,显示静态警告,
    // 而非误导性的"生成中" spinner(作品都生成完了不可能还在生成)。
    if (
      slug &&
      (validation.kind === "streaming" || validation.kind === "incomplete")
    ) {
      return (
        <div className="flex h-full items-center justify-center bg-amber-50 p-6 text-center">
          <div>
            <div className="mx-auto mb-3 text-2xl">⚠️</div>
            <div className="text-sm font-medium text-amber-700">
              作品代码不完整
            </div>
            <div className="mt-1 text-xs text-amber-600">
              该作品可能因长度超限被截断({validation.error}
              )。可重新生成或在对话区要求修复。
            </div>
          </div>
        </div>
      );
    }
    return (
      <div className="flex h-full items-center justify-center bg-slate-50 p-6 text-center">
        <div>
          <div className="mx-auto mb-3 h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-blue-500" />
          <div className="text-sm font-medium text-slate-600">预览校验中</div>
          <div className="mt-1 text-xs text-slate-400">{validation.error}</div>
        </div>
      </div>
    );
  }
  return (
    <iframe
      srcDoc={injectEnv(validation.html, slug, apiBase)}
      // allow-same-origin:让生成物的 localStorage 可用 + fetch 后端 API 不被拦。
      sandbox="allow-scripts allow-same-origin"
      className="w-full h-full border-0 bg-white"
      title="preview"
    />
  );
}
