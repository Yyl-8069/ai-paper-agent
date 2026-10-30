# AI Paper Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:执行计划 for native execution, or superpowers:子代理驱动开发 if the user selects delegation. Steps use checkbox syntax for tracking.

**Goal:** 实现手动收集 AI 论文、本机转换与格式检查、本地简报和每周总结，以及四种可预览确认的清理方式。

**Architecture:** Python 本地应用以工作流编排独立工具，SQLite 保存索引与状态，普通文件保存正文和报告。模型仅承担筛选和总结，程序执行来源核验、编号、路径检查与删除授权。

**Tech Stack:** Python、SQLite、PyMarkdown；转换器和总结模型经过任务 1 的机器与接口验证后选定并锁版本。初期采用本地命令菜单，网页界面不在本计划范围。

**Spec:** [已审阅设计](ai-paper-agent-design.md)。本计划命令和测试均为待实现目标，不表示已经执行。

## Global Constraints

- 由用户决定何时收集，不自动按日或按周检索、下载新论文。
- PDF 转 Markdown 完全在本机执行，不调用在线 PDF 解析服务。
- 每周总结已经收集的文档，使用固定论文编号定位依据。
- 清理由用户选择对象、范围和删除方式后确认执行，不自动删除。
- 编号永久不复用，全部删除仍保留最小编号索引与删除记录。
- 产品使用独立目录及 Git 仓库，不修改参考样例、不把技能库作为产品仓库。
- agents、tools、skills、workflows、prompts、context、memory、tests、evals 为根目录职责边界。
- 密钥不进入源码和日志；论文内容不能改变系统权限。

## Review Focus

1. 下载来源 ID 不变但论文版本变化：保留固定编号，版本分别追踪（任务 2、3）。
2. PDF 双栏错序、公式或表格缺失：格式通过仍须标记内容复核状态（任务 4）。
3. 跨周、关机错过触发或重复运行：按北京时间周边界补跑且不重复报告（任务 6）。
4. 共享图片或多论文周报：清理不得因删除一篇论文而连带删除共享内容（任务 7）。
5. 确认后文件替换、符号链接逃逸或部分删除失败：重新预览或明确失败，索引反映实际状态（任务 7）。

## 文件与接口映射

最终路径以独立项目根目录为基准：

- `app/cli.py`：交互菜单与命令入口。
- `app/models.py`：共享数据类型。
- `app/store.py`：SQLite 索引与状态。
- `tools/search.py`、`download.py`、`convert.py`、`validate.py`、`cleanup.py`：单项基础能力。
- `agents/researcher.py`：论文筛选与有依据的总结。
- `workflows/collect.py`、`weekly.py`、`cleanup.py`：流程控制。
- `prompts/`：筛选、单篇摘要、周报、事实约束和输出 schema。
- `tests/`、`evals/`：代码验证与固定论文评估。
- `docs/`：本设计、计划、环境核验与运行说明。

共享类型：`PaperCandidate(source, source_id, version, title, authors, published_at, abstract, pdf_url, evidence)`；`PaperRef(paper_id, version)`；`Artifact(ref, kind, path, sha256, size, status)`；`ConversionResult(markdown_path, assets, warnings, completeness)`；`ValidationResult(path, issues, status)`；`Report(id, kind, period, path, references, coverage)`；`CleanupPlan(id, mode, targets, bytes_total, fingerprint)`；`CleanupResult(deleted, missing, failed)`。kind/mode/status 使用显式枚举，日期存带时区 ISO 8601。

## Task 1: 环境与依赖核验

**Files:** `docs/environment.md`、`docs/decisions.md`。

**Interfaces:** 产出确定的产品目录、Python 版本、转换器版本、模型连接方式、周报时间、运行资源约束；不创建未经确认的收费服务或定时任务。

- [ ] 只读核验 Python、CPU、内存、可用磁盘、GPU 与现有本地模型服务；不输出凭据。
- [ ] 提议独立目录，默认候选 `D:/codex/projects/ai-paper-agent`；核实可写权限与已有目录，禁止覆盖已有项目。
- [ ] 依据核验结果查阅官方转换库文档，用用户允许的代表性论文验证双栏、公式、表格；记录首次模型下载与离线运行条件，固定可用版本。
- [ ] 明确总结模型：本地或在线由用户选择；本机 PDF 转换不等于授权在线发送论文正文。在线方案须明确费用与数据范围。
- [ ] 明确每周总结时间，建议周一 09:00 北京时间总结上一自然周；具体值待用户选定。
- [ ] 输出核验记录及明确技术决策，再开展后续依赖安装。不能用默认选择冒充已经获得的用户事实或授权。

