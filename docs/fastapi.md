# FastAPI 本机部署

启动：双击根目录 start-api.cmd，浏览器访问 http://127.0.0.1:8000。
接口文档：http://127.0.0.1:8000/docs；OpenAPI：http://127.0.0.1:8000/openapi.json。
前台窗口按 Ctrl+C 停止。端口占用时不要反复启动；先检查已有服务。
仅监听本机回环地址，单进程、单 worker，不开启 reload。开发与运行文件均在 D 盘。

## 操作

网页可配置 DeepSeek、检索和勾选候选、收集、上传本地 PDF、下载已登记文件、
生成简报与周报、查看后台任务及执行四种选择性清理。
API Key 输入后不会回显。原 .env 与 CLI 配置共用，已有密钥继续可用。
上传以 application/pdf 流式写入 D 盘临时目录，最大 50 MiB，不使用默认 C 盘上传缓存。

PDF 转换、收集和模型总结通过进程内后台任务执行；返回 202 仅表示已接受，
通过 GET /api/jobs/{job_id} 查看真实结果。任务记录保存在同一 SQLite。
应用重启将未完成任务标记 interrupted；不会默默重跑收费请求。
当前单机版本不使用 Redis/Celery，服务运行期间需保持进程。
所有资料库修改共用原 CLI 文件锁，与每周总结任务互斥；忙时返回 409。

## 接口

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET | /health | 健康检查 |
| GET | /api/session | 获取本次服务的本地操作令牌 |
| GET / PUT | /api/config | 查看配置状态 / 保存密钥和模型 |
| GET | /api/papers | 编号、元数据与文件状态 |
| GET | /api/reports | 简报和周报清单 |
| GET | /api/files?path=... | 下载资料库内已登记且存在的文件 |
| POST | /api/search | 检索并保存服务端候选清单 |
| POST | /api/collect | 按 search_id 和从 1 开始的 indices 收集 |
| POST | /api/import | 上传 PDF，query 可提供 title 与 filename |
| POST | /api/brief | 总结指定 refs |
| POST | /api/weekly | 生成指定 week，可 force 重建 |
| POST | /api/catch-up | 补充到期周报，不检索新论文 |
| GET | /api/jobs、/api/jobs/{job_id} | 任务清单与状态 |
| POST | /api/cleanup/preview | 提交 mode、refs、reports，生成精确清单 |
| POST | /api/cleanup/execute | 提交 plan_id 与 confirmation: DELETE 执行 |

写操作需要 X-Local-Token 请求头，并拒绝跨站 Origin；网页自动处理。
Swagger 可先调用 /api/session，再在 Authorize 中填入 token。
令牌不是 DeepSeek 密钥，服务重启后令牌更新。
未经登记的 .env、数据库、临时文件和任意主机路径无法通过下载接口读取。
Markdown 以附件下载，不将论文文本作为 HTML 执行。

## 部署范围与限制

本次是用户本机部署，不开放公网端口。若需要多人远程访问，应另行配置用户认证、
HTTPS、持久任务队列与访问策略，不能仅改成 0.0.0.0。
不会因启动 FastAPI 自动安装每周 Windows 任务；周日 21:00 调度仍使用已有独立脚本。
DeepSeek 实际付费总结仍需用户在本机配置有效密钥后验证。

后台运行时可双击 stop-api.cmd 停止服务；脚本会检查端口进程属于本项目且没有运行任务。
