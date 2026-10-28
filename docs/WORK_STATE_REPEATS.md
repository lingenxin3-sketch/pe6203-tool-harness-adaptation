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

第二新增轮路径预声明门也已测试通过，目前相关测试总计36项。等长路径文件系统验证可用 scripts/repeat_validate_path.py 复现，仅创建和清理自己新建的8字符临时测试目录，不调用模型。该测试27个布局均通过；真实第二新增轮仍需逐条核验输入。

随后增加了证据包日志保留测试并通过，目前相关测试总计37项。repeat_publish.package 保留失败案例工具stderr及已结束的每轮execution/scoring/summary日志，不将仍在写入的全局模型服务日志当作完整附件。

旧管理进程 PID6104 载入的是仅比较manifest的旧发布逻辑；actor执行进程 PID4404 必须继续。通过 repeat_supervise_existing.py 先保留worker句柄并防睡眠，再只替换管理程序，持续等待同一worker自然退出；之后 --resume 跳过所有已保存actor记录，再评分发布。接管实际状态以 runtime/repeats-20261029/management-handoff.json 和CIM进程为准，不凭本段判断完成。

脚本职责：repeat_common.py 严格矩阵/可比性/指标；repeat_runner.py 恢复边界适配，首次使用原执行器，已保存不重跑，无结果残留目录阻止恢复；repeat_publish.py 白名单提交、远端逐文件核验、新Release及匿名下载哈希；repeat_campaign.py 控制逐轮执行、评分、发布门和15分钟状态发布。

只在 smoke 实际验证通过、分支和准备状态已远端核验、无其他推理进程时启动正式 controller。启动应隐藏后台窗口并记录 PID、日志。它运行期间持有与网页控制器共享的 runtime/dashboard/control.lock，且请求进程级防睡眠。Windows venv 可能显示父子两个 python 进程，不能误判重复启动。以实际 PID、命令行、子进程和输出为准，观察超时不表示进程停止。

## 后续操作与门槛

正式命令 .venv/Scripts/python.exe scripts/repeat_campaign.py。续跑必须先证明旧 controller/child 已终止，再审查 partial result 与日志，显式 --resume。controller 绝不自动清理或重试有 workspace 无 result 的条目。评分中断保留已评分，其他前提见冻结与故障协议。

第一新增轮 runs/repeat-r2-20261029，第二新增轮在启动前改为 runs/final-r3（与旧轮final-v1等长8字符）。原计划repeat-r3-20261029从未执行，不增加新轮。27组无模型的文件系统检查证明等长目录可恢复对应原轮的基准资源可见性，见 second-new-round-path-validation.json；实际第二新增轮仍需逐条核对。配置、模型、seed均不改。第一新增轮输入差异保留并单列，即使第二新增轮与原轮可比，也不发布含第一新增轮的486合并表。独立结果为 docs/追加实验/第2轮结果.md 和 第3轮结果.md。

第一轮发布门 runtime/repeats-20261029/repeat-r2-20261029-gate.json 只有在162评分、审计、新Release匿名下载哈希及最后状态commit远端核验均成功才产生。第二轮只有通过此前门槛才开始。发布失败则留真实状态并停止第二轮。12:00后第二轮若未启动，不自动启动，等待团队决定。

保持每15分钟进度发布，若机器/网络/认证失败不能保证08:00。检查 runtime/repeats-20261029/progress-publication-error.json 和 last-publish.json。不允许仅凭 state 文件判定存活，必须查看实际进程或exec句柄。新Release不能覆盖旧v1.0.0。最终只有486完整、评分、可比且远端证据均核验才报告三轮完成。

## 2026年10月29日0321续接快照

第一新增轮实际运行中，已落盘132/162，评分0，执行异常4。此数仅为带时间戳的快照。actor PID4404（创建于00:34:09）从未重启；旧管理PID6104已在00:57由接管脚本结束，监管PID41868（父33500）持续等同一actor完成。03:21已通过CIM再次核实两者存活。不要启动第二份controller，不要对活进程执行 --resume。

只读观察会话 exec session99236 在等原actor的Windows进程句柄，每50秒输出计数；它不是实验或模型。可继续 write_stdin 轮询该会话。若会话丢失，先用完整CIM查询PID4404、41868及当前state所载PID；受限进程视图可能看不到活进程，不能据此认定停止。若观察仍超时，重查同一进程，不重跑。

