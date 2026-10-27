# 最终提交与复现说明

本项目已完成 162 条主实验、6 条组件对照以及 9 条独立开发复现验证的执行与评分。最终结果和英文报告已经形成；提交包保留原始证据及已知局限。团队仍需填写真实成员信息、记录本人完成的工作并进行展示排练。

## 提交包包含什么

`scripts/build_submission.py` 会在完整性检查通过且最终报告存在时生成 `deliverables/PE6203_Project4_Submission.zip`。包内包含：

- 最终英文报告的 PDF 和可编辑 Markdown 源文稿。
- 三种策略的实现、固定配置、运行与分析程序、测试。
- 正式实验及组件对照的原始模型/工具记录、评分、结果表和实际生成的文件。
- 失败记录、校验摘要和评分校准的来源记录。
- 六人分工、逐任务核查、演示和复现指南。

包内不重复放入模型权重、工具服务器压缩包和每次实验未修改的原始资源。它们可以按 `REPRODUCTION.md` 的固定来源和校验值重新获取。最终 ZIP 会检查文件哈希和压缩完整性。

## 上传方式

课程允许 GitHub 仓库或 Google Drive 文件夹。最直接的方式是上传完整 ZIP，并在同一文件夹另外放一份最终 PDF，方便老师先读报告。若使用 GitHub，上传代码和文档，并将包含原始证据的 ZIP 放在仓库 Release 或明确链接的共享目录中。

开发目录中的 `.gitignore` 会排除体积很大的本地运行目录，不能因为代码推送成功就误以为原始实验记录也已上传。提交前应从老师能访问的链接下载一次 ZIP，确认报告、配置、记录和生成文件都能打开。不要只提交截图或汇总分数。

这些说明不会自动创建仓库、上传文件或发送给老师。

## 团队需要实际完成的部分

每个人按照 `TEAM_PLAN_ZH.md` 和 `TASK_REVIEW_GUIDE_ZH.md` 操作、检查或分析自己的部分，保留真实贡献记录。报告中的成员姓名、学号和个人贡献应按事实填写。AI 协助开发和写作的说明应保留，不应将自动生成的全部工作写成某位成员独立完成。

## 重新生成报告 PDF

报告渲染工具与实验模型环境可以分开安装。下面是可选的独立报告环境；已有最终 PDF 的读者无需安装。

```powershell
python -m venv runtime/report-venv
runtime/report-venv/Scripts/python.exe -m pip install -r requirements-report.txt
runtime/report-venv/Scripts/python.exe scripts/render_report.py docs/REPORT.md output/pdf/PE6203_Project4_Report.pdf
```

修改结果或文字后，必须重新检查 PDF 的全部页面，尤其是表格、分页和结论与数字的一致性。正式统计尚未完成时，不应把预览稿改名后当作最终报告提交。
