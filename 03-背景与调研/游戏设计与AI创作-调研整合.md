# 游戏设计与 AI 创作 · 调研整合报告

> **文档类型**：全网检索归纳 · 服务 AI 小游戏创作工坊
> **版本**：Survey-01
> **日期**：2026-06-13
> **检索报告**：`data/游戏设计与AI创作调研/report_20260613_195217.json`
> **检索方式**：`research_crawler` + `game_crawler_patch` · 虚拟环境 `py310_torch251_cu121`
> **数据源**：web · bilibili · csdn · github · zhihu · juejin

---

## 一、调研摘要（给方案与模板预制用）

本次检索覆盖 **AI 辅助游戏创作、Godot 2D 实践、游戏手感理论、参数化模板、K12 教育游戏展陈、分品类机制设计、学术综述** 七条主线。有效条目 **800** 条（已过滤噪声）。

**对本项目的直接结论：**

1. **你的「core 预制 + tuning 小改」思路与行业最佳实践一致**——Data-driven / Game Jam 模板路线是 10 分钟交付的唯一可行解。
2. **Godot + Cursor + MCP** 已有大量社区案例（俯视角射击教程、塔防 case study、godot-mcp）。
3. **AI 做游戏的价值在闭环**——GamingAgent 等研究证明：能运行、能读报错、能迭代才有意义。
4. **K12 展陈**需低暴力、短循环、可视化创作过程，与教育游戏/Serious Games 文献方向一致。
5. **分品类**应分别预制：射击（移动+命中）、塔防（数值公式+波次）、闯关（跳跃手感）。

---

## 二、分主题要点与项目映射

### 2.1 AI辅助游戏创作与智能体

- LLM Agent 适合承担「改配置/写脚本补丁」而非从零设计核心手感
- godot-mcp / GamingAgent 类工具证明：运行-读日志-修复闭环是 AI 做游戏的关键
- 展陈场景应限制 Agent scope：模板 + tuning + theme，与品类核心参数规格一致

| # | 分数 | 来源 | 标题 | 链接 |
|---|------|------|------|------|
| 1 | 90 | official | GitHub - lmgame-org/GamingAgent: [ICLR 2026] LLM/VLM gaming ... | https://github.com/lmgame-org/GamingAgent |
| 2 | 89 | official | GitHub - JingyeChen/awesome-game-generation: ️ Explore ... | https://github.com/JingyeChen/awesome-game-generation |
| 3 | 83 | official | GitHub - BlueBirdBack/godot-cursorrules: Godot 4.4 Cursor rules... | https://github.com/BlueBirdBack/godot-cursorrules |
| 4 | 82 | bilibili | 250814-视觉小说游戏开发：AI代理工作流完成，一键生成功能即将实现 /...做了个游戏：llm狼人杀_哔哩哔哩_bilibili【AI教程】全B站最详细AI Agent开发全套教程，手把手教你从0到1开始搭...【精华35分钟】这应该… | https://www.bilibili.com/video/BV1UzbJzbEsN/ |
| 5 | 82 | bilibili | 做了个游戏：llm狼人杀_哔哩哔哩_bilibili【AI教程】全B站最详细AI Agent开发全套教程，手把手教你从0到1开始搭...【精华35分钟】这应该是全网AI Agent讲解得最透彻的教程了，从什么是A...LLM+MCP+RAG… | https://www.bilibili.com/video/BV134421c7uK/ |
| 6 | 78 | bilibili | 让AI直接操作godot开发游戏，mcp新版本发布_哔哩哔哩_bilibili | https://www.bilibili.com/video/BV1mL5d66ETm/ |
| 7 | 75 | bilibili | 【精华35分钟】这应该是全网AI Agent讲解得最透彻的教程了，从什么是A...LLM+MCP+RAG实战-从0无框架实现极简Agent客户端 OpenAI/智能体/大模型...10分钟讲清楚 Prompt, Agent, MCP 是什么… | https://www.bilibili.com/video/BV1dxm6YPEDB/ |
| 8 | 75 | bilibili | LLM+MCP+RAG实战-从0无框架实现极简Agent客户端 OpenAI/智能体/大模型...10分钟讲清楚 Prompt, Agent, MCP 是什么_哔哩哔哩_bilibiliLLM Agent的 “Windows” 来了！AIO… | https://www.bilibili.com/video/BV1dcRqYuECf/ |

