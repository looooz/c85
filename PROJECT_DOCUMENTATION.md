# 多功能提醒工具 — 项目技术与业务说明文档

---

## 一、项目概述

**项目名称**：多功能提醒工具（ReminderTool）

**项目定位**：一款基于桌面端的综合型提醒管理软件，集成定时提醒、倒计时、间隔提醒、整点报时、专注模式等多项功能，帮助用户高效管理日程和工作节奏。

**技术形态**：跨平台桌面原生应用（Windows / macOS / Linux）

---

## 二、技术框架深度解析

### 2.1 技术栈选型

| 层级 | 技术选型 | 版本要求 | 用途说明 |
|------|----------|----------|----------|
| 开发语言 | Python | 3.10+ | 核心业务逻辑实现 |
| GUI框架 | PyQt6 | ≥6.6.0 | 桌面界面渲染与交互 |
| 数据库 | SQLite3 | Python内置 | 本地数据持久化存储 |
| 音频模块 | PyQt6 Multimedia | - | 音效播放与控制 |
| 语音合成 | PyQt6 TextToSpeech | - | 整点报时语音播报 |
| 打包工具 | PyInstaller | ≥6.0.0 | 生成可执行安装包 |

### 2.2 系统架构设计

项目采用**分层架构**设计，各层职责清晰、解耦合理：

```
┌─────────────────────────────────────────────────┐
│                   表现层 (UI)                    │
│  ui_main.py  ui_dialogs.py  tray.py  theme.py   │
├─────────────────────────────────────────────────┤
│                 业务核心层 (Core)                │
│         ReminderEngine  AudioManager             │
│         FocusModeManager                         │
├─────────────────────────────────────────────────┤
│                 数据访问层 (DAO)                 │
│                   database.py                    │
├─────────────────────────────────────────────────┤
│                数据库 (SQLite)                   │
│                  reminders.db                    │
└─────────────────────────────────────────────────┘
```

#### 2.2.1 入口层 — [main.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/main.py)