## Task 2: 建立独立项目与可追溯资料库

**Files:** `pyproject.toml`、锁文件、`.gitignore`、`.env.example`、`AGENTS.md`、`README.md`、`app/models.py`、`app/store.py`、九个职责目录说明、`tests/test_store.py`。

**Interfaces:** `Store.register(candidate: PaperCandidate) -> PaperRef`；`Store.lookup(ref: PaperRef) -> dict`；`Store.record_artifact(artifact: Artifact) -> None`。

- [ ] 写测试：同 source/source_id 返回同一 paper_id；新 version 新建版本；删除后编号不复用；并发登记不产生重复；空库初始化可重复执行。
- [ ] 运行 `python -m pytest tests/test_store.py -q`，确认缺少实现导致失败。
- [ ] 实现 SQLite 唯一约束、事务、编号和状态；建根目录职责与真实环境说明。使用任务 1 选定依赖生成锁文件。
- [ ] 重跑测试，确认全部通过；在独立产品仓库提交本任务文件，提交不含数据库、密钥及论文正文。

## Task 3: 手动搜索、去重与下载

**Files:** `tools/search.py`、`tools/download.py`、`agents/researcher.py`、`prompts/selection.md`、`workflows/collect.py`、`app/cli.py`、`tests/test_collect.py`。

**Interfaces:** `search_papers(query: str, start: datetime, end: datetime, limit: int) -> list[PaperCandidate]`；`download_pdf(candidate: PaperCandidate, target: Path) -> Artifact`；`collect(request: dict, store: Store) -> str` 返回运行 ID。

- [ ] 写测试覆盖日期范围、空结果、重复版本、API 超时、未知热度、无效 PDF、下载中断与断点重跑；缺热度时 evidence 必须为空且不得产生热度排名。
- [ ] 运行 `python -m pytest tests/test_collect.py -q`，确认预期失败。
- [ ] 使用 arXiv 官方接口实现首个来源；查询热门信号的官方可用接口，记录信号含义和限制。不可用时仅提供最新榜，明确热门来源不可用，不伪造热门榜。
- [ ] 下载限定 HTTPS、允许的来源和重定向目标；设置超时、大小上限与有限重试，先写临时文件，核实 PDF 后原子保存。模型筛选输出限定为候选 ID 子集。
- [ ] 接入手动收集命令及菜单，不配置自动收集；重跑测试通过后提交。

## Task 4: 本机转换与 Markdown 检查

**Files:** `tools/convert.py`、`tools/validate.py`、`tests/test_convert.py`、`tests/test_validate.py`、`evals/conversion/manifest.json`。

**Interfaces:** `convert_pdf(pdf_path: Path, output_dir: Path) -> ConversionResult`；`validate_markdown(path: Path) -> ValidationResult`。

- [ ] 写测试：转换成功、空输出、解析部分失败、资源超限、附件路径正确；格式失败返回规则和行号。构造格式通过但正文不完整的结果，断言 completeness 仍是待复核。
- [ ] 运行 `python -m pytest tests/test_convert.py tests/test_validate.py -q`，确认预期失败。
- [ ] 接入任务 1 选定的本机转换器；设置进程超时与失败出口。复用参考样例的 PyMarkdownApi 扫描与格式化逻辑，配置论文公式相关规则，不改写科研内容。
- [ ] 在离线解析条件下检查代表性 PDF，记录页数、正文、公式、表格、图片和人工核对结果；不把测试替身结果写成真实转换成功。
- [ ] 重跑单元测试并提交；实际转换评估不通过时记录限制并阻止声称完整全文。

## Task 5: 有依据的中文简报

**Files:** `agents/researcher.py`、`prompts/summary.md`、`prompts/constraints.md`、`prompts/output.schema.json`、`workflows/collect.py`、`tests/test_brief.py`、`evals/papers/manifest.json`。

**Interfaces:** `summarize_paper(ref: PaperRef, content: str, evidence: dict) -> dict`；`write_brief(run_id: str, summaries: list[dict], output: Path) -> Report`。