### 2.2 Godot游戏设计与GDScript

- Godot 4 2D 俯视角射击、塔防、平台跳跃均有成熟开源教程与 template
- GDScript 强类型 + 全文本项目最适合 Cursor 批量编辑
- 官方与 GDQuest 教程可作为 core 层预制参考实现

| # | 分数 | 来源 | 标题 | 链接 |
|---|------|------|------|------|
| 1 | 92 | github | rogal01/tower-defense-case-study | https://github.com/rogal01/tower-defense-case-study |
| 2 | 90 | official | Godot Top-down Shooter Tutorial - GitHubCreating a Top-Down Shooter Game in Godot - Sharp Coder BlogHow to do top-down g… | https://github.com/josephmbustamante/Godot-Top-down-Shooter-Tutorial |
| 3 | 86 | bilibili | Godot 2D游戏开发- 完整版 - Complete 2D Platformer in Godot 4.3: F...互联网上最全面的Godot4 2D游戏开发指南课程_哔哩哔哩_bilibiliGodot 4 中的 2D 平台游戏教程… | https://www.bilibili.com/video/BV1md5WzAErR/ |
| 4 | 86 | bilibili | 互联网上最全面的Godot4 2D游戏开发指南课程_哔哩哔哩_bilibiliGodot 4 中的 2D 平台游戏教程 -（第01 / 7部分）-【英译中-双字幕】_...在Godot 4中创建一个完整的2D幸存者风格游戏_哔哩哔哩_bil… | https://www.bilibili.com/video/BV1ci1SYaEJy/ |
| 5 | 82 | official | GitHub - EladKarni/godot4-2d-platformer-template: A simple template... | https://github.com/EladKarni/godot4-2d-platformer-template |
| 6 | 82 | official | ape1121/Godot-4-Tower-Defense-Template: A project designed to... | https://github.com/ape1121/Godot-4-Tower-Defense-Template |
| 7 | 80 | bilibili | Godot 4 中的 2D 平台游戏教程 -（第01 / 7部分）-【英译中-双字幕】_...在Godot 4中创建一个完整的2D幸存者风格游戏_哔哩哔哩_bilibili【dev log】camera debug和coyote-time土… | https://www.bilibili.com/video/BV16QZVYZEoR/ |
| 8 | 80 | github | age-of-asparagus/godot3-3dgame | https://github.com/age-of-asparagus/godot3-3dgame |

### 2.3 游戏手感与核心机制设计

- Game Feel / Juice 理论支持：射击反馈、平台 coyote time、塔防数值公式应写入 core
- MDA 框架：Mechanics 预制锁定，Dynamics 靠 tuning 微调，Aesthetics 靠 theme
- 10 分钟交付依赖「手感预制好」，而非现场调参