监管进程在原actor自然退出且exit code为0后，会自动启动修正后 repeat_campaign.py --resume，跳过所有已保存actor记录，然后整理失败、评分、审计及发布。新controller可能为venv父子两个python进程，运行信息在 controller-continuation.stdout.log、controller-continuation.stderr.log、management-continuation.json。原actor执行日志仍为 repeat-r2-20261029-execution.log。模型切换和已完成记录跳过都是已授权工作，不需要再次询问许可。

截至快照的四条异常：full_rewrite/iter5/117、selective_patch/iter5/117、no_update/iter3/389、full_rewrite/iter5/389。只读重建均成功，分别有8、16、6、6条消息，未应用或重跑，原始哈希在 r2-live-failure-review.json。正式执行结束后使用原finalize程序创建failure-record.json并保留execution_status，再按原协议评分。若新的异常缺少一致轨迹则真实停在不完整状态，不能伪造分数。

模型启动收据 actor-runtime.json 可能会在后续切换被更新，已将00:34的首轮actor原收据按字节复制到 r2-actor-start-runtime.json，哈希9b0d42d4554b610347502c1898f820490ff0453b5d11588f376257ee1d01793f。评分和第二新增轮启动时也应保留每轮独立的模型启动收据，不能把后来的收据误称为前一轮启动状态。

03:20自动发布已远端核验，未见发布错误。当前还没有新轮最终分数或新Release。第一新增轮存在资源可见性混杂，原轮与它不可严格合并；第二新增轮尚未启动，已预声明final-r3等长目录并完成27组无模型检查，但实际输入仍要在运行后核对。即使最终有486条已评分记录，也不能把不兼容轮硬合并成三次可比实验。

## 2026年10月29日0417阶段切换快照

原actor PID4404在04:14自然退出，已通过保留的Windows进程句柄核实exit code=0；只读观察会话99236已正常结束，不再轮询它。监管程序自动启动 --resume 管理程序，实际Python管理PID40048、venv启动器PID39668，创建于04:14:34。现已进入scoring，评分子进程记录PID17588。不要启动第二份管理器或评分器。runtime/repeats-20261029/management-continuation.json、state.json、controller-continuation.stdout.log/.stderr.log为本阶段现场信息。

第一新增轮162条全部落盘，execution-audit.json无issues且recorded_invariants_pass=true；评分尚未全部完成，不能称整轮完成。异常共5条，新增full_rewrite/original/416，留下10条消息。五条failure-record.json已按此前原始哈希逐条验证保留，见r2-failure-preservation-verification.json。它们按已有轨迹评分，不重跑。第二新增轮final-r3此时未创建，发布门也未产生。

完整162条输入检查发现123条可见资源文件名清单与旧轮不同（full_rewrite52、no_update17、selective_patch54），没有缺失输入检查。见r2-input-compatibility-final-execution.json。第一新增轮不可与旧轮严格合并，且组内策略有输入可见性混杂，不把所有分数差异归因于策略。较长6条离线评分长度预查最大预留17261<固定容量24576，属于非穷尽检查，正式评分逐条精确容量检查仍为准；见r2-late-long-trace-context-check.json。

本轮judge在04:15:44核验，原模型、24576容量；独立原字节收据为r2-judge-start-runtime.json及r2-judge-runtime-preservation.json。第二新增轮后续actor/judge也须及时保留独立运行收据，不能让全局actor-runtime.json或judge-runtime.json后写版本冒充前轮。

新只读观察会话exec session46604运行runtime/repeats-20261029/wait_campaign.py 40048，保留当前管理进程句柄，每50秒打印两轮真实found/scored/failures及发布回执时间。它不执行实验、不启动模型。后续用write_stdin轮询此会话，单次等待50秒；若会话丢失，先从完整CIM进程视图确认40048及其子进程和当前state，不能因受限观察或等待超时就恢复或重跑。第一轮评分齐备后仍需审计、独立结果、打包、新Release匿名下载SHA和最终commit远端核验，门通过后才启动final-r3。当前尚无新Release。

## 2026年10月29日0540阶段交付快照

