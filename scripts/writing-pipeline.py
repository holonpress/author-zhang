#!/usr/bin/env python3
"""
writing-pipeline.py — 强制分阶段写作管线

用法：
  python3 scripts/writing-pipeline.py --brief "任务描述" --materials "搜索资料" [--model "deepseek/deepseek-v4-pro"]

流程：
  Phase 0: 加载 identity + harness 文件 → 理解人设
  Phase 1: 理解任务 + 调研材料
  Phase 2: 生成结构化 Plan（核心判断 + 段落结构）
  Phase 3: 逐段写作（每段一次调用，强制 M1-M6 弧线）
  Phase 4: 质量审查（逐条跑 quality-review.md）
  Phase 5: 若审查不通过 → 修改 → 重新审查（最多 2 轮）
  Phase 6: 拼装 Jekyll post + git commit + git push
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL = "deepseek/deepseek-v4-pro"

# ── API 调用（OpenClaw 的 openai-http-api 兼容）──

def call_model(prompt, system_prompt="", model=DEFAULT_MODEL):
    """通过 OpenClaw 的 OpenAI-compatible API 调用模型。
    回退：直接使用 exec curl 到 openclaw gateway。
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # 尝试通过 curl 调用 OpenClaw gateway API
    cmd = [
        "curl", "-s",
        "-X", "POST",
        "http://127.0.0.1:18789/v1/chat/completions",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
        })
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[WARN] API call failed: {e}", file=sys.stderr)

    # 如果 OpenClaw gateway 不可用，尝试直接调用 DeepSeek API
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
        except Exception as e:
            print(f"[WARN] Direct API call failed: {e}", file=sys.stderr)

    return None


def read_file(path):
    """读取 repo 内的文件"""
    full_path = os.path.join(REPO_ROOT, path)
    if os.path.exists(full_path):
        with open(full_path, "r") as f:
            return f.read()
    return f"[FILE NOT FOUND: {path}]"


def make_slug(title):
    """从中文标题生成英文 slug"""
    import re
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


# ── Phase 0: 加载 identity + harness ──

def phase_0_load_identity():
    print("\n=== Phase 0: 加载身份与写作 Harness ===")

    files = {
        "persona": "identity/persona.md",
        "methodology": "identity/methodology.md",
        "voice": "identity/voice.md",
        "skill": "skills/horse-style-writer/SKILL.md",
        "writing_guide": "skills/horse-style-writer/writing-guide.md",
        "quality_review": "skills/horse-style-writer/quality-review.md",
    }

    identity_text = ""
    for name, path in files.items():
        content = read_file(path)
        identity_text += f"\n--- {name} ---\n{content}\n"
        print(f"  ✓ {name} ({path})")

    return identity_text


# ── Phase 1: 理解任务 ──

def phase_1_understand(brief, materials, identity_text):
    print("\n=== Phase 1: 理解任务 + 调研材料 ===")

    prompt = f"""你是张三，一个持续的公共写作者。

以下是你的人设、写作方法论和文风指导：

{identity_text}

## 写作任务

{brief}

## 调研材料

{materials}

## 你的任务

请阅读以上材料，确认：
1. 选题的核心角度
2. 目标字数（短篇1000-2000 / 中篇2000-5000 / 长文5000+）
3. 情绪基调
4. 关键事实要点（交叉验证）

用 200 字以内回答。"""
    return call_model(prompt)


# ── Phase 2: 生成 Plan ──

def phase_2_plan(brief, materials, understanding):
    print("\n=== Phase 2: 生成写作 Plan ===")

    prompt = f"""你是张三。基于以上理解，请输出一个结构化写作计划（JSON 格式）：

{{
  "core_judgment": "一句话核心判断",
  "structure": [
    {{"paragraph": 1, "type": "trigger", "content": "以什么具体触发物开头"}},
    {{"paragraph": 2, "type": "judgment", "content": "犹疑但明确的初步判断"}},
    {{"paragraph": 3, "type": "reverse_frame", "content": "拒绝什么表面解释，提出什么反框架"}},
    {{"paragraph": 4, "type": "context", "content": "放入什么历史/结构/机制语境"}},
    {{"paragraph": 5, "type": "return_to_people", "content": "回到什么具体的人"}},
    {{"paragraph": 6, "type": "aftertaste", "content": "以什么方式留下余味结尾"}}
  ],
  "word_count_target": "中篇（3000-5000字）",
  "m1_m6_check": {{
    "m1_trigger": true,
    "m2_judgment": true,
    "m3_reverse_frame": true,
    "m4_context": true,
    "m5_return_people": true,
    "m6_aftertaste": true
  }}
}}

只输出 JSON，不要其他文字。"""
    return call_model(prompt)


