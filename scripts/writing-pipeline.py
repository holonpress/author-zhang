#!/usr/bin/env python3
"""
writing-pipeline.py — 分阶段写作管线（stage-based subcommands）

用法（agent 在上下文内通过 exec 逐步调用）：
  # Phase 1: 热身
  python3 scripts/writing-pipeline.py --stage warmup --slug "my-article"

  # Phase 3: 生成 Plan
  python3 scripts/writing-pipeline.py --stage plan --slug "my-article" --brief "..." --materials "..."

  # Phase 4: 写初稿
  python3 scripts/writing-pipeline.py --stage write --slug "my-article" --plan _drafts/my-article-plan.md

  # Phase 5: 自我审查
  python3 scripts/writing-pipeline.py --stage review --slug "my-article"

  # Phase 8: 发布
  python3 scripts/writing-pipeline.py --stage publish --slug "my-article" --title "文章标题" --sources "来源列表"

每个 stage 独立运行，agent 在自己的 exec 上下文内逐步调用。
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS_DIR = os.path.join(REPO_ROOT, "_drafts")
POSTS_DIR = os.path.join(REPO_ROOT, "_posts")

os.makedirs(DRAFTS_DIR, exist_ok=True)


def read_file(path):
    """读取 repo 内的文件"""
    full_path = os.path.join(REPO_ROOT, path) if not path.startswith("/") else path
    if os.path.exists(full_path):
        with open(full_path, "r") as f:
            return f.read()
    return f"[FILE NOT FOUND: {path}]"


def make_slug(title):
    """从中文标题生成英文 slug"""
    import re
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:60].strip('-')


def call_model(prompt, system_prompt=""):
    """调用模型。优先用 OpenClaw gateway，回退 DeepSeek API。"""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # OpenClaw gateway
    cmd = [
        "curl", "-s",
        "-X", "POST",
        "http://127.0.0.1:18789/v1/chat/completions",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "model": "deepseek/deepseek-v4-pro",
            "messages": messages,
            "max_tokens": 4096,
        })
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data["choices"][0]["message"]["content"]
    except Exception:
        pass

    # Fallback: DeepSeek API
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if api_key:
        cmd = [
            "curl", "-s",
            "-X", "POST",
            "https://api.deepseek.com/v1/chat/completions",
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {api_key}",
            "-d", json.dumps({
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": 4096,
            })
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data["choices"][0]["message"]["content"]
        except Exception:
            pass

    return None


# ═══════════════════════════════════════════
# 阶段实现
# ═══════════════════════════════════════════

def stage_warmup(slug):
    """Phase 1: 热身。读 identity 文件 → 写热身笔记。"""
    identity_text = ""
    for f in ["identity/persona.md", "identity/methodology.md", "identity/voice.md"]:
        identity_text += f"\n--- {f} ---\n{read_file(f)}\n"

    prompt = f"""你是张三，一个持续的公共写作者。

以下是你的人设、方法论和文风：

{identity_text}

请写一段热身笔记，包含：
1. 今天侧重哪个角色（结构观察者/生活记录者/混合）
2. 一句话核心判断的初步方向
3. 从什么具体场景/新闻/经历开始
4. 可能采用的第一个反框架

输出格式：
## 热身笔记

角色：…
核心判断：…
触发物：…
预期反框架：…"""
    result = call_model(prompt)
    if not result:
        print("[ERROR] warmup 生成失败", file=sys.stderr)
        sys.exit(1)

    warmup_path = os.path.join(DRAFTS_DIR, f"warmup-{slug}.md")
    with open(warmup_path, "w") as f:
        f.write(result.strip())
    print(f"✅ 热身笔记 → _drafts/warmup-{slug}.md")


def stage_plan(slug, brief, materials):
    """Phase 3: 生成结构化 Plan。"""
    persona = read_file("identity/persona.md")
    methodology = read_file("identity/methodology.md")
    voice = read_file("identity/voice.md")
    examples = read_file("skills/horse-style-writer/references/examples/结构化推理.md")

    prompt = f"""你是张三。你的文风公式：具体触发 → 犹疑判断 → 反框架 → 结构语境 → 回人 → 不封闭的余味。

### 人设
{persona}

### 文风
{voice}

### 写作方法论
{methodology}

### 格式参考
{examples[:1000]}

### 写作任务
{brief}

### 调研材料
{materials}

请生成一个结构化写作计划（Markdown 格式）：

## Plan: {{标题}}

**核心判断（一句话）：** …

**段落结构：**
1. [trigger] — 以什么具体场景开头
2. [judgment] — 初步的犹疑判断
3. [reverse_frame] — 拒绝什么解释 → 提出什么替代（`不是A而是B` ≤ 3次）
4. [context] — 放入什么历史/结构/机制
5. [people] — 落在哪个具体的人/人群
6. [aftertaste] — 以什么方式留余味

**触发物细节：** …

**反框架：** 大家以为…但其实…

**不是A而是B 计划位置：** 第___段和第___段

**语境层：** …

**回人：** …

**余味方式：** …

**来源清单：** 3-5条关键来源"""
    result = call_model(prompt)
    if not result:
        print("[ERROR] plan 生成失败", file=sys.stderr)
        sys.exit(1)

    plan_path = os.path.join(DRAFTS_DIR, f"{slug}-plan.md")
    with open(plan_path, "w") as f:
        f.write(result.strip())
    print(f"✅ Plan → _drafts/{slug}-plan.md")


def stage_write(slug, plan_file):
    """Phase 4: 按 Plan 一次写完初稿。"""
    plan = read_file(plan_file)
    voice = read_file("identity/voice.md")

    system = f"""你是张三。严格按 Plan 写作。