**第一新增轮已完成并核验交付。** runs/repeat-r2-20261029为162条执行、162条有效评分、5条执行异常；全量audit无issues，recorded_invariants_pass和complete_and_evaluated均为true。执行约00:34至04:14，评分04:15至05:35；这些是约数墙钟时间，不是模型请求秒数相加。

第一新增轮发布门在05:37:57实际通过，最终阶段提交e7186eaed5f8206a813ec317381026fbddafae3a，Release为repeat-r2-20261029-evidence，公开ZIP为29,696,677字节，SHA-256为9c2c963d0b8fa02267a87034a398672442a10424f22dae81a4298587f137fceb。实际匿名下载后独立核对867个清单条目的哈希及CRC，内含162份result、162份agent-record、162份events及5份failure-record；27条重点案例的已评分文件哈希与公开核查索引一致。独立归档/远端复核收据为r2-independent-archive-verification.json及r2-independent-remote-verification.json，已实际核对GitHub分支提交、结果页Git blob和Release资产digest。门文件runtime/repeats-20261029/repeat-r2-20261029-gate.json存在。

本轮ECS（原自动评分）为不更新5.982999、全部重写5.611179、选择性更新4.597480；选择性更新这轮不是最高。更新token为104413对36449，节省65.1%；三阶段合计token为全部重写3063088、选择性3321519，后者高8.4%。123条输入资源清单与旧轮不同，并有策略间输入混杂，所以本轮独立报告，不作整体成本或质量的严格因果结论，也不发布含它的324/486合并结论。2-round-combination-refused.json保留拒绝依据。

任务28、113、117共27条完成评分和原件对照，原始字节及执行关键字段均验证一致；见r2-case-postscore-review.json及docs/追加实验/第一新增轮案例核查.md。任务117全部重写Middle、Late有明确评分与实际失败分歧，Late异常、回答为空却TF/PE均10；任务113不更新Late七次规划校验失败，本轮TF1/PE4，与旧轮同类高分不同。任务28全部重写Middle的TF6/PE5识别了部分失败。报告这些具体事实，不能笼统声称全部评分有效或无效，不改分、不把满分解释实际成功。review始终标AI协助、成员独立复核待完成。

第二新增轮final-r3已在05:38:09开始，晚于首轮发布门通过。实际管理PID40048（venv启动器39668）；执行启动器PID37256、实际Python子PID36868，已于05:39完整CIM核对。不要重复启动。actor运行收据已独立保存r3-actor-start-runtime.json及r3-actor-runtime-preservation.json，固定容量16384，原模型不变。只读观察会话仍为46604，它现在同时输出R2和R3计数。05:39时R3已落盘5条、0评分、0异常，首批5条实际资源清单与旧轮一致，仅是部分检查，不能提前称整轮可比。见r3-first-input-check.json。

接下来继续等待同一R3执行进程完成；出现异常时只读assemble审查真实轨迹，保留，不重跑；管理器会自动finalize、审计、切换原judge、评分和发布。R3评分实际开始时须及时保存独立r3-judge-start-runtime.json，不能复制目前仍留存的R2全局judge收据。最终需再次独立核对R3的162条及失败、实际输入可比性、Release匿名下载SHA和远端提交，并核查两次阶段交付顺序、旧结果/主分支保留、无强制486合并。即便R3与旧轮可比，含R2的三轮汇总仍禁止；最多两个新增轮，不再补第三个新轮。

R2结果页追加了成本解释和本轮27条案例链接；独立复核收据、R3启动/首批输入收据及本段文字将由下次15分钟心跳发布。不要把尚未从last-publish.json确认的补充文件称为已远端核验。GitHub文本CRLF转LF与原始ZIP字节的SHA区别，已经实际核对并记录在冻结与故障协议中。

runtime/repeats-20261029/case_score_table.py是本次一次性只读提取及原件验证脚本，已在27条案例全部评分后成功生成公开JSON和表格；不要重复执行覆盖输出，也不要算作新实验。旧Word/PDF/演讲材料和依赖扩展组件对照仍是旧单轮版本，尚未同步更新；没有新增PPT或替团队提交课程。