# ── Phase 3: 逐段写作 ──

def phase_3_write(brief, materials, plan_json, identity_text):
    print("\n=== Phase 3: 逐段写作 ===")

    # 解析 plan
    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError:
        print("[ERROR] Plan 不是有效 JSON，将使用平面写作")
        plan = {"structure": [{"paragraph": 1, "type": "full_article", "content": "整篇文章"}]}

    # 读取精选示例作为格式参考
    examples = read_file("skills/horse-style-writer/references/examples/结构化推理.md")
    examples += "\n\n"
    examples += read_file("skills/horse-style-writer/references/examples/生活记录.md")

    system = f"""你是张三。以下是你的写作人设和文风指导：

{identity_text}

你严格按照 horse 文风写作：
- 文风公式：具体触发 → 犹疑判断 → 反框架 → 结构语境 → 回到人 → 不封闭的余味
- 从具体场景开始，不从观点开始
- 带着 `我觉得` `大概` `可能` 的犹疑，但必须有真判断
- 拒绝表面解释，推动反框架
- 放入历史/结构语境
- 回到具体的人
- 结尾留余味

格式参考示例：
{examples[:1500]}
"""

    paragraphs = []
    for para in plan.get("structure", [plan]):
        p_type = para.get("type", "unknown")
        p_content = para.get("content", "")
        p_num = para.get("paragraph", 1)

        print(f"  写作第 {p_num} 段 ({p_type})...")

        # 把之前写好的段落作为上下文
        context = "\n\n".join(paragraphs[-2:]) if paragraphs else "（这是第一段）"

        prompt = f"""选题角度：{brief}
素材：{materials[:2000]}

计划：第 {p_num} 段 — {p_type}: {p_content}

已写好的上文：
{context}

请按计划写第 {p_num} 段（{p_type}）：
- {p_content}
- 保持 horse 文风：具体、犹疑、反框架、语境化、回人、余味
- 写 300-800 字
- 注意：`不是A而是B` 句型整篇限 1-3 次"""
        result = call_model(prompt, system_prompt=system)
        if result:
            paragraphs.append(result)
        else:
            paragraphs.append(f"[第 {p_num} 段生成失败]")

    return "\n\n".join(paragraphs)


# ── Phase 4: 质量审查 ──

def phase_4_review(full_article):
    print("\n=== Phase 4: 质量审查 (M1-M6) ===")

    quality_review = read_file("skills/horse-style-writer/quality-review.md")

    prompt = f"""你是一个严格的文风审查员。请按以下审查表逐条检查这篇文章：

{quality_review}

## 文章正文

{full_article}

## 审查要求

逐条评分 M1-M6，每条标记 Yes/No/Partial：
- M1 触发物：文章是否从具体场景开始？
- M2 真判断：是否有自己的明确判断？
- M3 反框架：是否拒绝了表面解释？
- M4 语境化：是否放入了历史/结构语境？
- M5 回到人：是否回到了具体的人？
- M6 余味：结尾是否不封死？

同时检查：
- R1-R4 修辞频率
- B1-B4 边界违规

最后给出：通过/不通过。不通过时列出具体问题。"""
    return call_model(prompt)


# ── Phase 4b: 修改（如不通过）──

def phase_4b_revise(full_article, review_result, max_rounds=2):
    round_count = 0
    while round_count < max_rounds:
        if "不通过" in review_result or "No" in review_result.split("\n")[0]:
            round_count += 1
            print(f"\n=== Phase 4b: 第 {round_count} 轮修改 ===")
            prompt = f"""审查结果指出以下问题：

{review_result}

原文：

{full_article}

请按审查意见修改。保持文章整体结构和长度。"""
            revised = call_model(prompt)
            if revised:
                full_article = revised
            review_result = phase_4_review(full_article)
            if "不通过" not in review_result and "No" not in review_result:
                print("  ✅ 审查通过")
                break
        else:
            print("  ✅ 审查通过")
            break
    return full_article, review_result


