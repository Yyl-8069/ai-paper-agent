# Markdown 论文工作台

把 Markdown 格式检查用于论文处理：**收集／导入 PDF → 本机转 Markdown → 格式检查 → 保存检查记录**。中文译文、简报和周报也会检查。

## Markdown 检查什么

| 范围 | 常见问题 |
| --- | --- |
| 标题 | 缺少空格、层级跳跃、前后缺少空行 |
| 列表与引用 | 缩进、符号、编号及空格不规范 |
| 空格与空行 | 行末多余空格、连续空行、末尾缺少换行 |
| 代码块 | 围栏写法、前后空行、缺少语言标识 |
| 链接与图片 | 空链接、裸网址、图片缺少替代文字 |
| 强调与分隔线 | 符号、空格及写法不一致 |

实现入口：[tools/validate.py](tools/validate.py)。调用 **PyMarkdownApi.scan_path()**，输出通过状态或问题清单，包含规则号、行号和描述。

例如，标题后缺少空行会报告 MD022：

~~~markdown
# 标题

正文与标题之间需要空行。
~~~

为了适应论文，关闭五项规则：行长度（MD013）、同级重复标题（MD024）、多个一级标题（MD025）、内联 HTML（MD033）、首行一级标题（MD041）。

**格式检查不验证论文事实、翻译准确性或公式完整性。** 当前保存问题供人工复核，不自动修复，也不因格式问题阻止入库。实现复用了原样例的检查能力，尚未发布独立 SKILL.md 技能包或运行完整 CrewAI 编排。

## 启动

在 PowerShell 运行：

~~~powershell
cd D:\codex\projects\ai-paper-agent
.\start-api.cmd
~~~

打开 [本地工作台](http://127.0.0.1:8000/)，按 Ctrl+C 停止。已有服务运行时不要重复启动。

首次重建依赖见[部署说明](docs/fastapi.md)。PDF 转换无需密钥；翻译和总结需在页面配置 DeepSeek，会发送提取文本并产生费用。

## 使用与文件

- 搜索关键词，默认不限时间、按相关度排序，勾选后手动收集；也可导入本地 PDF。
- 在资料库查看 Markdown、生成中文译文、下载检查记录。
- 按编号定位论文；清理可选 PDF、Markdown、总结或全部，先预览再确认。
- 周总结只处理已收集论文；周日 21:00 自动运行须另行安装定时任务，见部署说明。

文件默认保存在 **D:\codex\projects\ai-paper-agent\library**，禁止资料库存到 C 盘。浏览器下载时也请选择 D 盘。

| 文件／目录 | 用途 |
| --- | --- |
| tools/validate.py | 统一 Markdown 检查器 |
| workflows/ | 收集、翻译、报告流程 |
| app/ | FastAPI 与网页 |
| library/papers/P000001/v1/ | PDF、原文、译文及检查记录 |
| library/briefs/、library/weekly/ | 简报、周报及同名检查 JSON |
| tests/、evals/ | 代码测试与评估记录 |

原文检查保存为 validation.json，译文检查保存为 translation.validation.json。网页提供对应记录入口，尚无逐行问题面板。

## 验证与限制

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q -o cache_dir=tmp/pytest-cache --basetemp=tmp/pytest
~~~

当前功能版本已通过 64 项测试。PDF 解析使用本机 PyMuPDF/PyMuPDF4LLM，格式检查使用 pymarkdownlnt；暂不支持扫描件 OCR，复杂公式和排版需人工核对。真实模型内容质量不以测试通过代替评估。

[验证记录](evals/results.md) · [迭代记录](docs/progress.md) · [原参考样例](https://github.com/crewAIInc/crewAI-examples/tree/main/crews/markdown_validator)

论文来源为 arXiv 与 Hugging Face Daily Papers；社区票数不代表学术排名。工具与论文遵循各自许可。Thank you to arXiv for use of its open access interoperability.
