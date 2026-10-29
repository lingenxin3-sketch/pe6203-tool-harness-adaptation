# 团队分工与资料索引

本项目采用统一代码与实验目录，各成员负责对应板块的实现、核查、分析或交付。以下为责任分配表；共同基线的来源与AI协助说明见项目首页。

| 板块 | 成员 | 负责内容 | 主要文件或资料 |
|---|---|---|---|
| A | SU YANG | 执行系统与工具调用 | [查看](../tool_adapt/agent.py) |
| B | LIU ZHEYUAN | 工具知识与选择性修补 | [查看](../tool_adapt/knowledge.py) |
| C | HE YUJIE | 实验设计与复现 | [查看](../configs/experiment.json) |
| D | SHISHUYI | 指标、恢复保持与成本 | [查看](../artifacts/final-report-data.json) |
| E | LIN GENXIN | 失败案例与评分核查 | [查看](members/E_LIN_GENXIN/README.md) |
| F | PAN JUNKUN | 报告整合与交付一致性 | [查看](../docs/REPORT.md) |

## 文件与成果位置

- [ownership.json](ownership.json)：当前整理分支的完整文件责任映射。
- 核心代码、配置、测试、报告与实验凭据均保留原项目路径。
- `members/`保存已导入成员的个人资料和工作记录；文件状态以实际内容为准。
- [LIN GENXIN的E部分](members/E_LIN_GENXIN/README.md)：失败案例、真实产物与评分核查。

## 项目材料

- [系统与仓库总览](../README.md)。
- [完整报告PDF](../output/pdf/PE6203_Project4_Final_Report.pdf)。
- [正式案例与逐项核查](../docs/追加实验/第二新增轮案例核查.md)。
- [实验结果、来源与原始证据索引](../docs/追加实验/交付与核验.md)。

不同板块共用同一模型设置、任务和实验协议。历史收据、原分数和失败原件保留，不将个人资料目录中的草稿或模板计作已经完成的独立核查。
