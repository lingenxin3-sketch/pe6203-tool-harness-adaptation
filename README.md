# 企业AI工具更新与能力保持

PE6203 Group Project4：在MCPEvol-Bench的工具环境升级后，比较不更新、全部重写、选择性修补三种工具知识策略。系统更新工具契约和用法说明，基础模型权重不变。

企业AI使用的工具改变后，旧参数或旧规则可能导致调用失败。我们检测公开工具接口的变化，只为受影响及明确关联的工具重新生成说明，再让同一个AI执行任务，保存调用、返回、文件和评分，以评估恢复、保持与更新开销。

## 报告与结果入口

- [最新完整报告PDF](output/pdf/PE6203_Project4_Final_Report.pdf) · [报告源文稿](docs/REPORT.md)。
- [三轮结果与证据索引](docs/追加实验/交付与核验.md)。
- [原轮与第二新增轮的可比对照](docs/追加实验/原轮与第二新增轮对照.md)。
- [安装与复现](docs/REPRODUCTION.md) · [课程要求与证据对应](docs/REQUIREMENTS_EVIDENCE_ZH.md)。

## 仓库结构

| 目录 | 内容 |
|---|---|
| `tool_adapt/` | 共用AI执行循环、MCP工具连接、工具知识更新与指标聚合 |
| `scripts/` | 下载、运行、评分、结果核查、复现和交付工具 |
| `configs/` | 冻结实验配置及评分容量设置 |
| `tests/` | 知识更新边界、协议、失败保存和打包等测试 |
| `artifacts/` | 工具清单、结果数据、故障证据与核验收据 |
| `docs/` | 方法、完整报告、失败案例与复现说明 |
| `output/pdf/` | 最新报告与原单轮历史报告 |
| `contributions/` | 实名责任表、负责文件索引与个人成果目录 |
| `archive/` | 已分类保存的历史开发材料和中途快照 |

## 方法

| 策略 | 工具环境改变后如何处理 |
|---|---|
| 不更新 | 保留Early工具契约和用法说明 |
| 全部重写 | 复制当前工具契约，重新生成全部范围内的说明 |
| 选择性修补 | 复制当前契约，只重写变化及明确关联的说明，保留其他说明 |

两种更新策略使用相同模型与校验规则。参数结构直接来自当前公开接口；更新模型不接收任务答案、参考轨迹、变异标签或评分。依赖扩展依据工具名称的明确引用，不能保证识别全部隐含操作顺序。

## 实验结果

每轮使用相同18个任务、3种策略、3个版本，共162条；三轮已评分486条，全部执行异常保留。

| 轮次 | 已评分 | 执行异常 | ECS：不更新 / 全部重写 / 选择性修补 |
|---|---:|---:|---|
| 原轮final-v1 | 162 | 4 | 6.280 / 5.239 / 6.332 |
| 第一新增轮repeat-r2-20261029 | 162 | 5 | 5.983 / 5.611 / 4.597 |
| 第二新增轮final-r3 | 162 | 5 | 4.929 / 5.340 / 6.152 |

第一新增轮存在123条跨轮资源清单差异和54组策略间输入差异，单独报告。只有原轮与第二新增轮按已披露条件作324条描述性对照：18个不同任务，每个任务/策略/版本组合两次。

可比两轮中，选择性修补ECS均值为6.242，不更新5.605、全部重写5.289。选择性修补比全部重写少用65.1%的**更新token**，但更新、执行和评分三阶段已记录总token反而多5.6%。这些结果不证明总成本下降或任务效果普遍更好。Early尚未更新就有分数差异，且自动评分有已保存的误判；实际完成情况需结合工具返回和文件判断。

## 团队分工

| 板块 | 成员 | 负责内容 | 资料入口 |
|---|---|---|---|
| A | SU YANG | 执行系统与工具调用 | [查看](tool_adapt/agent.py) |
| B | LIU ZHEYUAN | 工具知识与选择性修补 | [查看](tool_adapt/knowledge.py) |
| C | HE YUJIE | 实验设计与复现 | [查看](configs/experiment.json) |
| D | SHISHUYI | 指标、恢复保持与成本 | [查看](artifacts/final-report-data.json) |
| E | LIN GENXIN | 失败案例与评分核查 | [查看](contributions/members/E_LIN_GENXIN/README.md) |
| F | PAN JUNKUN | 报告整合与交付一致性 | [查看](docs/REPORT.md) |

完整责任索引见[contributions](contributions/README.md)。分工表说明板块责任，个人实际完成情况以相应成果记录为准。

## 复现与原始证据

Actor/updater使用Qwen3-4B-Instruct-2507 Q4_K_M，judge使用Qwen2.5-7B-Instruct Q4_K_M，通过llama.cpp b11900本地运行，无付费API。基准固定为`888c779a0fe735f612ca62bdd1fdd7c9e6bf8701`；模型、依赖和运行命令见复现说明。

完整运行目录和模型权重不放入源码树。原始执行、调用、产物、评分及失败分别保存在[原轮Release](https://github.com/lingenxin3-sketch/pe6203-tool-harness-adaptation/releases/tag/v1.0.0)、[第一新增轮Release](https://github.com/lingenxin3-sketch/pe6203-tool-harness-adaptation/releases/tag/repeat-r2-20261029-evidence)、[第二新增轮Release](https://github.com/lingenxin3-sketch/pe6203-tool-harness-adaptation/releases/tag/final-r3-evidence)，哈希与核验入口见最终结果页。

原单轮PDF、结果表和图作为历史版本保留。固定seed与temperature=0的重复不构成显著性证据；成本只统计已返回并保存用量的调用，API零计费不含硬件、电费与开发成本。

## 来源

官方基准：[MCPEvol-Bench](https://github.com/Octobrist/MCPEvol-Bench)。本项目的代码开发、文档和证据整理使用AI协助，原始实验数据、失败和评分均保留供核查。