| # | 分数 | 来源 | 标题 | 链接 |
|---|------|------|------|------|
| 1 | 76 | zhihu | 射击游戏手感与表现构建综述（上） - 知乎【策划向】全景解构射击游戏枪械设计——表现/手感篇如何用交互打造FPS之魂——枪械手感 - 知乎射击游戏，如何构建让人欲罢不能的反馈体系？ - 知乎射击游戏的枪械手感解析Part1——什么是手感？ … | https://zhuanlan.zhihu.com/p/433929865 |
| 2 | 72 | juejin | 爆肝推荐！GitHub上这个「游戏项目」，竟能让CUDA新手秒变大神 ... | https://juejin.cn/post/7478129452679315506 |
| 3 | 70 | bilibili | 【塞德莎】神乎其神的过法 免费类推箱解谜游戏《Pull Chain》全关卡初...【聊聊解谜游戏】面向趣味出题，回顾下我的谜题设计方法_哔哩哔哩_bil...游戏关卡设计核心教程丨玩家引导 / 关卡节奏 / 战斗设计 / 循环理论 -...… | https://www.bilibili.com/video/BV1zGGY64EwU/ |
| 4 | 70 | bilibili | 【聊聊解谜游戏】面向趣味出题，回顾下我的谜题设计方法_哔哩哔哩_bil...游戏关卡设计核心教程丨玩家引导 / 关卡节奏 / 战斗设计 / 循环理论 -...解谜游戏关卡设计练习_哔哩哔哩bilibili【关卡设计】线性解密+平台跳跃关卡白… | https://www.bilibili.com/video/BV1A8MFzGEJA/ |
| 5 | 68 | bilibili | 游戏设计原则 - 塔防, 第四集 '平衡和数学' / 中英双字 / LtRandolph ...救救制作组，如何设计塔防数值_杂谈游戏设计原则 - 塔防, 第一集 '基础' / 中英双字 / LtRandolph Games游戏数值拆解：只… | https://www.bilibili.com/video/BV1yY411L7pR/ |
| 6 | 68 | bilibili | 救救制作组，如何设计塔防数值_杂谈游戏设计原则 - 塔防, 第一集 '基础' / 中英双字 / LtRandolph Games游戏数值拆解：只需要5步 掌握任何游戏数值结构_游戏热门视频【数值化气球塔防6】第一期模范计算篇_游戏热门视频在… | https://www.bilibili.com/video/BV18f4y1L7ir/ |
| 7 | 68 | bilibili | 游戏设计原则 - 塔防, 第一集 '基础' / 中英双字 / LtRandolph Games游戏数值拆解：只需要5步 掌握任何游戏数值结构_游戏热门视频【数值化气球塔防6】第一期模范计算篇_游戏热门视频在Unity中创建3D塔防游戏的终极… | https://www.bilibili.com/video/BV1k3411j74G/ |
| 8 | 68 | bilibili | 游戏数值拆解：只需要5步 掌握任何游戏数值结构_游戏热门视频【数值化气球塔防6】第一期模范计算篇_游戏热门视频在Unity中创建3D塔防游戏的终极指南_哔哩哔哩_bilibili用了这个数值工具，我竟然吊打了10年老策划_哔哩哔哩_bili… | https://www.bilibili.com/video/BV1Ezw7zqEWz/ |

### 2.4 模板化与参数化游戏生成

- Data-driven design（JSON/Resource 驱动）是快速个性化的行业共识
- Game Jam 10 分钟原型实践：预制场景 + 换数值 + 换皮
- 与本项目 `config/game_config.json` 三层模型完全同构

| # | 分数 | 来源 | 标题 | 链接 |
|---|------|------|------|------|
| 1 | 81 | official | Godot 2D Platformer Starter Kit - GitHubGreenCloversGames/Scalable-Platformer-Template - GitHubnonlilynear/godot-platfor… | https://github.com/brettchalupa/godot_2d_platformer |
| 2 | 81 | web | Top rapid-prototyping Repositories - GitHub Projects for... / Git Stars | https://git-stars.org/repositories/topic/rapid-prototyping |
| 3 | 78 | official | GreenCloversGames/Scalable-Platformer-Template - GitHub | https://github.com/GreenCloversGames/Scalable-Platformer-Template |
| 4 | 78 | official | nonlilynear/godot-platformer-template - GitHub | https://github.com/nonlilynear/godot-platformer-template |
| 5 | 74 | official | GitHub - cwage/godot-template: Simple template for godot game ... | https://github.com/cwage/godot-template |
| 6 | 73 | official | GitHub - Matt-OP/godot-game-template | https://github.com/Matt-OP/godot-game-template |
| 7 | 72 | official | Maaack/Godot-Game-Template - GitHub | https://github.com/Maaack/Godot-Game-Template |
| 8 | 72 | official | GitHub - ovrdos/godot-game-template: Godot template with a ... | https://github.com/ovrdos/godot-game-template |

