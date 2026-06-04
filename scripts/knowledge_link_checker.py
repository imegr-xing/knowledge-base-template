"""
知识库死链扫描器
用途: 扫描 Knowledge/ 下所有 .md 文件的 [[wiki 链接]]，检查目标是否存在
用法:
  python knowledge_link_checker.py              # 扫描所有链接
  python knowledge_link_checker.py --json       # JSON 输出
"""

import re
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# === 配置（自动检测路径，无需硬编码） ===
SCRIPT_DIR = Path(__file__).resolve().parent
VAULT_ROOT = SCRIPT_DIR.parent
KNOWLEDGE_DIR = VAULT_ROOT / "Knowledge"
LINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')


def build_page_index(vault_root: Path) -> dict[str, Path]:
    """构建页面名 → 文件路径的映射（模拟 Obsidian 的链接解析）"""
    page_index: dict[str, Path] = {}

    for md_file in vault_root.rglob("*.md"):
        if any(part.startswith(".") for part in md_file.parts):
            continue

        stem = md_file.stem
        rel_from_root = str(md_file.relative_to(vault_root)).replace("\\", "/")[:-3]

        page_index[stem] = md_file
        page_index[stem.lower()] = md_file
        page_index[rel_from_root] = md_file
        page_index[rel_from_root.lower()] = md_file

    return page_index


def resolve_link(link_target: str, page_index: dict[str, Path], source_file: Path = None) -> Path | None:
    """解析 [[链接]] → 目标文件路径"""
    target = link_target.strip().replace("\\", "/")

    if " " in target and "/" not in target:
        return None

    if target.endswith(".md"):
        target = target[:-3]

    # 直接匹配
    if target in page_index:
        return page_index[target]
    if target.lower() in page_index:
        return page_index[target.lower()]

    # 路径后缀匹配
    target_lower = target.lower().rstrip("/")
    for key, path in page_index.items():
        ks = key.lower().rstrip("/") if isinstance(key, str) else ""
        if ks.endswith("/" + target_lower) or ks == target_lower:
            return path

    # .. 相对路径解析
    if source_file and target.startswith(".."):
        try:
            source_dir = source_file.parent
            resolved = (source_dir / target).resolve()
            vault_root_resolved = VAULT_ROOT.resolve()
            if str(resolved).startswith(str(vault_root_resolved)):
                for key, path in page_index.items():
                    try:
                        if path.resolve() == resolved or path.resolve() == resolved.with_suffix(".md"):
                            return path
                    except Exception:
                        pass
        except (ValueError, OSError):
            pass

    # 直接路径匹配
    try:
        candidate = (VAULT_ROOT.resolve() / target).resolve()
        for key, path in page_index.items():
            try:
                if path.resolve() == candidate or path.resolve() == candidate.with_suffix(".md"):
                    return path
            except Exception:
                pass
    except Exception:
        pass

    return None


def scan_links(knowledge_dir: Path, page_index: dict[str, Path]) -> tuple[dict, dict]:
    """扫描所有链接，返回 {文件: [(链接目标, 是否有效, 行号)]} """
    results: dict[str, list] = defaultdict(list)
    stats = {"total_links": 0, "dead_links": 0, "files_scanned": 0}

    for md_file in knowledge_dir.rglob("*.md"):
        stats["files_scanned"] += 1
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            results[str(md_file)].append(("FILE_READ_ERROR", False, 0, str(e)))
            continue

        for line_no, line in enumerate(content.split("\n"), 1):
            for match in LINK_PATTERN.finditer(line):
                raw_target = match.group(1).strip()
                stats["total_links"] += 1

                link_target = raw_target
                link_target = re.split(r'\\\|', link_target)[0]
                link_target = link_target.split("|")[0]
                link_target = link_target.split("#")[0]
                link_target = link_target.rstrip("\\")
                link_target = link_target.strip()

                resolved = resolve_link(link_target, page_index, source_file=md_file)
                if resolved is None:
                    stats["dead_links"] += 1
                    rel_file = str(md_file.relative_to(knowledge_dir))
                    results[rel_file].append((raw_target, False, line_no, None))

    return dict(results), stats


def print_report(results: dict, stats: dict):
    """打印终端格式化报告"""
    dead_count = stats["dead_links"]
    total = stats["total_links"]

    if dead_count == 0:
        health = "🟢 健康"
    elif dead_count < 5:
        health = "🟡 需关注"
    else:
        health = "🔴 需修复"

    print("=" * 50)
    print(f"  知识库链接健康检查")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    print(f"  扫描文件: {stats['files_scanned']}")
    print(f"  总链接数: {total}")
    print(f"  死链数量: {dead_count}")
    print(f"  健康状态: {health}")
    print("=" * 50)

    if dead_count > 0:
        print("\n⚠️  死链详情:")
        print("-" * 50)
        for file, issues in sorted(results.items()):
            for target, is_valid, line_no, _error in issues:
                if not is_valid:
                    print(f"  📄 {file}:{line_no}")
                    print(f"     ❌ [[{target}]]")
        print("-" * 50)

    if dead_count == 0:
        print("\n✅ 无死链，知识库健康。")
    else:
        print(f"\n🔧 修复建议:")
        print(f"  1. 打开对应文件，找到死链所在行")
        print(f"  2. 检查链接目标是否改名或已删除")
        print(f"  3. 更正为目标文件名，或删除无效引用")
        print(f"  4. 重新运行扫描器确认修复")


def main():
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

    json_mode = "--json" in sys.argv

    page_index = build_page_index(VAULT_ROOT)
    results, stats = scan_links(KNOWLEDGE_DIR, page_index)

    if json_mode:
        print(json.dumps({"stats": stats, "dead_links": {
            f: [(t, l) for t, v, l, _ in issues if not v]
            for f, issues in results.items()
            if any(not v for _, v, _, _ in issues)
        }}, ensure_ascii=False, indent=2))
        return

    print_report(results, stats)

    if stats["dead_links"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
