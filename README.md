# 知识库模板

基于 **Obsidian + Claude Code** 的个人知识管理系统模板。

> "市面上的知识库模板是设计出来的。这个是用了 3 个月、管了 47 篇文档后提纯出来的。"

---

## 快速开始

```bash
# 1. 克隆仓库
git clone <repo-url> my-knowledge-base
cd my-knowledge-base

# 2. 用 Obsidian 打开 Knowledge/ 目录作为 Vault
#    Obsidian → Open folder as vault → 选择 Knowledge/

# 3. （可选）在项目根目录启动 Claude Code
#    claude
```

---

## 目录结构

```
├── CLAUDE.md              # Agent 行为指令（核心差异化）
├── README.md              # 本文件
├── .gitignore
├── Knowledge/
│   ├── index.md           # 总索引（脚本自动维护）
│   ├── MOC-工作流全景.md  # 顶层枢纽
│   ├── 知识库/            # 技术参考、产品方案、市场研究
│   │   ├── CLAUDE.md
│   │   ├── MOC-AI工具生态.md
│   │   ├── MOC-产品与变现.md
│   │   ├── MOC-技术参考.md
│   │   ├── Skills使用指南-知识贡献规范.md
│   │   └── 示例-技术参考文档.md    ← 示例
│   └── 运营思路/          # SOP、方法论、数据复盘
│       ├── CLAUDE.md
│       ├── MOC-内容运营.md
│       └── 示例-运营复盘.md       ← 示例
└── scripts/
    ├── knowledge_index_generator.py   # 索引生成 + AI 清单
    └── knowledge_link_checker.py      # 死链检查
```

---

## 三种用法

### 1. 纯手动（Obsidian 用户）
用 Obsidian 打开 `Knowledge/` 作为 Vault，手动写文档、加链接。索引由脚本维护。

### 2. AI 辅助（Claude Code 用户）
在项目根目录启动 Claude Code，Agent 自动读取 CLAUDE.md 获得完整行为指令。

### 3. 全自动（推荐）
在 Claude Code 中使用斜杠命令：
- `/新知识 <主题>` — AI 帮你按规范写文档 + 自动更新索引
- `/周复盘` — AI 扫描本周变化，生成复盘报告
- `/查链接` — AI 检查并修复死链

---

## 维护命令

```bash
# 新增文档后重建索引（同时生成 AI_MANIFEST.md）
python scripts/knowledge_index_generator.py

# 检查所有 Wiki 链接有效性
python scripts/knowledge_link_checker.py
```

---

## 设计哲学

| 原则 | 说明 |
|------|------|
| **索引优先** | Agent 初始化只读地图，不搬领土 |
| **MOC 路由** | Map of Content 枢纽网，按需深入 |
| **错误也是知识** | 保留踩坑记录，Agent 能回溯历史错误 |
| **实战提纯** | 不是设计出来的理想结构，而是从真实使用中剥出来的 |

---

## 依赖

- [Obsidian](https://obsidian.md/) — 知识管理前端（可选）
- [Claude Code](https://claude.ai/code) — AI 协作助手（可选）
- Python 3.10+ — 运行维护脚本

---

## 贡献

欢迎提交 Issue 和 PR。新增文档请遵循 `Skills使用指南-知识贡献规范.md` 中的规范。