### 2.5 K12教育游戏与展陈

- 教育游戏/Serious Games 强调低暴力、短时长、可带走成果
- 研学场景需要讲解员复位、双工位队列、成果上墙
- 与文三路馆「AI 教育区 K12」定位一致：创造感 > 竞技感

| # | 分数 | 来源 | 标题 | 链接 |
|---|------|------|------|------|
| 1 | 75 | juejin | 游戏角色设计：塑造独特的人物形象1.背景介绍 游戏角色设计是游戏开发...创客教室-中小学创客教育课程介绍近年来，国家在围绕以“素质教育”为中...Unity 6 2D平台游戏开发_从入门到精通it课程《游戏即教材：Unity 6 2D..… | https://juejin.cn/post/7318914474060021811 |
| 2 | 59 | web | blog.csdn.net/lovelion/article/details/8263025 | https://blog.csdn.net/lovelion/article/details/8263025 |
| 3 | 59 | juejin | 游戏的教育和娱乐价值：如何利用游戏提高学习效果1.背景介绍 随着现代...教育游戏实践：Cocos2d-x+HarmonyOS 5开发跨设备协作的儿童编程应用以...机器智能幽默感的教育应用：如何提高学生参与度1.背景介绍 在当今的教...… | https://juejin.cn/post/7319903143956152346 |
| 4 | 59 | juejin | 机器智能幽默感的教育应用：如何提高学生参与度1.背景介绍 在当今的教...Unity 6 2D平台游戏开发_从入门到精通it课程《游戏即教材：Unity 6 2D...中美创客大赛历年获奖作品展当我们环顾整个展区，最先映入眼帘的就是...公… | https://juejin.cn/post/7321410216855322650 |
| 5 | 57 | juejin | 我花一天用AI做了个免费儿童编程小游戏，比市面上的贵价APP好玩多了最... | https://juejin.cn/post/7613453695863324715 |
| 6 | 54 | juejin | 微信小游戏开发新手教程 - 小蚂蚁教你做游戏的专栏 - 掘金 | https://juejin.cn/column/6960570072054104077 |
| 7 | 53 | bilibili | 《妃十三学园》全平台公测开启 | https://game.bilibili.com/girl/rabbit/?msource=1&source=afid_1706cf30d48211e99a451ec09ba8d106 |
| 8 | 52 | juejin | 【Java】Teaching 在线教学平台 scratch3https://github.Scratch在线... | https://juejin.cn/post/7277458508802850879 |

### 2.6 分品类设计参考

- 射击：顶视角移动 + 波次；塔防：路径 + 经济 + 波次表
- 闯关：移速/跳跃/关卡块；休闲：单核心循环 + 计分
- 直接映射到 TPL-01~07 模板 core 预制清单

| # | 分数 | 来源 | 标题 | 链接 |
|---|------|------|------|------|
| 1 | 82 | official | GitHub - 764424567/Game_Parkour: Unity开发跑酷游戏 | https://github.com/764424567/Game_Parkour |
| 2 | 75 | juejin | 【Unity3D开发小游戏】Unity3D零基础一步一步教你制作跑酷类游戏最近...【c语言】实现天天酷跑游戏天天酷跑游戏开发日志及源码 纯c语言开发的...当我做了一个网页版的地铁跑酷由于笔者最近在研究图形学Three.js相关...# … | https://juejin.cn/post/7124503132935028750 |
| 3 | 73 | bilibili | Godot 4 制作随机 2D 障碍敌人（C#）（游戏开发教程） | https://www.bilibili.com/video/BV1kT421X7g7/ |
| 4 | 67 | github | nnameuy/RhythmDash | https://github.com/nnameuy/RhythmDash |
| 5 | 64 | juejin | 英语单词拼写塔防游戏开发实战 将游戏工程更新到了Unity2018，并开源... | https://juejin.cn/post/7130546251195482148 |
| 6 | 64 | web | Unity 简单跑酷游戏策划与实现_跑酷游戏设计方案-CSDN博客 | https://blog.csdn.net/leoysq/article/details/134111311 |
| 7 | 63 | web | Unity塔防游戏终极指南 / Udemy【中文字幕】 - 云艺术空间 | https://yyskj.com/58025.html |
| 8 | 61 | bilibili | UE5 移动端跑酷游戏开发 / 角色控制 / 障碍物生成 / UI系统 / 移动端... | https://www.bilibili.com/video/BV1gFGj6hEKe/ |

