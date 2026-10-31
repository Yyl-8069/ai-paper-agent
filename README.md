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
