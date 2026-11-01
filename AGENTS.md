# AI 论文助手开发约定

- 项目主线是 Markdown 检查能力的实际运用：统一检查器、工作流覆盖、规则与问题记录、结果展示及复核。论文检索、翻译和周报为应用场景，README 优先解释 Markdown 实现。
- 准确区分 PyMarkdown 工具集成、完整 CrewAI 编排与独立 SKILL.md 技能包；未实现的能力不得宣称已具备。

- 项目根目录为 D:/codex/projects/ai-paper-agent；所有环境、缓存、临时文件和资料库放 D 盘。
- 开发前读取 D:/codex/skills/ponytail/SKILL.md 和 D:/codex/skills/superpowers/开发前注意/agent-development-standards/SKILL.md，按任务读取 references。
- 设计与计划见 docs/design.md、docs/plan.md；已确认用户仅手动收集，周日北京时间 21:00 总结，四种清理均需预览后确认。
- workflow 管流程；tools 只做单一能力；agents 负责有来源的总结；prompts 与代码一起版本管理。
- PDF 本机解析，总结使用 DeepSeek API。密钥不进入源码、提示词、日志、测试与 Git；不得输出真实 .env。
- 用户原始文件不覆写；只有资料库内登记且在预览中确认的文件可删除；固定编号不复用。
- reports 和数据库变更须同步考虑删除记录、历史引用、周报补跑与去重。
- nine responsibilities: agents、tools、skills、workflows、prompts、context、memory、tests、evals。未启用模块只写职责。
- 改工具或状态需测试失败、边界和幂等；改模型或提示词另跑固定论文评估，未运行不得宣称通过。
- 必跑：.venv/Scripts/python.exe -m pytest -q -o cache_dir=tmp/pytest-cache --basetemp=tmp/pytest。
- 真实论文、.env、library、日志、运行数据库和运行环境不提交 Git；依赖修改用 uv 更新锁文件。
- 规范只在能读取这些入口的项目生效，不声称全局安装。