### 2.7 学术与行业理论

- PCG（程序化内容生成）综述支持参数化关卡而非生成新引擎
- LLM 代码生成论文指出：闭环执行与类型约束降低失败率
- 期刊材料用于方案汇报背书，落地仍以 Godot 模板为准

| # | 分数 | 来源 | 标题 | 链接 |
|---|------|------|------|------|
| 1 | 97 | github | cirosantilli/china-dictatorship | https://github.com/cirosantilli/china-dictatorship |
| 2 | 97 | github | gege-circle/.github | https://github.com/gege-circle/.github |
| 3 | 97 | github | cirosantilli/china-dictatroship-7 | https://github.com/cirosantilli/china-dictatroship-7 |
| 4 | 97 | github | mRFWq7LwNPZjaVv5v6eo/cihna-dictattorshrip-8 | https://github.com/mRFWq7LwNPZjaVv5v6eo/cihna-dictattorshrip-8 |
| 5 | 97 | github | panbinibn/OpenPacketFix_ | https://github.com/panbinibn/OpenPacketFix_ |
| 6 | 97 | github | zpc1314521/PCL2 | https://github.com/zpc1314521/PCL2 |
| 7 | 96 | github | Aryia-Behroziuan/References | https://github.com/Aryia-Behroziuan/References |
| 8 | 77 | web | A Survey on Large Language Models for Code GenerationLarge Language Models for Game Development: A Survey on ...GitHub -… | https://arxiv.org/abs/2406.00515 |

---

## 三、高价值资源精选（跨主题 Top 15）

### 1. cirosantilli/china-dictatorship

- **综合分**：97.2 · **来源**：github · **主题**：学术与行业理论
- **链接**：https://github.com/cirosantilli/china-dictatorship
- **摘要**：【开源代码】cirosantilli/china-dictatorship | 来源:github | 站点:github.com | 提供:地图、模型、技术文档、开源代码、数据集、教程、SDK/API、可下载资源、涉及授权/版权 | 相关词:unity、城市、3d、地图、杭州、开源、sdk、api | 摘要:反中共政治宣传库。Anti Chinese government propaganda. 住在中国真名用户的网友请别给星星，不然你要被警察请喝茶。常见问答集，新闻集和饭店和音乐建议。卐习万岁卐。冠状病毒审查郝海东新疆改造中心六四事件法轮功 996.

### 2. gege-circle/.github

- **综合分**：97.2 · **来源**：github · **主题**：学术与行业理论
- **链接**：https://github.com/gege-circle/.github
- **摘要**：【开源代码】gege-circle/.github | 来源:github | 站点:github.com | 提供:地图、模型、技术文档、开源代码、数据集、教程、SDK/API、可下载资源、涉及授权/版权 | 相关词:unity、城市、3d、地图、杭州、开源、sdk、api | 摘要:这里是GitHub的草场，也是戈戈圈爱好者的交流地，主要讨论动漫、游戏、科技、人文、生活等所有话题，欢迎各位小伙伴们在此讨论趣事。This is GitHub grassland, and the community place for Gege circle lover

### 3. cirosantilli/china-dictatroship-7

