# E · LIN GENXIN：失败案例与评分核查

负责人：**LIN GENXIN**。本板块核对工具调用、返回正文、实际产物与自动评分，区分工具知识更新问题、AI操作错误、工具/资源问题及评分误判。

## 案例与分析

| 案例 | 分析重点 | 完整材料 |
|---|---|---|
| 任务113 | 新必填参数未更新导致规划注册失败；区分计划保存与实际实现 | [原轮案例](../../../docs/CASE_113_REVIEW.md) |
| 任务28 | 未变工具说明被重写后出现操作退化；区分关联证据与确定因果 | [原轮案例](../../../docs/CASE_28_REVIEW.md) |
| 任务117 | 异常、拆分或检索失败却获高分；核对返回正文与任务存储 | [原轮评分分歧](../../../docs/CASE_117_JUDGE_REVIEW.md) |
| 两轮新增 | 重点案例、原评分、真实文件及执行异常的逐条对照 | [第一新增轮](../../../docs/追加实验/第一新增轮案例核查.md) · [第二新增轮](../../../docs/追加实验/第二新增轮案例核查.md) |

## 核查工具

| 文件 | 用途 |
|---|---|
| [demo_evidence.py](../../../scripts/demo_evidence.py) | 回放已保存的调用和产物，不调用模型生成新结果 |
| [check_saved_artifacts.py](../../../scripts/check_saved_artifacts.py) | 检查重点案例的真实文件保存情况 |
| [inspect_tool_errors.py](../../../scripts/inspect_tool_errors.py) | 定位MCP标记错误与结构化返回错误 |
| [finalize_failed_episodes.py](../../../scripts/finalize_failed_episodes.py) | 从已有事件保存失败轨迹供评分，不重试任务 |
| [test_failure_accounting.py](../../../tests/test_failure_accounting.py) | 验证失败保留与证据一致性边界 |

## 证据范围

完整负责文件见[FILE_LIST.md](FILE_LIST.md)。`artifacts/repeats-20261029/`内的案例索引、评分后核查与失败保存收据提供对应来源；`artifacts/incidents/`保留原运行故障和恢复凭据。它们是项目证据，不单独证明成员个人完成了独立核查。

现有案例保留原自动分数，并使用真实调用、返回和产物说明分歧。工具返回未标错误不等于动作成功，文件存在不等于内容正确，保存计划也不等于已交付实现。

个人工作记录与results文件的状态以其实际内容为准，未完成模板不计入正式核查结论。