05:48在R3尚未评分时补充了对照口径预声明：如R3全部评分且与原轮严格可比，可另提供明确名称的“原轮final-v1＋第二新增轮final-r3”324条、每组合2次的对照和配对差，R2继续独立；不得把它说成3次或486可比，也不能按成绩选择纳入轮次。当前campaign.aggregate_views会因R2而拒绝全三轮，额外的原轮/R3视图须在最终核验后用merge_views([old,r3])并逐条来源哈希实现，不能改原记录。若R3不满足严格可比性，则不生成该对照。依据为评分前已发现的输入差异，非结果选择。见冻结与故障协议最后一节。

05:52续接补充：第二新增轮31/162条落盘、0评分、0异常，同一管理40048与执行37256/36868继续，观察会话46604仍活跃；不要因本次阶段交付回复就停止当前实验，也不要新启动副本。05:50:11进度提交0da9583cdb8b1143ed06c78b0b88ec46a74a4e02已逐文件远端核验，包含R2成本补充、独立归档与远端复核收据、R3actor独立收据和预先声明的对照口径。05:51:41实际检查到28条R3输入资源清单，全部与旧轮一致，见r3-first27-input-check.json（达到27条检查点时实际已增至28，文件内记录真实28）；它仅为部分核验、尚未随下一次心跳发布，不称整轮可比。

## 2026年10月29日0626续接快照

R3正在同一进程执行，06:25实际64/162条、0评分、2条执行异常；管理PID40048及只读观察会话46604仍在工作。没有重跑任何episode。下一步先续同一write_stdin会话；不要启动新controller或模型，也不因一次等待超时判断停止。当前是有具体进程句柄证明的等待，同时完成了下列新证据工作，非阻塞。

新增docs/追加实验/第二新增轮案例核查.md，以及r3-case-execution-review-receipt.json（现27条、cases=[28,113,117]、complete_case_matrix=true，仅指案例子集）。这些案例在评分前完成逐条读取，记录原始result字节SHA、实际文件SHA、调用及搜索返回。任务28/113旧18条原件和实际产物在加入117时再次校验未变；r3-case-event-freeze.json再冻结27条的事件日志SHA。后续评分完成要用这些原始SHA核对normal的agent-record.json、异常的failure-record.json，并核对事件不变，再补原自动分数表；不要直接复用硬编码R2路径的一次性case_score_table.py。

任务28：不更新三版、全部重写Early、选择性更新三版共7条真实创建任务Markdown，各3个未勾选待办；路径有anotation_path/markdown/tasks.md、markdown/tasks.md、txt/tasks.md。全部重写Middle相关契约未改却重写3说明，随后虚构source_id_1、两次拿txt日志初始化来源，3次错误、无文件。选择性更新Late4次调用中第一次添加缺来源失败，后初始化txt/tasks.md取得真实编号再添加成功，有恢复但多一次失败步骤。多数文件仍把昨天数据库错误断言为未解决，两份日志不支持该断言；今天无该报错也不证明已经解决。selective Late有核实历史故障措辞，不能笼统说所有内容相同或全错。

任务113：root tasks.json结构是requests数组内嵌tasks，不能只读顶层tasks（那会误数0）。根计划任务数依次为不更新5/5/无、全部重写5/无/5、选择性更新5/6/6；所有done/approved=false。全部重写Middle另一个.agentic-tools-mcp/tasks/tasks.json有4条pending、subtasks为空，不能说没有计划。不更新Late7次规划均缺priority/tags等必填字段，8个工具调用、7错误，没有root计划；selective Middle仅2个工具调用、6个计划任务，未创建另一套项目，不混淆工具族的前置条件。

任务117：九条模型轮数/工具调用数/真实Shrimp任务数为no_update Early12/12/0、Middle12/12/0、Late12/12/5；full Early12/12/0、Middle12/12/0、Late3/3/0；selective Early3/3/0、Middle10/8/6、Late12/22/0。只有selective Middle有非空最终回答。12步指模型决策，22个工具调用未违反12轮上限，不能据此造假定性。full Middle三次split_tasks正文为JSON非法控制字符错误，isError却false；实际无Shrimp任务文件，必须区分MCP错误标记和语义失败。