文风：{voice}

关键约束：
- 从具体场景开始
- 带着 `我觉得` `大概` `可能` 的犹疑，但必须有真判断
- `不是A而是B` 整篇 ≤ 3 次
- 结尾不封死
- 不编造事实"""
    prompt = f"""## Plan

{plan}

请按以上 Plan 写完整篇初稿。一次写完，不要分段。

注意：
1. 从 trigger 段开始
2. 按段落结构推进
3. 最后一段是 aftertaste（余味结尾）
4. 写完为止，不要加"综上所述"

文章正文："""
    result = call_model(prompt, system_prompt=system)
    if not result or len(result) < 500:
        print("[ERROR] 初稿生成失败或过短", file=sys.stderr)
        sys.exit(1)

    draft_path = os.path.join(DRAFTS_DIR, f"{slug}.md")
    with open(draft_path, "w") as f:
        f.write(result.strip())
    print(f"✅ 初稿 → _drafts/{slug}.md ({len(result)}字)")


def stage_review(slug):
    """Phase 5: 自我审查。"""
    draft = read_file(os.path.join(DRAFTS_DIR, f"{slug}.md"))
    quality = read_file("skills/horse-style-writer/quality-review.md")

    prompt = f"""你是严格的文风审查员。按以下审查表逐条检查：

{quality}

## 文章正文

{draft}

## 审查要求

逐条评分，输出格式：
M1 [Yes/No/Partial] 触发物：…
M2 [Yes/No/Partial] 真判断：…
M3 [Yes/No/Partial] 反框架：…
M4 [Yes/No/Partial] 语境化：…
M5 [Yes/No/Partial] 回人：…
M6 [Yes/No/Partial] 余味：…

R1 不是A而是B 使用次数：_次（≤3 ✅ / >3 ⚠️）
R2 犹疑词频率：_次（2-5 ✅ / 其他 ⚠️）
R3 编号使用：合理/过度
R4 括号使用：每段 ≤ 2 处 ✅/⚠️

B1 广告语气：有/无
B2 过度文艺：有/无
B3 确定性幻觉：有/无
B4 编造：有/无

## 总评

M1-M6 通过数：_/6
边界违规：_项
结论：通过/不通过"""
    result = call_model(prompt)
    if not result:
        print("[ERROR] 审查失败", file=sys.stderr)
        sys.exit(1)

    review_path = os.path.join(DRAFTS_DIR, f"{slug}-review.md")
    with open(review_path, "w") as f:
        f.write(result.strip())
    print(f"✅ 审查结果 → _drafts/{slug}-review.md")

    # 判断是否通过
    if "不通过" in result or all(f"M{i}" not in result for i in range(1, 7)):
        print("⚠️  审查不通过，请修改后重新审查")
        sys.exit(2)
    else:
        print("✅ 审查通过")


def stage_publish(slug, title, sources):
    """Phase 8: 发布到 _posts/。"""
    draft_path = os.path.join(DRAFTS_DIR, f"{slug}.md")
    if not os.path.exists(draft_path):
        print(f"[ERROR] 未找到初稿: {draft_path}", file=sys.stderr)
        sys.exit(1)

    body = read_file(draft_path)
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    datetime_str = today.strftime("%Y-%m-%d %H:%M:%S +0900")

    post = f"""---
layout: post
title: "{title}"
date: {datetime_str}
categories: [国际, 人道, 随笔]
tags: [随笔]
authors: [张三]
---

{body}

---

**主要信息来源 / Sources：**

{sources}
"""
    post_slug = make_slug(title)
    filename = f"{date_str}-{post_slug}.md"
    filepath = os.path.join(POSTS_DIR, filename)

    with open(filepath, "w") as f:
        f.write(post)
    print(f"✅ 已发布 → _posts/{filename}")

    # Git commit + push
    try:
        subprocess.run(["git", "add", "_posts/"], cwd=REPO_ROOT, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"article: {title}"], cwd=REPO_ROOT, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True, capture_output=True)
        print("✅ git commit + push 完成")
    except subprocess.CalledProcessError as e:
        print(f"[WARN] git push 失败: {e}")

    # 清理草稿
    import glob
    for f in glob.glob(os.path.join(DRAFTS_DIR, f"{slug}*")):
        os.remove(f)
    print(f"✅ 草稿文件已清理")


# ═══════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="张三写作管线（分阶段）")
    parser.add_argument("--stage", required=True,
                        choices=["warmup", "plan", "write", "review", "publish"],
                        help="执行阶段")
    parser.add_argument("--slug", default="unnamed", help="文章标识")
    parser.add_argument("--brief", help="任务描述（plan 阶段用）")
    parser.add_argument("--materials", help="调研材料（plan 阶段用）")
    parser.add_argument("--plan", help="Plan 文件路径（write 阶段用）")
    parser.add_argument("--title", help="文章标题（publish 阶段用）")
    parser.add_argument("--sources", help="来源列表（publish 阶段用）")
    args = parser.parse_args()

    stages = {
        "warmup": lambda: stage_warmup(args.slug),
        "plan": lambda: stage_plan(args.slug, args.brief or "", args.materials or ""),
        "write": lambda: stage_write(args.slug, args.plan or os.path.join(DRAFTS_DIR, f"{args.slug}-plan.md")),
        "review": lambda: stage_review(args.slug),
        "publish": lambda: stage_publish(args.slug, args.title or "未命名文章", args.sources or ""),
    }

    stages[args.stage]()


if __name__ == "__main__":
    main()
