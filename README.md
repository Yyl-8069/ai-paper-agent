# AI 论文助手

本地收集 AI 最新和社区热门论文，PDF 转 Markdown 后执行格式检查，
通过 DeepSeek API 生成中文简报和每周总结，按固定编号管理和选择性清理。

## FastAPI 网页版

双击 start-api.cmd，访问 http://127.0.0.1:8000。接口文档在 /docs。
网页可配置 DeepSeek、检索与收集、上传 PDF、查看任务、下载文件、生成总结和选择性清理。
停止后台服务可双击 stop-api.cmd；有任务运行时会拒绝停止，不会终止其他程序。
详见 [FastAPI 部署说明](docs/fastapi.md) 与 [验证记录](docs/fastapi-validation.md)。

## 开始使用

项目位于 D:/codex/projects/ai-paper-agent。Python、依赖、缓存和默认资料库均在 D 盘。

1. 双击 start.cmd 打开菜单。
2. 选择 1，在本机终端输入 DeepSeek API Key；输入不会显示，保存在本项目 .env。
3. 选择 2 收集最新论文，或选择 3 收集社区热门论文。
4. 从候选清单中选择论文，程序下载、转换、检查并生成简报。
5. 通过 7 查看论文编号和报告 ID，通过 8 选择文件类型进行清理。

本地 PDF 可直接使用菜单 4 导入，无须 API Key；生成中文总结时才需要密钥。
API Key 不要发到聊天中。默认模型 deepseek-flash，可在配置菜单修改。

## 运行方式

在项目目录打开 PowerShell：

~~~powershell
.\start.cmd
.\start.cmd search --mode latest --days 7 --limit 5
.\start.cmd search --mode hot --limit 5
.\start.cmd collect --mode latest --days 7 --limit 5
.\start.cmd collect --mode latest --limit 2 --no-summary
.\start.cmd import-pdf "D:\papers\example.pdf" --title "论文标题"
.\start.cmd brief P000001/v1
.\start.cmd weekly --week 2026-W44
.\start.cmd catch-up
.\start.cmd list
.\start.cmd cleanup --mode pdf --refs P000001/v1
.\start.cmd cleanup --mode summary --reports 总结ID
.\start.cmd cleanup --mode all --refs P000001/v1 --reports 总结ID
.\start.cmd cleanup --mode markdown --since 2026-10-01 --until 2026-10-31
~~~

search 只检索；collect 是用户主动发起的下载。
命令行 collect 收集命令参数指定范围的候选，菜单提供进一步勾选。
已主动删除的论文不会被重复收集自动恢复；使用 collect --restore 才允许恢复。
--library 可在子命令前指定另一个资料库，建议始终选 D 盘路径。

## 每周总结

当前自动安装被 Windows 权限拒绝，请右键 install-weekly.cmd 选择“以管理员身份运行”完成安装。

按用户选择，每周日北京时间 21:00 运行 catch-up，只处理已收集材料，不下载新论文。
报告按北京时间自然周编号，写明生成截止时间；周日 21:00 后补收的论文会在后续任务中补充旧周报告并保留前一版本。
已主动删除的周报不会自动重建；手动指定 weekly --force 可重建。
关机时不运行，Windows 任务计划设置允许错过后补跑；未配置密钥时任务失败并保存日志。

任务名为 AI Paper Agent Weekly。可在 Windows 任务计划程序停用或删除。
安装/更新脚本见 docs/install-weekly-task.ps1；运行日志保存在 library/logs。
同一资料库同时只允许一个操作。若强制结束进程，确认无任务运行后再删除 library/.operation.lock。

## 资料与编号

~~~text
library/
  collection.sqlite
  index.md
  papers/P000001/v1/
    original.pdf
    paper.md
    assets/
    metadata.json
    conversion.json
    validation.json
  briefs/
  weekly/
  logs/
~~~

P000001 是固定编号，v1 是论文来源版本。索引保留来源 ID 和文件状态，编号不复用。
本地导入按文件 SHA-256 去重；arXiv 按来源 ID 与版本去重。
以编号查 index.md 或菜单 7，即使文件已删仍能确认对应论文身份。
本地原始文件导入后仅复制到资料库，清理不会删掉资料库外的原始文件。

## 四种清理

