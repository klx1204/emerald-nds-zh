# Pokémon Emerald NDS 中文化补丁

给 [Pokémon Emerald NDS](https://github.com/logdog2325/pokemon-ruby-sapphire-nds)（在《黑2》引擎里重做的绿宝石）加一层中文补丁。

本项目**只包含补丁和构建数据**，不包含 ROM、游戏文本原文或存档。

- 上游项目：<https://github.com/logdog2325/pokemon-ruby-sapphire-nds>
- 上游源码：<https://github.com/logdog2325/HoennB2>
- 当前兼容上游版本：**Emerald NDS v2.1**

## 状态

开发中。当前目标：

- 中文字体（基于 `rh-hideout-chinese/pokeemerald-expansion` 的中文点阵字库，缺字用 Fusion Pixel 补）
- Hoenn 剧情/菜单文本：用现成中文替换，匹配不到保留英文
- 黑2原生 UI（菜单、战斗、背包、图鉴、商店等）：从黑2汉化版迁移

**不进行 AI 翻译。** 没有现成译文的内容保留英文。

## 原理

上游补丁把 Hoenn 放进 Black 2（USA/Europe，游戏码 `IREO`）里。本补丁只做三件事，不改 ARM9、overlay 或存档结构：

1. 替换文本库 `a/0/0/2`（系统文本）和 `a/0/0/3`（脚本文本）；
2. 给字体库 `a/0/2/3` 补上简体中文字形；
3. 按中文字宽重排换行，保留 `{0100:x}`、`{be00}`、`{be01}` 等控制码。

因此存档与上游版本通用（汉化前后可以继续读同一个存档）。

## 安装

需要：

1. 你自己的 **Pokémon Black Version 2**（USA/Europe，游戏码 `IREO`）干净 dump：
   - 大小 536,870,912 字节
   - CRC32 `D4427FD1`
   - SHA-1 `e51e6dfb8678a3d19dcd2a10691b96a569ca0abb`
2. 上游对应的 **Emerald NDS** BPS 补丁。

Release 里会提供两种补丁：

| 文件 | 源 ROM | 用途 |
| --- | --- | --- |
| `emerald-nds-zh_<version>_full.bps` | 原版 Black 2 | 新用户一步到位 |
| `emerald-nds-zh_<version>_from-upstream.bps` | 上游 patched ROM | 已安装上游的用户增量更新 |

用任意 BPS 补丁器（Floating IPS、beat、Rom Patcher JS）应用在电脑上，不要用手机浏览器打 512 MB 的补丁。

## 构建

需要 Python 3、[uv](https://docs.astral.sh/uv/)、一份干净的 Black 2 dump，以及上游 bps。

```sh
uv venv .venv
uv pip install ndspy pillow numpy

# 下载上游最新补丁并重新构建（需要 gh 已登录）
./update_zh.sh

# 或指定上游版本
./update_zh.sh v2.1
```

脚本会：

1. 下载上游 Emerald BPS；
2. 应用到本地的干净 Black 2；
3. 用 `zh_data/` 替换文本与字体；
4. 生成 full / incremental 两个 BPS；
5. 用 melonDS 做一次启动检查。

本地 ROM 路径通过参数/环境变量传入，不写死在仓库里：

```sh
BLACK2_ROM=/path/to/black2.nds ./update_zh.sh v2.1
```

## 目录结构

```text
zh_data/
  hoenn/    Hoenn 文本覆盖表（按文本库文件编号 + 行号）
  b2/       从黑2汉化版迁移的 UI 文本
  terms/    物种/招式/道具/地名/角色名映射
  font/     生成的字体数据
tools/      文本索引、字体构建、排版、打包脚本
release/    生成的 BPS（不提交）
```

## 中文覆盖范围

| 内容 | 来源 |
| --- | --- |
| 宝可梦名、招式、特性、道具、地名、职业 | 中文 `pokeemerald-expansion`、`pokemon-dataset-zh` |
| 图鉴说明 | `pokemon-dataset-zh`（Emerald 版） |
| 黑2原生 UI | 黑2汉化版（ACG汉化组 + 口袋群星SP 等）迁移 |
| Emerald 原版剧情 | 中文 `pokeemerald-expansion` 精确匹配 |
| HoennB2 改写/新增剧情 | 无现成译文，保留英文 |

## 许可

代码与补丁数据：**GPL-3.0**，见 [LICENSE](LICENSE)。

第三方资源的来源与许可见 [NOTICE](NOTICE)。游戏文本、图像、音乐的权利归 Nintendo / Game Freak / Creatures / The Pokémon Company 所有；本项目不分发这些内容，只分发补丁。

## 致谢

- [logdog2325](https://github.com/logdog2325)：HoennB2 与上游游戏
- [pret](https://github.com/pret)：pokeemerald
- [fuddlesworth](https://github.com/fuddlesworth)：pokebw2
- [rh-hideout-chinese](https://github.com/rh-hideout-chinese/pokeemerald-expansion)：中文文本与字库
- [42arch/pokemon-dataset-zh](https://github.com/42arch/pokemon-dataset-zh)：中文图鉴数据
- [TakWolf/fusion-pixel-font](https://github.com/TakWolf/fusion-pixel-font)：缺字补充字体
- ACG汉化组、口袋群星SP 等黑2汉化参与者
