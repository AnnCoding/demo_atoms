#!/usr/bin/env bash
# logs.sh — Atoms Demo 日志查看工具
# 用法: ./logs.sh [命令]   (默认 f 实时跟踪后端)

# ---- 定位日志(基于脚本所在目录,从任意位置运行都行)----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_LOG="$SCRIPT_DIR/backend/logs/backend.log"
FRONTEND_LOG="$SCRIPT_DIR/backend/logs/frontend.log"

# ---- 颜色 ($'...' 让 bash 把 \033 解释成真正的 ESC 字符)----
R=$'\033[0;31m'    # 红 = ERROR
Y=$'\033[0;33m'    # 黄 = WARNING
G=$'\033[0;32m'    # 绿 = 提示
B=$'\033[0;36m'    # 青 = 标题
D=$'\033[0;90m'    # 灰 = 次要
N=$'\033[0m'       # reset

# ---- 帮助 ----
usage() {
  cat <<EOF
${G}═════════════ Atoms Demo 日志查看工具 ═════════════${N}

${B}用法:${N} ./logs.sh [命令]

${B}实时跟踪 (默认 f):${N}
  ${G}f${N}, ${G}follow${N}        实时跟踪后端日志 ${D}(默认)${N}
  ${G}front${N}          实时跟踪前端日志
  ${G}all${N}            同时跟踪前后端日志

${B}过滤查看:${N}
  ${G}err${N}            只看 ERROR / WARNING
  ${G}agent${N}, ${G}orch${N}     只看 Agent 执行流转 ${D}(Mike/Emma/Bob/Alex)${N}
  ${G}llm${N}            只看 LLM 调用 ${D}(智谱AI 请求/状态码)${N}
  ${G}skill${N}          只看 Skill 匹配/激活
  ${G}session${N} <id>   按 session id 过滤 ${D}(id 可只写前8位)${N}

${B}其他:${N}
  ${G}tail${N} [n]       最近 n 行 ${D}(默认 50)${N}
  ${G}clear${N}          清空所有日志
  ${G}help${N}           显示此帮助

${B}示例:${N}
  ${D}./logs.sh                       # 实时看后端${N}
  ${D}./logs.sh err                   # 实时只看错误${N}
  ${D}./logs.sh session 2c7fb158      # 跟踪某个会话${N}
  ${D}./logs.sh tail 100              # 最近 100 行${N}

${B}快捷键:${N} ${G}Ctrl+C${N} 退出实时跟踪
${G}═════════════════════════════════════════════════${N}
EOF
}

# ---- 着色输出:全部行都显示,但高亮关键词 ----
# 技巧: pattern|$ 让没匹配的行也通过($恒匹配),实现"全显示+局部高亮"
colorize() {
  grep --color=always -E "ERROR.*|WARNING.*|$" 2>/dev/null \
    || cat
}

# ---- 实时跟踪(带高亮)----
follow_backend() {
  [ -f "$BACKEND_LOG" ] || { echo -e "${R}✗ 后端日志不存在:${BACKEND_LOG}${N}"; exit 1; }
  echo -e "${D}实时跟踪后端日志 (Ctrl+C 退出)...${N}\n"
  tail -fF "$BACKEND_LOG" | colorize
}

follow_front() {
  [ -f "$FRONTEND_LOG" ] || { echo -e "${R}✗ 前端日志不存在:${FRONTEND_LOG}${N}"; exit 1; }
  echo -e "${D}实时跟踪前端日志 (Ctrl+C 退出)...${N}\n"
  tail -fF "$FRONTEND_LOG"
}

follow_all() {
  for f in "$BACKEND_LOG" "$FRONTEND_LOG"; do
    [ -f "$f" ] || { echo -e "${R}✗ 日志不存在:${f}${N}"; exit 1; }
  done
  echo -e "${D}同时跟踪前后端日志 (Ctrl+C 退出)...${N}\n"
  # 前缀标记来源 [BE]/[FE]
  tail -fF "$BACKEND_LOG" | sed "s/^/${D}[BE]${N} /" &
  tail -fF "$FRONTEND_LOG" | sed "s/^/${D}[FE]${N} /"
}

# ---- 按关键词过滤(实时)----
follow_grep() {
  local pattern="$1" label="$2"
  [ -f "$BACKEND_LOG" ] || { echo -e "${R}✗ 后端日志不存在${N}"; exit 1; }
  echo -e "${D}实时跟踪 [${label}] (Ctrl+C 退出)...${N}\n"
  tail -fF "$BACKEND_LOG" | grep --color=always -E "${pattern}" \
    || echo -e "${Y}(暂无匹配)${N}"
}

# ---- 清空日志 ----
clear_logs() {
  for f in "$BACKEND_LOG" "$FRONTEND_LOG"; do
    if [ -f "$f" ]; then
      : > "$f"
      echo -e "${G}✓ 已清空 ${f}${N}"
    fi
  done
}

# ---- 主分发 ----
case "${1:-f}" in
  f|follow)       follow_backend ;;
  front|f-log)    follow_front ;;
  all)            follow_all ;;
  err)            follow_grep "ERROR|WARNING" "ERROR/WARNING" ;;
  agent|orch)     follow_grep "atoms\.orch|→" "Agent 流转" ;;
  llm)            follow_grep "httpx|HTTP|atoms\.llm" "LLM 调用" ;;
  skill)          follow_grep "atoms\.skills" "Skill" ;;
  session)
    [ -z "${2:-}" ] && { echo -e "${R}✗ 请提供 session id${N}"; echo "  例: ./logs.sh session 2c7fb158"; exit 1; }
    follow_grep "${2}" "session ${2}" ;;
  tail)
    n="${2:-50}"
    [ -f "$BACKEND_LOG" ] || { echo -e "${R}✗ 后端日志不存在${N}"; exit 1; }
    echo -e "${D}后端最近 ${n} 行:${N}\n"
    tail -n "$n" "$BACKEND_LOG" | colorize ;;
  clear)          clear_logs ;;
  help|-h|--help) usage ;;
  *)              echo -e "${R}✗ 未知命令: ${1}${N}\n"; usage; exit 1 ;;
esac