- pdf：只删所选论文版本的 PDF。
- markdown：只删转换全文及不再被其他已登记 Markdown 引用的图片，保留总结。
- summary：只删显式选中的简报或周报。
- all：删除预览中选中的论文文件、附件和总结。

多论文共享周报必须按报告 ID 单独选择，不因选择一篇论文而连带删除。
每次删除均列出具体文件和预计释放空间，输入 DELETE 才执行。该删除不经过回收站。
索引、来源身份和删除记录始终保留，便于查编号；全部删除不等于销毁整个资料库。
文件变化会使确认失效；部分删除失败会逐项报告。
图片只有在程序能确认不被其余已登记文档引用时才纳入删除。
资料库外手工复制的文档不在依赖跟踪范围。

## 格式检查与内容限制

检查器复用原 markdown_validator 的 PyMarkdownApi().scan_path()。
论文、简报、周报都执行检查，规则号、行号和问题写入 validation.json 或对应报告的 .validation.json。
格式失败会明确显示 issues，并保留原输出供复核，不把“生成文件”说成“格式通过”。
对论文关闭 MD013、MD024、MD025、MD033、MD041，避免长公式、重复页标题等常见误报，其余规则保留。
不会为消除警告擅自改写公式、表格或科研结论。

PDF 转换完全在本机执行，无在线 PDF 解析服务或大型 GPU 模型。
第一版不支持扫描件 OCR；限制 50 MiB、200 页，单篇转换默认 180 秒。
公式、双栏阅读顺序、复杂表格和图片仍需人工复核，所有转换全文标记 extracted_unverified。
API 输入有字符预算，超出部分标记 excerpt；不能把节选分析宣称为全文精读。
全文缺失则回退摘要并标记 abstract_only；无摘要也无全文则不生成研究结论。
参考文献附近的数学排版可能不完整，原始 PDF 可用于核对。

DeepSeek 只接收用于总结的提取文本，不上传 PDF。密钥保存在本机 .env 且被 Git 忽略；
会产生 DeepSeek API 费用。程序记录可获得的 token 数，费用未实测时记 unknown。
没有配置密钥就不会发起模型请求。论文属于数据，不能给程序授权执行删除或系统命令。

## 来源与热度

最新论文：arXiv 官方 API，覆盖 cs.AI、cs.LG、cs.CL、cs.CV、cs.RO、stat.ML。
热门论文：Hugging Face Daily Papers 的观察票数与来源时间，不等同于整个学术界排名。
热门候选先回查 arXiv 版本，再登记本地编号。来源不可用时报错，不用模型编造热度。
Thank you to arXiv for use of its open access interoperability.

## 安装与验证

已有独立 Python 3.11，不改变系统 Python。若重建环境，在本项目目录设置所有安装路径到 D 盘：

~~~powershell
$env:UV_CACHE_DIR = "$PWD/.cache/uv"
$env:UV_PYTHON_INSTALL_DIR = "$PWD/.runtime"
$env:TEMP = "$PWD/tmp"
$env:TMP = $env:TEMP
.\.tools\uv.exe sync --locked --python .runtime/cpython-3.11-windows-x86_64-none/python.exe
.\.venv\Scripts\python.exe -m pytest -q -o cache_dir=tmp/pytest-cache --basetemp=tmp/pytest
~~~

当前验证记录见 evals/results.md。测试使用临时资料库，不删除用户正式论文。
线上 API 的可用性与转换质量需分别验证，测试替身通过不等于真实模型总结可靠。
退出菜单输入 0，命令执行时 Ctrl+C；中断产生的 .part 文件可在后续人工清理。

## 许可与来源

原参考样例：crewAIInc/crewAI-examples 的 crews/markdown_validator，来源版本记录在原样例 UPSTREAM_SOURCE.json。
PDF 工具链使用 PyMuPDF/PyMuPDF4LLM，遵循各自上游许可；本项目未赋予再分发其二进制的新许可。

## 界面迭代（2026-11-01）

本次整理版本将原长页面改为浅色学术工作台：分区导航、真实资料库统计、论文检索与阅读区，以及独立的导入、设置和选择性清理区域。保留原 API、手动收集和删除前预览确认流程，无新增前端依赖。

