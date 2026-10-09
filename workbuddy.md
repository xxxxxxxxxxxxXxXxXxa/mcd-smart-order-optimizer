# workbuddy.md — WorkBuddy 开发上下文

> 本文件用于核验本参赛项目是否真实使用腾讯 WorkBuddy 智能体开发，符合「麦当劳程序员创意开发大赛」WorkBuddy 专项奖励条件。

## 一、开发环境

- 智能体：腾讯 WorkBuddy（Agent 模式）
- 开发方式：全程由 WorkBuddy 完成「调研规则 → 方案设计 → 编码 → 单测 → 文档 → 发布准备」
- 工程目录：`mcd-smart-order-optimizer/`
- 运行环境：Python 3.13（WorkBuddy 托管运行时），仅标准库，无第三方依赖

## 二、开发过程记录

### 阶段 1 · 规则调研（Web 检索 + 文档解析）
- WorkBuddy 抓取并解析了活动推文与官方仓库 `M-China/mcd-developer-innovation-challenge`，
  提炼出必交文件清单：`README.md` / `CONTEST_DECLARATION.md`（原样）/ `MCP_INTEGRATION.md`
  / `mcp-config.example.json` / `workbuddy.md` + 源代码；并确认**排名只看 Star 数**、10/26 00:00 定榜。
- 解析 `M-China/mcd-mcp-server`，整理出麦当劳 MCP 工具清单与接入方式（Streamable HTTP + Bearer 鉴权）。

### 阶段 2 · 方案设计
- 确定差异化定位：不止「点餐助手」，而是「多目标优化决策层」。
- 设计三种模式：**省钱 / 营养达标 / 积分策略**，并定义可单测的纯算法 `src/optimizer.py`。

### 阶段 3 · 编码
WorkBuddy 直接编写并落盘以下文件（均未人工干预）：
- `src/optimizer.py`：用券计算、组合枚举打分、积分价值排序（纯函数）
- `src/mcp_client.py`：仅标准库的 Streamable HTTP MCP 客户端（JSON-RPC + Bearer + SSE 解析）
- `src/mock_data.py`：dry-run 样例数据，零 Token 也能演示
- `src/cli.py`：命令行入口（save / nutrition / points / live）
- `SKILL.md`：可安装的 WorkBuddy 技能定义

### 阶段 4 · 测试（WorkBuddy 运行验证）
- WorkBuddy 编写 `tests/test_optimizer.py`（8 项断言），并用托管 Python 运行通过：
  - 用券：单品券 + 订单券（满减 vs 折扣取优）
  - 营养组合：命中目标热量带、同类不重复
  - 预算约束：无可行组合返回 `None`
  - 积分排序：按每千积分价值降序、可兑标记正确
- 运行 `demo.py` 验证三类模式真实输出（省钱 ¥31→¥16；营养 813kcal/41g 蛋白；积分排序正确）。

### 阶段 5 · 文档与合规
- 撰写 `README.md`（含 Mermaid 架构图、双方式快速开始、示例输出、核心公式）
- 撰写 `MCP_INTEGRATION.md`（Server/Auth/Tools/调用流程/业务价值/合规）
- 放置官方 `CONTEST_DECLARATION.md`（内容未改动）
- `mcp-config.example.json` 仅用 `${MCD_MCP_TOKEN}` 占位符，符合信息安全声明
- `.gitignore` 屏蔽 `.env`、真实 token 配置，防止凭据泄露

## 三、WorkBuddy 在本项目中的关键价值

1. **一次性拉通规则与 MCP 能力**，避免参赛者逐篇读文档。
2. **把「点餐」升级为「优化决策」**，产出可单测的算法而非脚本堆砌。
3. **dry-run 设计**：让评委与路人无需麦当劳 Token 即可体验核心能力，提升可玩性与传播性（利于 Star）。
4. **端到端交付**：从调研、编码、测试到合规文档，全程在 WorkBuddy 内完成。

## 四、提交物清单（与规则一一对应）

| 规则要求 | 文件 | 状态 |
|---|---|---|
| README.md | `README.md` | ✅ |
| CONTEST_DECLARATION.md（原样） | `CONTEST_DECLARATION.md` | ✅ |
| MCP_INTEGRATION.md | `MCP_INTEGRATION.md` | ✅ |
| mcp-config.example.json | `mcp-config.example.json` | ✅ |
| workbuddy.md | `workbuddy.md` | ✅ |
| 源代码 | `src/`、`SKILL.md`、`demo.py` | ✅ |
| 测试 | `tests/test_optimizer.py`（8 项通过） | ✅ |

> 本文件为实际开发上下文记录，未包含任何真实 Token、手机号或订单号。
