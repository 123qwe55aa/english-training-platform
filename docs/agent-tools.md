# Codex 教学操作入口

现已提供可发现的 JSON 工具、可预览的写操作、请求去重、旧版本覆盖保护和教师可见的操作记录。通过现有 SSH 身份调用，不新增公网写入接口。网页聊天助手不在此版本范围内。

## 日常使用

在 Codex 中使用 `$english-teaching-platform`，直接描述任务，例如：

- 查看某位学生已完成哪些课，为下一次课备课，先保存草稿。
- 把这份绘本整理成台词、对话和选择题，加入指定教材并分配给某个学生。
- 今天某月某日 Day N 已授课；记录实际表现，按你提供的依据发 10 点奖励。

Skill 源码在 `skills/english-teaching-platform/SKILL.md`，安装副本在用户 Codex skills 目录。新会话可发现该 skill；当前会话也可直接读取并使用工具。

## 工具

| 工具 | 功能 |
|---|---|
| students.list / students.get | 学生资料、分配课程、实际进度、近期教案及课堂证据 |
| students.save | 新建／修改学生、课程分配、计划和奖励规则 |
| courses.list / courses.save | 查询／新建／修改课程 |
| materials.get / materials.import | 查询完整教材；创建小课或追加内容块，保留原 VOA 数据 |
| sessions.get / sessions.prepare | 查询教案；创建／修改符合模板的一小时课堂 |
| sessions.progress | 依据教师确认更新授课状态、实际日期与掌握证据 |
| rewards.award | 按实际日期和依据发奖，或以负数更正 |
| operations.list | 查询教师私有的操作历史、请求结果 |

CLI：从仓库根目录运行 `python3 scripts/teaching_agent.py tools` 返回完整参数 schema。`call 工具名 --args 参数.json` 查询，`request --input 请求.json` 执行完整请求。`upload 本地文件` 返回可用于教材导入的上传句柄。

写请求格式：

```json
{
  "tool": "students.save",
  "arguments": {"fields": {"name": "New student", "planned_sessions": 24}},
  "request_id": "a-unique-stable-event-id",
  "apply": false
}
```

默认仅预览。核对后将 apply 改为 true，复用同一请求编号。修改已有资料还需 expected_revision，从对应 get 工具返回值读取。学生、课程、教材、课堂的版本不能混用。预览产生的新增 ID 是临时值，最终以提交结果为准。

网络超时后查询 operations.list 或重发同一编号与参数，避免重复发奖。不同参数不能复用已提交编号。版本冲突必须重新读取并协调修改。后台「Agent 操作记录」可查请求、修改前后及结果；界面不提供编辑或删除操作。

## 教材与备课边界

本版支持上传与结构化导入。Codex 在本地阅读／整理 PDF、Word 或网页材料，再发送文字、媒体、对话、Quiz 内容块；服务器不自动用 LLM 生成教案。媒体链接本身不会自动下载。现有 VOA 抓取／导入脚本仍可使用。

文件流式上传至非公开暂存目录，句柄不可替换为服务器文件路径；导入复用后台文件验证。失败或预览会清理新建的正式媒体，成功提交后删除暂存文件。未使用或失败的暂存文件仍留在私有目录，需定期清理；它们不属于已导入教材，未纳入课程媒体备份。

备课接口要求前一天实际教过的 5–6 个回顾句（第一天除外）、目标、表达卡、合计 60 分钟的流程、B 方案和出口检查。Codex 按 vault 模板补齐课前回顾与课后总结。准备教案不会自动标记已授课。

进度和奖励都要求教师提供事实依据；不会根据访问量推断口语水平。新建内容默认不公开，学生、课程、小课、内容块均发布并完成课程分配后才对学生可见。自动练习积分仍在浏览器，教师发奖及授课进度存于服务器。

学生查询同时返回 recorded_progress（包括未公开已完成课堂）与 progress（学生公开页面上的进度），备课时以真实记录为依据，避免把未公开课堂误当未授课。
