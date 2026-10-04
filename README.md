# 音频处理与报告工作流分享包

整理日期：2026-10-04。内容聚焦流程、模型分工、计算量、质量控制与分类方法。

本包由一个既有音频处理 skill 和项目中积累的多模型、来源核对、分类报告流程重新整理而成。下面的 4 个公开 skill 是这次模块化后的版本；不表示原项目此前安装了 4 个独立 skill。

## 阅读入口

- [方案与模型分工](docs/方案与模型分工.md)：默认、快速、自适应与完整多模型方案，以及文本模型的分级使用。
- [计算量与实测边界](docs/计算量与实测边界.md)：匿名耗时记录、RTF、传输量和估算公式。
- [质量与话题无关分类](docs/质量与话题无关分类.md)：时间、说话人、证据、信息类型及可配置主题标签。
- [公开内容范围](docs/公开内容范围.md)：分享包包含什么、排除了什么，以及如何继续维护。

## 可安装 skills

| skill | 输入与作用 | 主要模型／工具 |
|---|---|---|
| [audio-transcribe](skills/audio-transcribe/SKILL.md) | 从音频生成可追溯全文、时间轴和匿名说话人层 | faster-whisper large-v3 + Sortformer v2.1 |
| [audio-ensemble](skills/audio-ensemble/SKILL.md) | 对疑难区间补跑或做多模型比较与仲裁 | Whisper、Qwen3-ASR、VibeVoice-ASR；分离结果独立核验 |
| [audio-source-relations](skills/audio-source-relations/SKILL.md) | 核对格式副本、连续分卷、跨设备部分重叠 | 哈希、解码、文本锚点、声学锚点 |
| [transcript-report-classify](skills/transcript-report-classify/SKILL.md) | 从完整文字做分类、证据报告和分级审阅 | 按任务复杂度配置文本模型与推理强度 |

识别、分离、文本分析是三种不同任务。加强报告模型不能恢复 ASR 漏掉的内容；增加识别模型也不自动形成可靠会议结论。

## 使用方式

将需要的 skill 目录复制到接收方工具识别的技能目录；Codex 的常见个人目录为 `~/.codex/skills/`。本包不替换接收方已有配置。

示例请求：

- “使用 $audio-transcribe 处理我指定的音频，保留原始结果并标记不确定内容。”
- “使用 $audio-ensemble 对标出的疑难区间比较多模型，不自动猜测专名。”
- “使用 $audio-source-relations 核对这些文件是否同源或部分重叠。”
- “使用 $transcript-report-classify 按我提供的分类表整理全文，并生成带证据的报告。”

按 [配置示例](config/runtime.example.toml) 在自己的环境配置 Python、模型缓存和计算设备。代码 helper 依赖接收方自行准备的运行环境；未附模型权重、远端部署器或 PDF 引擎，因此本包不是完整的服务器安装镜像。

`audio-transcribe` 附通用 ASR、Sortformer worker 和说话人对齐脚本。`tools/estimate_compute.py` 可在无模型环境估算计算与传输开销；具体操作见各 skill。只运行 dry-run 不会加载模型或访问远端主机。

## 公开验证与效果边界

原流程支持带时间文字、说话人层、结构化报告、MP3、分类索引和哈希验收。分享包保留这些方法与交付要求，不附任何真实录音、全文、报告或实际主题分类。

匿名耗时表是历史运行日志的数值摘录，样本不可公开复现，不能当作模型准确率排行榜。本包的 helper 已做合成数据和 dry-run 检查；打包阶段未重新运行完整 GPU 识别实验。

参见 [核验结果](VALIDATION.json)。公开 ZIP 只按 [文件白名单](PUBLIC_FILES.json) 打包，没有从原项目递归复制文件。上游模型与软件的获取和使用依各自许可证；本包不分发它们的权重。

## 版本管理

本目录作为独立 Git 仓库维护。更新前运行公开内容扫描，检查新增文件并更新白名单；提交前核对暂存文件。忽略规则已排除常见录音、报告、运行输出和本地配置，但发布审阅仍以白名单为准。