R3目前两条异常为full_rewrite/iter5/117（原始SHA c3d375a4b91e38db5888f8624c2d6d522916b847a2551cf108bdf6c62275fd4a）与selective_patch/original/117（1331d7b8ea8857f54e51bc4fff95a5e4aac002ba47b3130c70e389d27e4fbed1）。两者均8条可只读重建消息、回答为空、split返回未闭合字符串，无任务文件；未应用finalize、未重试。见r3-live-failure-review.json；后续若有新异常更新只读检查。selective Early的adaptation.status=initial，在更新前异常，不能归因于选择性更新。

本轮117并非所有搜索都报错：no_update Late注册了基准work.md（工作方法指南）后用真实来源ID查询，正常返回空数组；没取到历史交通任务，不能说已找到可复用经验。full Middle最后注册了work.md但未再查询。selective Middle两次把真实Shrimp任务UUID当成另一套工具的source_id，已实际核对两次UUID均属其任务列表，两次来源不存在。其余档案搜索失败或未调用，细节在27条receipt中；不能复制R2“没有有效查询”的事实到R3。

新增within-round-input-fairness-check.json，实际检查旧轮54个同题同版本的跨策略组全部资源清单一致，R2的54组全部不同，R3当时完整的12组一致。R2的输入混杂已量化，不只跨轮不匹配，策略间也不公平；严格独立报告，不作ECS差异因果归因。R3这一份仍是部分检查，末尾必须更新核验全部54组，再核实old/R3全部162输入匹配及运行judge条件。

06:22:13实际进度提交ee1940681f0710e393ea5a90cadcafbf62cc2037远端逐文件核验，公开R3案例receipt当时仅[28,113]共18条，任务117补充及27条事件冻结在06:23以后生成，尚待下一心跳公开，不能误称已上传。持续15分钟发布，注意last-publish.json及publication-error日志。原来R2已完成的证据、提交、费用和限制仍如上，不动原轮、main、旧v1.0.0或无关可视化草稿。

后续R3自然完成执行时管理器会整理失败、审计、切换原judge评分、统计及发布新Release。评分实际开始后及时独立保存r3-judge-start-runtime.json，不要提前复制仍属于R2的global judge-runtime.json。完成后独立下载校验R3ZIP全部162来源、失败和日志，远端核验commit/结果页；审查27条原分数与已核对事实，不改分；若old/R3严格可比，再按已预声明的原轮+第二新增轮324视图提供两次对照，保留R2独立且不称486可比。完整目标尚未完成，不更新goal为complete，也不是blocked；继续至第二轮实际评分发布验证及最终要求逐项审计。

## 2026年10月29日0641续接补充

同一controller40048及观察会话46604继续，06:39实际R3落盘72/162、评分0、异常2；现属有实际进程句柄的等待，非阻塞。06:38:16的公开提交742e9e9ad59dcaa5ed0e7c6f61afc0828fe1d29a已逐文件远端核验；06:40:52还独立通过GitHub API读回27条r3-case-execution-review-receipt.json、27条r3-case-event-freeze.json及第二新增轮案例核查.md，与commit Git blob逐字节一致。见r3-case-publication-verification.json。现在27条案例及117补充确实已公开，不能再沿用06:22仅18条的旧快照。该独立核验收据本身将由下次心跳上传。

已准备runtime/repeats-20261029/case_score_table_r3.py并通过语法编译，尚未实际执行。仅当27条选定案例全部按原协议评分后运行（通常全局评分到154条左右），它会先核对27个事件文件SHA、早期实际Markdown/JSON产物SHA、原件字节（正常用agent-record、异常用failure-record）及actor/update调用，再生成r3-case-postscore-review.json并向第二新增轮案例核查.md追加原TF/PE表，绝不重评分。它在未评分或已有输出时拒绝写，不要提前运行或覆盖。准备阶段一次外层PowerShell引号错误已改为apply_patch，编译复核成功，没有执行模型或更动任何实验输出，不能把它计为实验失败。

最终如生成已预声明的old+R3两轮视图，merge_views中的cohorts.n是观测数之和；需另标distinct_tasks（沿用单轮该组人数）和n_observations，不把两个重复当新增独立任务。ECS中跨版本的总体标准差与跨轮均值的样本标准差须区分，n=2不作显著性或普遍优越结论。R2继续独立，整轮总token比full多8.4%的不利结果照样保留。不要为了更好结果再加第三个新轮、改seed、提高上下文或改动原评分。