# ── Phase 5: 发布 ──

def phase_5_publish(full_article, title, sources):
    print("\n=== Phase 5: 发布 ===")

    today = datetime.now()
    slug = make_slug(title)
    date_str = today.strftime("%Y-%m-%d")
    datetime_str = today.strftime("%Y-%m-%d %H:%M:%S +0900")

    # 拼装 Jekyll front matter + body
    post = f"""---
layout: post
title: "{title}"
date: {datetime_str}
categories: [国际, 人道, 随笔]
tags: [随笔]
authors: [张三]
---

{full_article}

---

**主要信息来源 / Sources：**

{sources}
"""
    filename = f"{date_str}-{slug}.md"
    filepath = os.path.join(REPO_ROOT, "_posts", filename)

    with open(filepath, "w") as f:
        f.write(post)
    print(f"  ✓ 写入 _posts/{filename}")

    # git commit + push
    try:
        subprocess.run(["git", "add", "_posts/"], cwd=REPO_ROOT, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"article: {title}"], cwd=REPO_ROOT, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True, capture_output=True)
        print(f"  ✓ git commit + push 完成")
    except subprocess.CalledProcessError as e:
        print(f"  [WARN] git push 失败: {e.stderr.decode() if e.stderr else 'unknown'}")

    return filename


# ── 主流程 ──

def main():
    parser = argparse.ArgumentParser(description="张三写作管线")
    parser.add_argument("--brief", required=True, help="任务描述（选题 + 角度 + 字数）")
    parser.add_argument("--materials", required=True, help="搜索资料/素材")
    parser.add_argument("--title", default="", help="文章标题（可选，默认从 Plan 生成）")
    parser.add_argument("--sources", default="", help="来源列表（多行，每行一条超链接+说明）")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"模型（默认 {DEFAULT_MODEL}）")
    args = parser.parse_args()

    print(f"✏️  张三写作管线启动")
    print(f"   模型: {args.model}")
    print(f"   任务: {args.brief[:80]}...")

    # Phase 0
    identity = phase_0_load_identity()

    # Phase 1
    understanding = phase_1_understand(args.brief, args.materials, identity)
    print(f"  理解结果: {understanding[:200] if understanding else 'FAILED'}...")
    if not understanding:
        print("[ERROR] Phase 1 失败，终止")
        sys.exit(1)

    # Phase 2
    plan = phase_2_plan(args.brief, args.materials, understanding)
    print(f"  Plan: {plan[:300] if plan else 'FAILED'}...")
    if not plan:
        print("[ERROR] Phase 2 失败，终止")
        sys.exit(1)

    # Phase 3
    article = phase_3_write(args.brief, args.materials, plan, identity)
    if not article or len(article) < 500:
        print("[ERROR] Phase 3 产出过短，终止")
        sys.exit(1)
    print(f"  ✅ 全文 {len(article)} 字")

    # Phase 4
    review = phase_4_review(article)
    print(f"  审查结果: {review[:300] if review else 'FAILED'}")

    # Phase 4b (如果审查不通过)
    if review:
        article, review = phase_4b_revise(article, review)
    else:
        print("[WARN] 审查未完成，直接发布")

    # Phase 5
    title = args.title or "未命名文章"
    filename = phase_5_publish(article, title, args.sources)
    print(f"\n✅ 完成！已发布到 _posts/{filename}")
    print(f"   等待 GitHub Actions 部署…")

    # 更新 memory/self.md
    memory_entry = f"""
### {datetime.now().strftime('%Y-%m-%d')}：{title}

- **主题**：{args.brief[:100]}
- **字数**：约{len(article)}字
- **审校要点**：M1-M6 审查{'通过' if review and '不通过' not in review else '有修改'}
- **状态**：已发布并推送（via pipeline）
"""
    memory_path = os.path.join(REPO_ROOT, "memory", "self.md")
    with open(memory_path, "a") as f:
        f.write(memory_entry)
    subprocess.run(["git", "add", "memory/self.md"], cwd=REPO_ROOT, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"chore: update memory for {title}"], cwd=REPO_ROOT, capture_output=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, capture_output=True)


if __name__ == "__main__":
    main()
