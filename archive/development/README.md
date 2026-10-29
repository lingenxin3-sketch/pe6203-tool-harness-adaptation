# 早期开发材料归档

这两份是原开发阶段的历史原件，不是当前正式实验配置或运行入口。内容按原样保留。

`development-task101.json`保留旧4B评分模型设置；正式配置使用`configs/experiment.json`及独立7B judge。`run_pilot.py`是任务3的早期单例脚本，原来的相对目录假设不适用于此归档位置，不从这里执行；当前开发运行与正式复现均见[复现说明](../../docs/REPRODUCTION.md)。

| 原位置 | 归档位置（相对此目录） | 原Git blob SHA |
|---|---|---|
| `configs/development-task101.json` | [configs/development-task101.json](configs/development-task101.json) | `c78e1d2319dcc3ba08f2d29d0921f098fbfc26da` |
| `scripts/run_pilot.py` | [scripts/run_pilot.py](scripts/run_pilot.py) | `716934cda885f9a2d36fea14687b856518f1baf5` |

迁移清单记录原Git blob SHA与本机字节SHA-256，两者的算法及换行口径不同。归档不表示这些证据无效，也不增加新的实验观测。
