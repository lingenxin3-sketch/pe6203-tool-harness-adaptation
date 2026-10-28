# 追加两轮实验工作状态

目标与授权：执行 docs/追加实验/执行指南.md，原轮基础上最多追加两个独立主实验轮，不使用付费 API，不派子代理，不合并 main，不覆盖旧 Release。

仓库根目录为本文件父目录的父目录。原 main d471239f99f95f7c6aadcb8070852f293eb1b95b。当前专用分支 experiments/repeats-20261029。正式前准备状态已提交并从远端核对。后续 authoritative 状态见 runtime/repeats-20261029/state.json、实际进程及 docs/追加实验/状态.md。

## 保留的既有工作

dashboard/、scripts/start-dashboard.ps1、tests/test_dashboard.py、启动可视化.cmd 是先前未完成且未跟踪的可视化草稿。不要加入本次提交，也不要删除。旧 runs/final-v1、ablation-v1、final-workflow-verification 和 v1.0.0 不改写。旧 docs/WORK_STATE.md 含历史过程，不能当作当前活进程证据。

## 准备和执行

read-only preflight 已核对 162 条旧记录、四条失败收据、冻结核心、配置、八个依赖下载、三版 32388 个工具源码文件。收据 artifacts/repeats-20261029/preflight.json，compatible_preconditions=true。旧结果哈希冻结，阶段结束再次校验。

开发验证由 runtime/repeats-20261029/smoke.py 运行。新建 runs/repeat-smoke-20261029，仅任务3、不更新、三版，共3条，依次执行、原协议评分、原统计、审计、实际恢复跳过验证。通过后有 artifacts/repeats-20261029/smoke-verification.json。开发轨迹不计正式轮。

34 项相关测试：原核心22项、追加实验12项均已通过。新增测试日志 runtime/repeats-20261029/repeat-tests.log，最后一次元数据锁测试单独通过。没有运行或修补独立可视化草稿的测试。

运行中追加实际输入检查发现 Windows 路径长度影响资源文件名清单：部分策略比旧轮少显示1至2个PDF。原配置和源文件字节匹配不足以证明输入一致。见 artifacts/repeats-20261029/compatibility-alert.json。新增逐条资源清单比较和“同manifest但输入不同拒绝合并”测试，追加实验13项通过，总计35项。原轮和新增轮按严格标准分开报告，不产出324/486合并表。禁止为凑三轮重跑或再加第三个新轮。

旧管理进程 PID6104 载入的是仅比较manifest的旧发布逻辑；actor执行进程 PID4404 必须继续。通过 repeat_supervise_existing.py 先保留worker句柄并防睡眠，再只替换管理程序，持续等待同一worker自然退出；之后 --resume 跳过所有已保存actor记录，再评分发布。接管实际状态以 runtime/repeats-20261029/management-handoff.json 和CIM进程为准，不凭本段判断完成。

脚本职责：repeat_common.py 严格矩阵/可比性/指标；repeat_runner.py 恢复边界适配，首次使用原执行器，已保存不重跑，无结果残留目录阻止恢复；repeat_publish.py 白名单提交、远端逐文件核验、新Release及匿名下载哈希；repeat_campaign.py 控制逐轮执行、评分、发布门和15分钟状态发布。

只在 smoke 实际验证通过、分支和准备状态已远端核验、无其他推理进程时启动正式 controller。启动应隐藏后台窗口并记录 PID、日志。它运行期间持有与网页控制器共享的 runtime/dashboard/control.lock，且请求进程级防睡眠。Windows venv 可能显示父子两个 python 进程，不能误判重复启动。以实际 PID、命令行、子进程和输出为准，观察超时不表示进程停止。

## 后续操作与门槛

正式命令 .venv/Scripts/python.exe scripts/repeat_campaign.py。续跑必须先证明旧 controller/child 已终止，再审查 partial result 与日志，显式 --resume。controller 绝不自动清理或重试有 workspace 无 result 的条目。评分中断保留已评分，其他前提见冻结与故障协议。

第一新增轮 runs/repeat-r2-20261029，第二新增轮在启动前改为 runs/final-r3（与旧轮final-v1等长8字符）。原计划repeat-r3-20261029从未执行，不增加新轮。27组无模型的文件系统检查证明等长目录可恢复对应原轮的基准资源可见性，见 second-new-round-path-validation.json；实际第二新增轮仍需逐条核对。配置、模型、seed均不改。第一新增轮输入差异保留并单列，即使第二新增轮与原轮可比，也不发布含第一新增轮的486合并表。独立结果为 docs/追加实验/第2轮结果.md 和 第3轮结果.md。

第一轮发布门 runtime/repeats-20261029/repeat-r2-20261029-gate.json 只有在162评分、审计、新Release匿名下载哈希及最后状态commit远端核验均成功才产生。第二轮只有通过此前门槛才开始。发布失败则留真实状态并停止第二轮。12:00后第二轮若未启动，不自动启动，等待团队决定。

保持每15分钟进度发布，若机器/网络/认证失败不能保证08:00。检查 runtime/repeats-20261029/progress-publication-error.json 和 last-publish.json。不允许仅凭 state 文件判定存活，必须查看实际进程或exec句柄。新Release不能覆盖旧v1.0.0。最终只有486完整、评分、可比且远端证据均核验才报告三轮完成。