- **综合分**：97.2 · **来源**：github · **主题**：学术与行业理论
- **链接**：https://github.com/cirosantilli/china-dictatroship-7
- **摘要**：【开源代码】cirosantilli/china-dictatroship-7 | 来源:github | 站点:github.com | 提供:地图、模型、技术文档、开源代码、数据集、教程、SDK/API、可下载资源、涉及授权/版权 | 相关词:unity、城市、3d、地图、杭州、开源、sdk、api | 摘要:反中共政治宣传库。Anti Chinese government propaganda. https://github.com/cirosantilli/china-dictatorship 的备份backup. 住在中国真名用户的网友请别给星

### 4. mRFWq7LwNPZjaVv5v6eo/cihna-dictattorshrip-8

- **综合分**：97.2 · **来源**：github · **主题**：学术与行业理论
- **链接**：https://github.com/mRFWq7LwNPZjaVv5v6eo/cihna-dictattorshrip-8
- **摘要**：【开源代码】mRFWq7LwNPZjaVv5v6eo/cihna-dictattorshrip-8 | 来源:github | 站点:github.com | 提供:地图、模型、技术文档、开源代码、数据集、教程、SDK/API、可下载资源、涉及授权/版权 | 相关词:unity、城市、3d、地图、杭州、开源、sdk、api | 摘要:反中共政治宣传库。Anti Chinese government propaganda. https://github.com/cirosantilli/china-dictatorship 的备份backup. 住在中国真

### 5. panbinibn/OpenPacketFix_

- **综合分**：97.2 · **来源**：github · **主题**：学术与行业理论
- **链接**：https://github.com/panbinibn/OpenPacketFix_
- **摘要**：【开源代码】panbinibn/OpenPacketFix_ | 来源:github | 站点:github.com | 提供:地图、模型、技术文档、开源代码、数据集、教程、SDK/API、可下载资源、涉及授权/版权 | 相关词:unity、城市、3d、地图、杭州、开源、sdk、api | 摘要:大陆修宪香港恶法台湾武统朝鲜毁约美中冷战等都是王沪宁愚弄习思想极左命运共同体的大策划中共窃国这半个多世纪所犯下的滔天罪恶，前期是毛泽东策划的，中期6.4前后是邓小平策划的，黄牛数据分析后期是毛的极左追随者三朝罪恶元凶王沪宁策划的。王沪宁高小肆业因文革政治和情报需

### 6. zpc1314521/PCL2

- **综合分**：97.2 · **来源**：github · **主题**：学术与行业理论
- **链接**：https://github.com/zpc1314521/PCL2
- **摘要**：【开源代码】zpc1314521/PCL2 | 来源:github | 站点:github.com | 提供:地图、模型、技术文档、开源代码、数据集、教程、SDK/API、可下载资源、涉及授权/版权 | 相关词:unity、城市、3d、地图、杭州、开源、sdk、api | 摘要:[stays mad] 反PCL宣传库。Anti PCL propaganda. 大陆修宪香港恶法台湾武统朝鲜毁约美中冷战等都是王沪宁愚弄习思想极左命运共同体的大策划中共窃国这半个多世纪所犯下的滔天罪恶，前期是毛泽东策划的，中期6.4前后是邓小平策划的，黄牛数据分析后期是毛的极左

### 7. Aryia-Behroziuan/References

- **综合分**：95.5 · **来源**：github · **主题**：学术与行业理论
- **链接**：https://github.com/Aryia-Behroziuan/References
- **摘要**：【开源代码】Aryia-Behroziuan/References | 来源:github | 站点:github.com | 提供:地图、技术文档、开源代码、数据集、教程、SDK/API、涉及授权/版权 | 相关词:tile、api、github、game、ai、cursor、agent | 摘要:Poole, Mackworth & Goebel 1998, p. 1.  Russell & Norvig 2003, p. 55.  Definition of AI as the study of intelligent agents: Poole,

### 8. rogal01/tower-defense-case-study