[main()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/main.py#L10-L42) 函数是应用启动的唯一入口，完成以下初始化：

1. **QApplication 实例化**：配置应用名、设置 `setQuitOnLastWindowClosed(False)` 实现关闭主窗口后托盘后台驻留
2. **数据库初始化**：调用 `database.init_db()` 完成表结构创建与默认值注入
3. **核心组件装配**：实例化 `MainWindow` → `TrayManager`，建立信号-槽连接
4. **信号转发机制**：将业务层的触发信号转发至托盘通知系统

#### 2.2.2 数据访问层 — [database.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/database.py)

**设计模式**：纯函数式 DAO（无状态、线程安全的数据库操作封装）

**连接管理**：
- [get_connection()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/database.py#L9-L13)：每次操作独立创建连接，`row_factory = sqlite3.Row` 实现字典式访问，启用外键约束
- **优势**：避免多线程共享连接的问题，PyQt 定时器回调可安全调用

**数据模型**：

| 表名 | 核心字段 | 业务含义 |
|------|----------|----------|
| `reminders` | id, title, content, reminder_type, trigger_time, advance_minutes, enabled, week_day, month_day, sound_type, volume | 定时提醒主表 |
| `countdowns` | id, title, duration_seconds, remaining_seconds, is_running, triggered | 倒计时任务表 |
| `intervals` | id, title, interval_minutes, start_time, end_time, is_paused, last_triggered | 间隔提醒配置表 |
| `history` | id, title, content, reminder_type, triggered_at, is_read | 提醒历史记录表 |
| `settings` | key(PK), value | KV型全局配置表 |

**设置表设计亮点**：
- 采用 EAV（Entity-Attribute-Value）模式，灵活扩展配置项，无需频繁变更表结构
- [init_db()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/database.py#L16-L99) 内置 `INSERT OR IGNORE` 幂等初始化，保证启动安全

#### 2.2.3 业务核心层 — [core.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py)

业务层包含三个核心 Manager 类，全部继承 `QObject` 以支持 Qt 信号机制。

##### AudioManager（音频管理器）

| 方法 | 技术要点 |
|------|----------|
| [_generate_wav()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py#L19-L32) | 使用 `wave` + `struct` 模块动态合成 WAV，正弦波 + ADSR 包络（10ms 淡入淡出）避免爆音 |
| [generate_default_sounds()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py#L35-L48) | 延迟初始化：5种预置音效（880Hz/523Hz/1047Hz/660Hz/440Hz）缺失时自动生成 |
| [play_sound()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py#L66-L94) | QMediaPlayer 单例复用，支持内置音效 / 自定义文件双路径选择 |
| [speak()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py#L96-L104) | 可选依赖模式：QTextToSpeech 导入失败不影响核心功能 |

> **技术创新点**：内置 WAV 合成算法意味着 **资源目录可以为空**，应用首次启动仍能正常工作，零外部资源依赖。

##### FocusModeManager（专注模式管理器）

核心逻辑 — [is_active()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py#L133-L142)：

```python
# 判定逻辑：
# 1. 总开关未启用 → 不激活
# 2. 若配置了时段(start/end) → 仅在时段内激活
# 3. 未配置时段 → 只要开关启用即激活
```

**业务价值**：白名单式的屏蔽机制，所有提醒触发前都会检查 `focus_mode.is_active()`，避免专注时段被打断。

##### ReminderEngine（提醒引擎 — 系统心脏）

**定时器架构**：4 个独立 1Hz QTimer 分工协作

| 定时器 | 回调函数 | 职责 |
|--------|----------|------|
| `_check_timer` | [_check_reminders()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py#L217-L227) | 扫描定时提醒 |
| `_countdown_timer` | [_tick_countdowns()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py#L330-L364) | 倒计时秒级递减 |
| `_interval_check_timer` | [_check_intervals()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py#L402-L443) | 间隔提醒轮询 |
| `_chime_timer` | [_check_hourly_chime()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py#L462-L486) | 整点报时检测 |

**定时提醒触发算法 — [_should_trigger()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py#L229-L289)**：

支持 5 种周期类型，全部基于「2秒触发窗口 + 幂等标记」机制避免重复触发：

| 类型 | 触发算法 | 幂等策略 |
|------|----------|----------|
| **单次 (single)** | 当前时间 ≥ 目标时间且在 2s 窗口内 | `last_triggered` 非空即跳过 |
| **每日 (daily)** | 取触发时间的时分与当前日期组合 | 按日期前缀匹配（%Y-%m-%d） |
| **每周 (weekly)** | 匹配 `week_day` 后组合时分 | 同上按日幂等 |
| **每月 (monthly)** | 匹配 `month_day` 后组合时分 | 按月份前缀匹配（%Y-%m） |
| **每年 (yearly)** | 匹配月日后组合时分 | 按年份前缀匹配（%Y） |

**提前提醒机制**：`target_time -= timedelta(minutes=advance)`，统一在目标时间计算阶段处理，触发逻辑完全复用。

**恢复机制**：[\_restore_countdowns()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py#L311-L314) / [\_restore_intervals()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py#L387-L390) 在 Engine 初始化时从数据库重建内存态计时器，保证重启应用后任务不丢失。

#### 2.2.4 表现层

##### [ui_main.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_main.py) — 主界面

**组件化 Tab 设计**：主窗口内嵌 4 个独立 Tab 组件，每个继承 `QWidget` 封装完整功能：

| Tab组件 | 实现类 | 核心特性 |
|---------|--------|----------|
| 📋 定时提醒 | [ReminderListTab](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_main.py#L22-L153) | QTableWidget + 6列视图，增删改查 / 启用切换 |
| ⏱ 倒计时 | [CountdownTab](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_main.py#L156-L264) | 卡片式布局，QProgressBar 进度条 + 暂停/继续/取消 |
| 🔄 间隔提醒 | [IntervalTab](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_main.py#L267-L397) | 行内操作按钮（暂停/编辑/删除）嵌入 QTableWidget |
| 📊 历史记录 | [HistoryTab](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_main.py#L400-L522) | 日期筛选 / 未读过滤 / CSV导出（utf-8-sig 兼容Excel） |

[MainWindow](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_main.py#L525-L704) 关键机制：
- **关闭事件拦截**：[closeEvent()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_main.py#L548-L559) 忽略关闭事件，隐藏窗口并弹出托盘气泡提示
- **全局信号总线**：4 个 `pyqtSignal` 向外部（托盘）广播提醒触发事件
- **状态栏定时器**：5秒刷新下一个提醒倒计时 + 运行状态指示

##### [ui_dialogs.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_dialogs.py) — 对话框集合

| 对话框类 | 关键交互特性 |
|----------|-------------|
| [AddReminderDialog](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_dialogs.py#L17-L203) | 动态表单：选择提醒类型后条件显示星期/日期选择器；自定义音效文件选择器 |
| [AddCountdownDialog](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_dialogs.py#L209-L264) | 时分秒三级SpinBox组合输入 |
| [AddIntervalDialog](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_dialogs.py#L267-L382) | 分钟/小时单位切换；活跃时段（start/end）QTimeEdit |
| [SettingsDialog](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_dialogs.py#L385-L513) | 三大分组：整点报时设置 / 专注模式设置 / 默认设置（主题+音量） |
| [NotificationPopup](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_dialogs.py#L516-L603) | 无边框 + 置顶 + 闪烁动画（6次透明度切换），右下角固定定位 |

##### [tray.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/tray.py) — 托盘与悬浮窗

[TrayManager](file:///Users/macbook/dev/trae/lzp/solocoder/c85/tray.py#L131-L281) 核心能力：
- **动态图标生成**：[create_tray_icon()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/tray.py#L14-L29) 使用 QPainter 代码绘制 64×64 红色圆形 + 白色 ⏰ 字符，无图标资源依赖
- **菜单状态同步**：2秒定时器刷新菜单勾选状态 + Tooltip 显示下一个提醒倒计时
- [FloatingWindow](file:///Users/macbook/dev/trae/lzp/solocoder/c85/tray.py#L32-L129)：桌面悬浮球，支持鼠标拖拽移动，每秒更新倒计时显示

##### [theme.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/theme.py) — 主题系统

**设计模式**：单例 `ThemeManager` + 数据驱动样式表

- 内置两套完整主题：`DARK_THEME`（30+色值） + `LIGHT_THEME`
- 通过 `pyqtSignal` 实现主题切换广播，所有UI组件监听后重新渲染
- QSS 样式表按主题模板化生成，约 350+ 行细粒度控件样式定义（按钮、表格、日历、滚动条等）

---

## 三、业务功能全景分析

### 3.1 功能模块总览

```
多功能提醒工具
├── 📋 定时提醒系统
│   ├── 单次提醒（精确到分秒）
│   ├── 周期提醒（日/周/月/年）
│   └── 提前提醒（5/10/30分钟可选）
├── ⏱ 倒计时系统
│   ├── 时/分/秒自由配置
│   ├── 暂停/继续/取消控制
│   └── 进度条可视化
├── 🔄 间隔提醒系统
│   ├── 固定间隔触发（分钟/小时）
│   ├── 活跃时段限定
│   └── 独立音效配置
├── 🔔 整点报时系统
│   ├── 报时段配置（默认9-21点）
│   ├── 4种报时音效
│   └── TTS语音播报
├── 🧘 专注模式系统
│   ├── 一键启用开关
│   ├── 专注时段精细配置
│   └── 全局提醒屏蔽
├── 📊 历史记录系统
│   ├── 完整触发流水
│   ├── 日期/未读筛选
│   └── CSV一键导出
└── ⚙️ 系统增强
    ├── 系统托盘后台驻留
    ├── 桌面悬浮时间窗
    ├── 深色/浅色双主题
    └── 自定义音效支持
```

### 3.2 核心业务流程

#### 3.2.1 定时提醒创建与触发流程

```
用户创建提醒
    │
    ▼
AddReminderDialog 收集字段
  ├─ title / content        基本信息
  ├─ reminder_type          类型（5选1）
  ├─ trigger_time           触发时间点
  ├─ advance_minutes        提前量（0/5/10/30）
  ├─ week_day / month_day   周期补充字段
  ├─ sound_type / sound_file / volume  音效配置
  └─ enabled                启用状态
    │
    ▼
database.add_reminder() → SQLite持久化
    │
    ▼
ReminderEngine._check_timer（1Hz轮询）
    │
    ├─ 遍历所有 enabled=1 的提醒
    ├─ 调用 _should_trigger(r, now) 判定
    │   ├─ 类型分支处理（5种周期算法）
    │   ├─ 2秒时间窗口匹配
    │   └─ last_triggered 幂等校验
    │
    ├─ ✅ 通过判定？
    │   ├─ 否 → 跳过
    │   └─ 是 → 检查专注模式
    │           ├─ 专注激活 → 静默跳过
    │           └─ 未激活 → 执行触发
    │
    └─ 触发动作链：
        1. audio.play_sound() 播放音效
        2. database.add_history() 写入历史
        3. reminder_triggered.emit(data) 广播信号
           ├─→ 主窗口弹出 NotificationPopup
           └─→ Tray 系统通知 showMessage()
        4. update_reminder_last_triggered() 标记已触发
```

#### 3.2.2 倒计时任务生命周期

```
创建 → 运行 → 暂停 → 继续 → 完成/取消
 │      │      │       │       │
 │      │      │       │       └─ triggered=1 记录结束
 │      │      │       │          播放alert音效 + 通知
 │      │      │       │
 │      │      │       └─ is_running=1，恢复递减
 │      │      │
 │      │      └─ is_running=0，冻结 remaining
 │      │
 │      └─ 每秒 remaining-1，同步写入DB
 │         到达0时触发结束流程
 │
 └─ duration_seconds, remaining_seconds 初始化
    立即加入 _countdown_timers 字典
```

> **设计亮点**：倒计时状态持久化到 `countdowns` 表，重启应用后通过 `_restore_countdowns()` 自动恢复，支持断点续跑。

#### 3.2.3 专注模式 — 全局拦截机制

专注模式是**横切关注点**，作用于所有提醒类型的触发前环节：

```
任何提醒触发前
    │
    ▼
调用 FocusModeManager.is_active()
    │
    ├─ 返回 False → 正常提醒
    │
    └─ 返回 True → 触发被静默丢弃
         │          （仅不通知，不跳过幂等标记，
         │           避免解除专注后补发）
         │
         └─ 覆盖范围：
             ✅ 定时提醒（_check_reminders）
             ✅ 倒计时结束（_tick_countdowns）
             ✅ 间隔提醒（_check_intervals）
             ✅ 整点报时（_check_hourly_chime）
```

---

## 四、核心技术亮点与设计决策

### 4.1 1Hz 轮询 vs 绝对时间定时器

**决策**：采用 4 个 1Hz QTimer 轮询而非为每个提醒创建独立 QTimer

| 维度 | 轮询方案（采用） | 独立Timer方案 |
|------|-----------------|---------------|
| 大规模提醒 | O(n) 线性扫描，可承载数百条 | 千级Timer造成线程事件队列拥堵 |
| 内存占用 | 常量级内存 | 每个Timer消耗独立对象 |
| 修改/删除 | 直接操作DB，下轮自动生效 | 需要精确查找并停止对应Timer |
| 误差累积 | 每秒对齐系统时钟，无漂移 | QTimer 本身存在毫秒级漂移 |
| 重启恢复 | 从DB重建状态即可 | 需要重建所有Timer |

### 4.2 2秒触发窗口 + 幂等标记防重

问题：1Hz轮询可能因系统调度抖动导致漏触发或重复触发

解决方案 — 「窗口 + 幂等」双重保障：
1. **时间窗口**：`now >= target && now < target + 2s`，容忍最多 1 秒的轮询延迟
2. **幂等屏障**：写入 `last_triggered` 时间戳，按周期粒度（日/月/年）匹配前缀，确保同一周期内仅触发一次

### 4.3 无资源依赖部署策略

项目 **不携带任何二进制资源文件** 即可正常运行：

| 资源类型 | 生成方式 | 代码位置 |
|----------|----------|----------|
| 5种内置音效 | 首次启动时用 Python wave 模块动态合成 | [_generate_wav()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py#L19-L32) |
| 托盘图标 | 使用 QPainter 代码绘制圆形+字符 | [create_tray_icon()](file:///Users/macbook/dev/trae/lzp/solocoder/c85/tray.py#L14-L29) |
| 通知/悬浮窗 | 纯QSS样式渲染，无边框自绘 | [NotificationPopup](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_dialogs.py#L516-L603) |

### 4.4 信号驱动的组件解耦

Qt 信号-槽机制贯穿全项目，实现了 UI ↔ 业务逻辑 ↔ 系统组件的完全解耦：

```
ReminderEngine (业务层)
  ├─ reminder_triggered ──→ MainWindow._on_reminder_triggered
  │                          ├─ 弹出通知窗
  │                          ├─ 刷新列表
  │                          └─ reminder_triggered_signal → TrayManager.showNotification
  ├─ countdown_triggered ──→ MainWindow._on_countdown_triggered
  ├─ interval_triggered ──→ MainWindow._on_interval_triggered
  └─ hourly_chime_triggered → MainWindow._on_hourly_chime
```

---

## 五、文件与代码索引

| 文件 | 代码行数 | 核心职责 | 关键类/函数 |
|------|----------|----------|-------------|
| [main.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/main.py) | 46 | 应用入口 | `main()` |
| [database.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/database.py) | 420 | 数据持久化 | `init_db()`, `add_reminder()`, `get_reminders()` |
| [core.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/core.py) | 545 | 业务引擎 | `ReminderEngine`, `AudioManager`, `FocusModeManager` |
| [ui_main.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_main.py) | 704 | 主界面 | `MainWindow`, `ReminderListTab`, `CountdownTab`, `IntervalTab`, `HistoryTab` |
| [ui_dialogs.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/ui_dialogs.py) | 603 | 对话框组件 | `AddReminderDialog`, `SettingsDialog`, `NotificationPopup` |
| [tray.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/tray.py) | 281 | 托盘与悬浮窗 | `TrayManager`, `FloatingWindow` |
| [theme.py](file:///Users/macbook/dev/trae/lzp/solocoder/c85/theme.py) | 943 | 主题系统 | `ThemeManager`, `DARK_THEME`, `LIGHT_THEME` |

---

## 六、总结

### 技术层面
本项目是 **PyQt6 桌面应用的优秀工程实践**：
- 架构层次清晰（UI/业务/数据三层分离）
- 数据模型设计合理（EAV配置表 + 状态持久化）
- 轮询引擎兼顾性能与可靠性
- 零资源依赖的部署策略体现了工程巧思
- 信号驱动模式实现了组件间松耦合

### 业务层面
围绕「提醒」这一核心场景，构建了 **4类提醒模式 + 2类辅助模式** 的完整生态：
- **基础层**：定时/倒计时/间隔/整点报时，覆盖绝大多数时间管理需求
- **增强层**：专注模式（屏蔽干扰）、历史记录（回溯审计）
- **体验层**：托盘驻留、悬浮窗、主题切换、自定义音效

系统设计体现了「**配置灵活度**」与「**使用便捷性**」的良好平衡，既可精细调控每个参数，又能通过合理默认值降低使用门槛。