- [ ] 写测试：每条结论必须引用输入 ref；未知编号拒绝保存；仅摘要材料明确标记；未成功转换不能宣称全文分析；模型超时和输出非法时记录失败。
- [ ] 运行 `python -m pytest tests/test_brief.py -q`，确认预期失败。
- [ ] 按任务 1 确定模型接入；设置调用预算，论文分段保留出处，超出上下文时明示覆盖范围；将论文中的指令视为数据。
- [ ] 生成标题、概述、依据、局限、阅读建议和覆盖情况；报告先写临时文件，格式检查与编号核验后保存，失败保留为未通过草稿。
- [ ] 重跑测试并运行固定评估集，核对事实、编号与失败出口；真实成本缺失记 unknown，提交代码与脱敏评估记录。

## Task 6: 每周总结与本机调度

**Files:** `workflows/weekly.py`、`prompts/weekly.md`、`app/cli.py`、`docs/scheduling.md`、`tests/test_weekly.py`。

**Interfaces:** `summarize_week(week: str, store: Store, force: bool = False) -> Report`；`due_weeks(now: datetime, store: Store) -> list[str]`。

- [ ] 写测试：北京时间跨周边界、重复执行、无新增、正文已删、模型失败、关机错过后补跑；每个编号必须映射实际收集版本。
- [ ] 运行 `python -m pytest tests/test_weekly.py -q`，确认预期失败。
- [ ] 按自然周收集材料并跨论文归纳，登记引用；同周默认不重复生成，force 明确新报告版本，旧报告不静默覆盖。
- [ ] 接入手动周报命令；按任务 1 确定时刻准备 Windows 任务计划配置，调度只生成周报，禁止触发新收集或删除。用户确认具体调度配置后再安装。
- [ ] 重跑测试，验证调度命令可手动执行；说明机器关闭期间不运行、恢复后如何补跑，提交。

## Task 7: 四种清理与交付

用户可选项固定为：只删 PDF、只删 Markdown、只删总结、全部删除。

**Files:** `tools/cleanup.py`、`workflows/cleanup.py`、`app/cli.py`、`tests/test_cleanup.py`、`tests/test_end_to_end.py`、`README.md`、`evals/results.md`。

**Interfaces:** `plan_cleanup(root: Path, selection: dict, mode: str, store: Store) -> CleanupPlan`；`execute_cleanup(plan: CleanupPlan, confirmation: str, store: Store) -> CleanupResult`。

- [ ] 写四种 mode（pdf、markdown、summary、all）测试，断言目标清单精确、字节数正确、索引保留；只删 Markdown 不删总结；共享附件、跨论文周报必须显式选择。
- [ ] 写边界测试：库外路径、链接逃逸、确认后文件变化、缺失文件、权限失败、部分成功和重复执行；未确认绝不调用文件删除。
- [ ] 运行 `python -m pytest tests/test_cleanup.py -q`，确认预期失败。
- [ ] 实现真实路径与文件指纹核验，预览绑定确认；逐文件执行、逐项记状态，保留不可复用编号；操作范围仅限程序登记且处于资料库内的目标。
- [ ] 完成交互菜单，支持按编号、版本或日期选择与批量预览；不让模型代替用户确认。显示不可恢复删除及预计释放空间。
- [ ] 用临时测试资料库端到端验证手动收集、转换、检查、简报、周报、查编号和四种删除，禁止用用户正式资料做删除测试。
- [ ] 运行 `python -m pytest -q`，运行固定业务评估；执行实际来源与模型冒烟时单独记录网络、解析和费用结果。
- [ ] 更新真实安装、运行、停用调度、清理与恢复限制说明，提交最终变更；交付通过项、失败项和未验证项，不以格式通过代替业务通过。

## 自检与执行交接

已覆盖设计中的手动收集、本机转换、格式与内容分检、固定编号、简报、周报、调度补跑、四种清理、日志、状态恢复、权限与评估要求。任务 1 的用户选择是技术决策前置条件，不能从此前功能批准推定具体模型付费、正文外发或产品目录授权。

建议本会话原生顺序执行：接口依赖较紧密，先完成可演示闭环再扩展。用户需审阅本计划并选择原生执行或子代理执行，之后进入实施；本计划尚未执行。