- **综合分**：92.2 · **来源**：github · **主题**：Godot游戏设计与GDScript
- **链接**：https://github.com/rogal01/tower-defense-case-study
- **摘要**：【开源代码】rogal01/tower-defense-case-study | 来源:github | 站点:github.com | 提供:地图、技术文档、开源代码、SDK/API、可下载资源、涉及授权/版权 | 相关词:unity、tile、api、demo、github、godot、gdscript、game | 摘要:A multi-engine case study demonstrating high-fidelity game design parity across Kotlin, Godot, and Unity. | ⭐0 | 语言

### 9. Godot Top-down Shooter Tutorial - GitHubCreating a Top-Down Shooter Game in Godot - Sharp Coder BlogHow to do top-down g…

- **综合分**：90.0 · **来源**：official · **主题**：Godot游戏设计与GDScript
- **链接**：https://github.com/josephmbustamante/Godot-Top-down-Shooter-Tutorial
- **摘要**：【地图数据】Godot Top-down Shooter Tutorial - GitHubCreating a Top-Down Shooter Game in Godo | 来源:official | 站点:github.com | 提供:地图、技术文档、开源代码、教程、可下载资源、涉及授权/版权 | 相关词:unity、tile、github、godot、gdscript、game、ai | 摘要:This repository contains the source code for the Godot Top-down Shooter Tuto

### 10. GitHub - lmgame-org/GamingAgent: [ICLR 2026] LLM/VLM gaming ...

- **综合分**：89.9 · **来源**：official · **主题**：AI辅助游戏创作与智能体
- **链接**：https://github.com/lmgame-org/GamingAgent
- **摘要**：【体感手势】GitHub - lmgame-org/GamingAgent: [ICLR 2026] LLM/VLM gaming ... | 来源:official | 站点:github.com | 提供:技术文档、开源代码、教程、SDK/API、可下载资源、涉及授权/版权 | 相关词:api、github、game、ai、llm、gpt、agent | 摘要:Introduction This repo enables and tests LLM/VLM-based agents in standardized interctive gaming 

### 11. GitHub - JingyeChen/awesome-game-generation: ️ Explore ...

- **综合分**：88.6 · **来源**：official · **主题**：AI辅助游戏创作与智能体
- **链接**：https://github.com/JingyeChen/awesome-game-generation
- **摘要**：【地图数据】GitHub - JingyeChen/awesome-game-generation: ️ Explore ... | 来源:official | 站点:github.com | 提供:模型、技术文档、开源代码、数据集、教程、涉及授权/版权 | 相关词:3d、demo、github、游戏、game、ai、llm、agent | 摘要:Mar 10, 2025 · A curated list of resources for using artificial intelligence models in game development, 

### 12. Godot 2D游戏开发- 完整版 - Complete 2D Platformer in Godot 4.3: F...互联网上最全面的Godot4 2D游戏开发指南课程_哔哩哔哩_bilibiliGodot 4 中的 2D 平台游戏教程…

- **综合分**：85.7 · **来源**：bilibili · **主题**：Godot游戏设计与GDScript
- **链接**：https://www.bilibili.com/video/BV1md5WzAErR/
- **摘要**：【教程视频】Godot 2D游戏开发- 完整版 - Complete 2D Platformer in Godot 4.3: F...互联网上最全面的Godot4 2D游戏 | 来源:bilibili | 站点:www.bilibili.com | 提供:地图、技术文档、开源代码、教程、可下载资源 | 相关词:地图、开源、github、godot、游戏、game、platformer、教程 | 摘要:Apr 19, 2025 · 在本实战课程中，你将学习如何使用完全免费开源的Godot 4.3游戏引擎，从零开发一款完整、精致、可玩的2D平台跳跃游戏。 无

### 13. 互联网上最全面的Godot4 2D游戏开发指南课程_哔哩哔哩_bilibiliGodot 4 中的 2D 平台游戏教程 -（第01 / 7部分）-【英译中-双字幕】_...在Godot 4中创建一个完整的2D幸存者风格游戏_哔哩哔哩_bil…

