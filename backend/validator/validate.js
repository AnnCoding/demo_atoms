// 读 stdin HTML,用 jsdom 跑一遍 init + 模拟点击/提交,报告是否"可体验"。
// 输出 JSON: { ok, errors, interacted, stateChanged }
//   ok = 无报错 且 (无交互元素 或 至少一次交互产生了可见业务状态变化)
// 关键:stateChanged 不再被 toast/临时 DOM 元素误导,聚焦"列表/数据真实更新"。
const { JSDOM, VirtualConsole } = require("jsdom");

let html = "";
process.stdin.on("data", (c) => (html += c));
process.stdin.on("end", () => {
  const errors = [];
  let done = false;

  function finish(ok, extra) {
    if (done) return;
    done = true;
    process.stdout.write(JSON.stringify({ ok, errors, ...(extra || {}) }));
    process.exit(0);
  }

  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) =>
    errors.push(
      String((e.detail && (e.detail.stack || e.detail.message)) || e.message),
    ),
  );
  vc.on("error", (...a) => errors.push("console.error: " + a.join(" ")));

  let dom;
  try {
    dom = new JSDOM(html, {
      runScripts: "dangerously",
      url: "http://localhost/", // 真 origin → localStorage 可用
      pretendToBeVisual: true,
      virtualConsole: vc,
      beforeParse(window) {
        // stub 常见未实现 API,避免生成的代码调用时报错
        window.alert = () => {};
        window.confirm = () => true;
        window.prompt = () => "测试";
        window.print = () => {};
        // jsdom 未实现的 Element/Window 方法(stub 掉,否则校验误报)
        // 典型:element.scrollIntoView() 在浏览器正常,jsdom 未实现会抛错
        const El = window.Element && window.Element.prototype;
        if (El) {
          El.scrollIntoView = El.scrollIntoView || function () {};
          El.scrollTo = El.scrollTo || function () {};
          El.scrollBy = El.scrollBy || function () {};
        }
        window.scrollTo = window.scrollTo || function () {};
        window.scrollBy = window.scrollBy || function () {};
      },
    });
  } catch (e) {
    finish(false, { note: "JSDOM 初始化失败: " + e.message });
    return;
  }

  // 业务列表容器选择器(记账/待办/CRUD 类应用的列表/表格)
  const LIST_SEL =
    "ul, ol, table, tbody, [class*='list'], [class*='item'], [class*='transaction'], [class*='record'], [class*='task'], [class*='note'], [id*='list'], [id*='items']";

  // 列表内容指纹:每个列表容器的 (子节点数 : 文本长度)
  function listSig(doc) {
    const parts = [];
    doc.querySelectorAll(LIST_SEL).forEach((el) => {
      parts.push(el.children.length + ":" + (el.textContent || "").length);
    });
    return parts.join("|");
  }
  // localStorage 数据指纹:每个 key 的 value 长度
  function lsSig(ls) {
    const parts = [];
    for (let i = 0; i < ls.length; i++) {
      const k = ls.key(i);
      parts.push(k + ":" + (ls.getItem(k) || "").length);
    }
    return parts.sort().join("|");
  }

  setTimeout(() => {
    try {
      const { document, localStorage } = dom.window;

      // 【新增】检测：有表单/交互元素但代码中没有任何存储逻辑
      const hasForm = document.querySelectorAll('form').length > 0;
      const hasInputs = document.querySelectorAll('input:not([type=submit]):not([type=button]), textarea, select').length > 0;
      const hasStorageLogic = html.includes('localStorage') || html.includes('MarkdownStore') || html.includes('sessionStorage') || html.includes('indexedDB');
      if ((hasForm || hasInputs) && !hasStorageLogic) {
        errors.push('检测到表单/输入元素但代码中没有任何数据存储逻辑（localStorage/MarkdownStore），用户提交的数据可能无法持久化，刷新后会丢失。');
      }

      const bodyText0 = ((document.body && document.body.textContent) || "")
        .length;
      const listSig0 = listSig(document);
      const lsSig0 = lsSig(localStorage);
      let interacted = false;
      let stateChanged = false;

      // 变化判定:列表指纹变 / localStorage 数据指纹变 / 正文文本显著变(>10,排除 toast 短文本)
      // 不再用 DOM 节点数(appendChild 一个 toast 就会误判)
      const changed = () =>
        listSig(document) !== listSig0 ||
        lsSig(localStorage) !== lsSig0 ||
        Math.abs(
          ((document.body && document.body.textContent) || "").length -
            bodyText0,
        ) > 10;

      // 1) 填充并提交每个 form
      document.querySelectorAll("form").forEach((form) => {
        interacted = true;
        try {
          form.querySelectorAll("input, select, textarea").forEach((el) => {
            const tag = el.tagName.toUpperCase();
            const t = (el.type || "").toLowerCase();
            if (
              t === "submit" ||
              t === "button" ||
              t === "hidden" ||
              t === "file"
            )
              return;
            if (tag === "SELECT") {
              if (el.options.length > 1) el.selectedIndex = 1;
            } else if (t === "checkbox" || t === "radio") {
              el.checked = true;
            } else if (t === "number" || t === "range") {
              el.value = "1";
            } else if (t === "email") {
              el.value = "test@test.com";
            } else if (t === "date") {
              el.value = "2026-07-10";
            } else if (t === "color") {
              el.value = "#000000";
            } else {
              el.value = "测试";
            }
          });
          const ev = new dom.window.Event("submit", {
            bubbles: true,
            cancelable: true,
          });
          form.dispatchEvent(ev);
          if (changed()) stateChanged = true;
          // 专项检测:数据已写入 localStorage 但列表未刷新 → 典型"漏调渲染函数"bug
          const lsChangedNow = lsSig(localStorage) !== lsSig0;
          const listChangedNow = listSig(document) !== listSig0;
          if (
            lsChangedNow &&
            !listChangedNow &&
            document.querySelectorAll(LIST_SEL).length > 0
          ) {
            errors.push(
              "表单提交后数据已存入 localStorage,但页面列表/表格未刷新——提交处理函数很可能遗漏了调用渲染函数(如 renderList())。",
            );
          }
        } catch (e) {
          errors.push("表单提交出错: " + e.message);
        }
      });

      // 2) 点击 submit 按钮及其他按钮(去重,上限 15 个)
      const seen = new Set();
      let cnt = 0;
      document
        .querySelectorAll("button, [type=submit], input[type=submit]")
        .forEach((btn) => {
          if (seen.has(btn) || cnt >= 15) return;
          seen.add(btn);
          cnt += 1;
          interacted = true;
          try {
            btn.dispatchEvent(
              new dom.window.Event("click", {
                bubbles: true,
                cancelable: true,
              }),
            );
            if (changed()) stateChanged = true;
          } catch (e) {
            errors.push("点击出错: " + e.message);
          }
        });

      const ok =
        errors.length === 0 && bodyText0 > 0 && (!interacted || stateChanged);
      finish(ok, { interacted, stateChanged });
    } catch (e) {
      finish(false, { note: "交互探测失败: " + e.message });
    }
  }, 400);

  setTimeout(() => finish(false, { note: "jsdom 运行超时(可能死循环)" }), 6000);
});