验证：50 项测试通过，JavaScript 语法检查通过；本机浏览器核对窄屏布局、资料库导航及空清理预览与取消。未执行真实收集、付费模型请求或删除，未测量性能指标，也未完成桌面宽屏视觉验证。

## 时间范围与全文翻译（2026-11-01）

网页检索提供 1 天内、7 天内、一个月内、半年内、一年内。月和年按北京时间的日历回推，月末超出目标月份时取该月最后一天；旧 API 的 days 参数继续兼容。热门来源仍为 Hugging Face Daily Papers 当前候选池，按所选范围过滤，不是历史全年热榜。

收集或导入并完成本机转换后，在「我的资料库」点击「中文全文翻译」。需要先在模型设置配置 DeepSeek 密钥；确认后分段发送全文，产生 API 费用。译文完成后可展开「查看中文译文」，或下载 Markdown。直接查看不创建浏览器下载文件。

- 正式资料库：D:/codex/projects/ai-paper-agent/library。
- 原文：papers/P000001/v1/paper.md；译文：同目录 paper.zh.md；检查记录：translation.validation.json。编号因论文而异。
- 翻译不使用摘要替代全文，也不采用总结流程的正文截取。输入上限 50 万字符，每段最多约 6000 字符；异常超长连续片段会拒绝。任一段失败或输出截断，都不发布部分译文；重试可能重新产生全部翻译费用。
- 常见公式、代码、HTML 与 Markdown 链接通过占位符原样保留，结构校验失败不保存。提取遗漏及复杂 LaTeX 仍需人工检查，不能保证语义翻译准确。
- 相同原文已有完整译文时复用；原文、译文发生改变或译文缺少校验记录时拒绝覆盖。旧译文请先核对并通过清理流程移除。
- 「只删 Markdown」包含所选论文的英文 Markdown 和中文译文；「只删 PDF」不影响译文；「只删总结」不删除译文。
- 程序拒绝 C 盘资料库，并将直接启动服务或 CLI 的临时目录设到项目 tmp。不要将项目迁回 C 盘。浏览器另存或下载的目标由浏览器控制，下载时请手动选择 D 盘；程序无法更改浏览器的默认下载盘。

验证：59 项测试通过，包含模拟 DeepSeek HTTP 的分段覆盖、公式链接保留、截断拒绝、缓存复用、防覆盖、翻译 API、清理与日历边界。真实 DeepSeek 翻译质量与费用尚未评估。

## 关键词相关检索与反馈（2026-11-01）

网页默认选择「关键词相关检索／不限时间」。研究主题可填 harness，按 arXiv 标题和摘要的相关度返回历史论文，不强制限定原来的六个 AI 分类。多个主题词以及逗号分隔的「相关词」以 OR 合并；相关词中的短语整体匹配，例如 evaluation harness。输入只作为关键词，不执行用户输入的 arXiv 查询运算符。此功能不是语义向量检索，不会自动推断同义词；宽泛关键词可能混入其他领域。

每页最多 10 篇，可翻阅前 1000 条。页面展示来源报告的总匹配数，它不是全部已收集论文数，也不保证每条都与 AI 有关。翻页会清空当前勾选，请先收集本页需要的论文；收集仍使用服务端保存的本页快照，不会因翻页错配论文。arXiv 最新与社区热门模式仍保留；这两种模式不支持不限时间或翻页。

相同检索条件及页码在 5 分钟内复用结果，服务进程最多缓存 100 组，重启失效；短时间内可能看不到刚更新的来源记录。检索中按钮禁用并显示等待秒数，翻页保留旧列表的占位布局，结束后展示数量和实际耗时。其他主要操作也增加按钮处理中状态。来源超时或失败会给出明确提示，网络延迟不能由界面完全消除。

本轮验证：64 项测试通过，JavaScript 语法检查通过。真实 harness 查询首屏工具调用约 1.05 秒、浏览器首屏约 1.1 秒，第二页约 1.0 秒；返回缓存页显示 0.0 秒（四舍五入）。结果包含 2026 年 6 月、9 月论文，验证不再受默认近 7 天限制；这些是单次观测，不是性能承诺。未下载、翻译或删除论文。已有服务需 Ctrl+C 后重新运行 start-api.cmd，再刷新网页。