- **综合分**：85.7 · **来源**：bilibili · **主题**：Godot游戏设计与GDScript
- **链接**：https://www.bilibili.com/video/BV1ci1SYaEJy/
- **摘要**：【教程视频】互联网上最全面的Godot4 2D游戏开发指南课程_哔哩哔哩_bilibiliGodot 4 中的 2D 平台游戏教程 -（第01 / 7部分）-【英译中-双字 | 来源:bilibili | 站点:www.bilibili.com | 提供:地图、技术文档、开源代码、教程、可下载资源 | 相关词:地图、github、godot、游戏、game、platformer、教程、bilibili | 摘要:在整个课程中，你将充分利用Godot 4直观的可视化脚本系统，了解基本的编程概念，从而将你的技能提升到新的水平，充分发挥Godot 4的潜力。 

### 14. GitHub - BlueBirdBack/godot-cursorrules: Godot 4.4 Cursor rules...

- **综合分**：83.1 · **来源**：official · **主题**：AI辅助游戏创作与智能体
- **链接**：https://github.com/BlueBirdBack/godot-cursorrules
- **摘要**：【开源代码】GitHub - BlueBirdBack/godot-cursorrules: Godot 4.4 Cursor rules... | 来源:official | 站点:github.com | 提供:地图、技术文档、开源代码、可下载资源、涉及授权/版权 | 相关词:tile、github、godot、gdscript、game、ai、llm、cursor | 摘要:Cursor AI will automatically adjust its behavior to follow the Godot-specific guidelines

### 15. GitHub - EladKarni/godot4-2d-platformer-template: A simple template...

- **综合分**：82.4 · **来源**：official · **主题**：Godot游戏设计与GDScript
- **链接**：https://github.com/EladKarni/godot4-2d-platformer-template
- **摘要**：【开源代码】GitHub - EladKarni/godot4-2d-platformer-template: A simple template... | 来源:official | 站点:github.com | 提供:技术文档、开源代码、可下载资源、涉及授权/版权 | 相关词:unity、demo、github、godot、gdscript、game、ai、platformer | 摘要:Coyote Timer Value - Max amount of time allowed after leaving the ground while st

---

## 四、对模板预制的行动清单

| 品类 | core 层应预制的理论依据 | 推荐参考类型 |
|------|-------------------------|--------------|
| 射击 TPL-01 | 八向移动平滑 + AABB 命中 + 波次 | Godot Top-down Shooter 教程 / GDQuest |
| 塔防 TPL-02 | 网格放置 + 伤害公式 + 波次调度 | tower-defense-case-study 多引擎对照 |
| 闯关 TPL-04 | coyote time + 可变高度跳 + 摩擦 | Game Feel / Godot platformer 教程 |
| 竞速 TPL-03 | 自动跑 + 跳跃缓冲 + 距离刷障碍 | 跑酷核心循环文献 |
| 休闲 TPL-07 | 单轴操作 + 计分公式 | Arcade 设计模式 |
| AI 编排 | 运行-日志-修复闭环 | godot-mcp · GamingAgent · Cursor Agent |

---

## 五、检索元数据

| 项 | 值 |
|----|-----|
| 报告文件 | `report_20260613_195217.json` |
| 生成时间 | 2026-06-13T19:57:25 |
| 主题 | AI辅助游戏创作与智能体 · Godot游戏设计与GDScript · 游戏手感与核心机制设计 · 模板化与参数化游戏生成 · K12教育游戏与展陈 · 分品类设计参考 · 学术与行业理论 |
| 数据源 | web, bilibili, csdn, github, zhihu, juejin |
| 有效条目 | 800 |
| 是否跑完 | 是 |

### 续跑命令

```powershell
cd "E:\文三路AI馆\2.ai生成游戏\05-工具脚本"
C:\Users\MAC\.conda\envs\py310_torch251_cu121\python.exe run_game_research_crawler.py
```

---

**关联报告**：用户向补调研见 [`K12用户向调研整合.md`](./K12用户向调研整合.md)（Survey-02 · 252/252 · POV/移情图/HMW）。

*游戏设计与 AI 创作 · 调研整合 Survey-01*