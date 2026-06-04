"""
知识库索引自动生成器
用途: 扫描 Knowledge/ 下所有 .md 文件，自动生成/更新 index.md 和 AI_MANIFEST.md
用法:
  python knowledge_index_generator.py          # 生成索引
  python knowledge_index_generator.py --dry-run # 仅打印，不写文件
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# === 配置（自动检测路径，无需硬编码） ===
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "Knowledge"
INDEX_PATH = KNOWLEDGE_DIR / "index.md"

# 匹配 YAML frontmatter
FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---', re.DOTALL)
# 匹配一级标题
TITLE_RE = re.compile(r'^#\s+(.+)', re.MULTILINE)

SKIP_FILES = {"CLAUDE.md", "index.md", "AI_MANIFEST.md"}

MOC_DIRS = ["知识库", "运营思路"]


def parse_frontmatter(text: str) -> dict:
    """解析 YAML frontmatter，返回 dict。支持多行列表。"""
    match = FRONTMATTER_RE.search(text)
    if not match:
        return {}
    fm = {}
    current_key = None
    for line in match.group(1).split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key:
            val = stripped[2:].strip().strip('"').strip("'")
            if current_key in fm:
                if isinstance(fm[current_key], list):
                    fm[current_key].append(val)
                else:
                    fm[current_key] = [fm[current_key], val]
            continue
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val == "":
                fm[key] = []
                current_key = key
            else:
                if val.startswith("[") and val.endswith("]"):
                    inner = val[1:-1]
                    fm[key] = [v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()]
                else:
                    fm[key] = val
                current_key = None
    return fm


def extract_title(text: str, fallback: str) -> str:
    """提取一级标题"""
    match = TITLE_RE.search(text)
    return match.group(1).strip() if match else fallback


def extract_description(text: str) -> str:
    """提取第一段描述文字"""
    lines = text.split("\n")
    in_frontmatter = False
    fm_closed = False
    for line in lines:
        stripped = line.strip()
        if stripped == "---" and not fm_closed:
            in_frontmatter = not in_frontmatter
            if not in_frontmatter:
                fm_closed = True
            continue
        if in_frontmatter:
            continue
        if stripped.startswith("#") or not stripped:
            continue
        if stripped.startswith(">"):
            return stripped.lstrip("> ")[:80]
        if len(stripped) > 10:
            return stripped[:80]
    return ""


def collect_entries(knowledge_dir: Path) -> tuple[dict[str, list[dict]], list[str]]:
    """收集所有知识条目，按目录分组"""
    entries: dict[str, list[dict]] = defaultdict(list)
    all_tags: set = set()

    for md_file in sorted(knowledge_dir.rglob("*.md")):
        rel_path = str(md_file.relative_to(knowledge_dir))
        parts = rel_path.replace("\\", "/").split("/")

        if md_file.name in SKIP_FILES:
            continue

        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        category = parts[0] if len(parts) > 1 else "根目录"

        fm = parse_frontmatter(text)
        title = extract_title(text, md_file.stem)
        desc = extract_description(text)

        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        for tag in tags:
            all_tags.add(tag)

        entries[category].append({
            "file": rel_path,
            "title": title,
            "desc": desc,
            "tags": tags,
        })

    return dict(entries), sorted(all_tags)


def generate_index(entries: dict[str, list[dict]], all_tags: list[str], moc_hubs: list[tuple[str, str]]) -> str:
    """生成完整的 index.md 内容"""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_docs = sum(len(v) for v in entries.values())
    moc_count = sum(1 for cat in entries for e in entries[cat] if "MOC-" in e.get("file", ""))

    lines = [
        f"# 知识库索引",
        f"> 自动维护 | 更新于 {today}",
        "",
        f"- **共 {total_docs} 篇文档** · **{moc_count} 个 MOC 枢纽**",
    ]

    if all_tags:
        lines.append(f"- **标签**: {' · '.join(all_tags[:10])}{' …' if len(all_tags) > 10 else ''}")

    lines.extend([
        "",
        "---",
        "",
        "## 🧭 MOC 枢纽",
        "",
        "从任意枢纽进入，即可触达所有关联知识：",
        "",
        "| 枢纽 | 覆盖范围 |",
        "|------|---------|",
    ])

    for path, desc in moc_hubs:
        name = path.split("/")[-1]
        lines.append(f"| [[{path}|{name}]] | {desc} |")

    lines.extend([
        "",
        "---",
        "",
        "## 按目录",
        "",
    ])

    category_order = ["运营思路", "知识库", "根目录"]
    for cat in category_order:
        if cat not in entries:
            continue
        cat_entries = entries[cat]
        if not cat_entries:
            continue

        lines.append(f"### {cat}/ ({len(cat_entries)}篇)")
        lines.append("")

        for e in cat_entries:
            file_link = e["file"].replace("\\", "/")
            tag_str = " ".join(f"`{t}`" for t in e["tags"][:3])
            desc_str = f"  > {e['desc']}" if e["desc"] else ""
            lines.append(f"- [{e['title']}]({file_link}) {tag_str}")
            if desc_str:
                lines.append(desc_str)

        lines.append("")

    # 全标签索引
    lines.extend([
        "---",
        "",
        "## 全标签索引",
        "",
    ])

    tag_index: dict[str, list[str]] = defaultdict(list)
    for cat, cat_entries in entries.items():
        for e in cat_entries:
            file_link = e["file"].replace("\\", "/")
            for tag in e["tags"]:
                tag_index[tag].append(f"[{e['title']}]({file_link})")

    for tag in sorted(tag_index.keys()):
        count = len(tag_index[tag])
        lines.append(f"### {tag} ({count}篇)")
        for item in tag_index[tag]:
            lines.append(f"- {item}")
        lines.append("")

    lines.extend([
        "_索引自动维护。新增文档后运行 `knowledge_index_generator.py` 即可更新。_",
    ])

    return "\n".join(lines)


def generate_ai_manifest(category_path: Path, entries: list[dict]) -> str:
    """为单个子目录生成 AI_MANIFEST.md"""
    dir_name = category_path.name
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# AI_MANIFEST — {dir_name}/",
        f"> 自动生成于 {today} · 共 {len(entries)} 篇文档",
        "",
        "| 文件 | 描述 | 标签 | 状态 |",
        "|------|------|------|------|",
    ]

    for e in entries:
        file_name = Path(e["file"]).name
        desc = e["desc"] or "—"
        tags = ", ".join(e["tags"][:3]) or "—"
        lines.append(f"| {file_name} | {desc} | {tags} | — |")

    lines.extend([
        "",
        "> 🤖 此文件由 `knowledge_index_generator.py` 自动生成。",
        "> Agent 读取此文件即可了解目录全貌，无需扫描所有文档。",
    ])

    return "\n".join(lines)


def write_all_manifests(entries: dict[str, list[dict]], knowledge_dir: Path):
    """为每个子目录写入 AI_MANIFEST.md"""
    for category_dir in MOC_DIRS:
        category_path = knowledge_dir / category_dir
        if not category_path.exists():
            continue

        cat_entries = entries.get(category_dir, [])
        manifest_content = generate_ai_manifest(category_path, cat_entries)
        manifest_path = category_path / "AI_MANIFEST.md"

        manifest_path.write_text(manifest_content, encoding="utf-8")
        print(f"  📋 {manifest_path.relative_to(PROJECT_ROOT)}")


def discover_moc_hubs(knowledge_dir: Path) -> list[tuple[str, str]]:
    """扫描 Knowledge/ 发现所有 MOC 文件"""
    hubs = []
    for md_file in sorted(knowledge_dir.rglob("MOC-*.md")):
        rel_path = str(md_file.relative_to(knowledge_dir)).replace("\\", "/")
        try:
            text = md_file.read_text(encoding="utf-8")
            fm = parse_frontmatter(text)
            coverage = fm.get("tags", "")
            if isinstance(coverage, list):
                coverage = "、".join(coverage)
            hubs.append((rel_path, coverage or "—"))
        except Exception:
            hubs.append((rel_path, "—"))
    return hubs


def main():
    # Windows 终端 GBK 编码兼容
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

    dry_run = "--dry-run" in sys.argv

    entries, all_tags = collect_entries(KNOWLEDGE_DIR)
    moc_hubs = discover_moc_hubs(KNOWLEDGE_DIR)
    index_content = generate_index(entries, all_tags, moc_hubs)

    if dry_run:
        print("=== 预览 (--dry-run) ===")
        print(index_content[:2000])
        print(f"\n... ({len(index_content)} 字符)")
        return

    # 写入 index.md
    INDEX_PATH.write_text(index_content, encoding="utf-8")
    print(f"✅ index.md 已更新")

    # 写入各子目录的 AI_MANIFEST.md
    print("📋 生成 AI_MANIFEST.md ...")
    write_all_manifests(entries, KNOWLEDGE_DIR)

    total_docs = sum(len(v) for v in entries.values())
    print(f"   {total_docs} 篇文档 · {len(all_tags)} 个标签 · {len(entries)} 个目录")


if __name__ == "__main__":
    main()
