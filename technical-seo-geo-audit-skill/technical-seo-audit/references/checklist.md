# 技术 SEO / GEO / E-E-A-T 完整检查清单

使用本文件进行深度审计、人工复核或扩展脚本规则。默认按 **P0/P1/P2/P3** 排优先级：P0 为会导致核心页面无法抓取、无法索引或站点不可用的问题；P1 为严重影响索引、重复内容、结构化数据有效性或安全信任的问题；P2 为明显影响搜索理解、展示、抓取效率或用户体验的问题；P3 为优化项、增强项或需要人工判断的策略项。

审计时必须把 **公开抓取可确认的问题**、**需要 GSC/GA4/PageSpeed/日志确认的问题**、**人工内容策略建议** 分开记录。不要把抽样抓取中未发现某项信号直接写成全站不存在；除非已抓取全量 URL 或有权威导出数据。

## 1. 核心技术文件

| 检查项 | 检查标准 | 优先级 | 自动化方式 | 修复方向 |
| --- | --- | --- | --- | --- |
| robots.txt 可访问性 | 根目录 `/robots.txt` 返回 200 或合理 404；生产站不得 5xx、超时或误返回 HTML 错误页。 | P1 | GET `/robots.txt` | 提供 UTF-8 文本文件，确保搜索引擎稳定读取。 |
| robots 禁止规则 | 不得误封首页、产品页、服务页、博客页、文档页、CSS/JS 等渲染必要资源；`User-agent: *` + `Disallow: /` 属 P0。 | P0/P1 | 解析 robots 内容并抽样 URL | 仅禁止后台、搜索结果页、参数垃圾页、隐私资源等无索引价值路径。 |
| robots Sitemap 指令 | 文件中应包含一个或多个完整 `Sitemap:` URL。 | P2 | 正则解析 | 在 robots.txt 底部声明 sitemap index 或 sitemap.xml。 |
| AI 爬虫策略 | 根据业务策略显式声明或至少内部记录 GPTBot、ClaudeBot、PerplexityBot、Google-Extended、CCBot、ChatGPT-User 等允许或限制规则。 | P3 | 正则解析 + 人工判断 | 对希望进入 AI 搜索和引用语境的公开内容应避免误封；对敏感、付费、合规受限内容应显式限制。不要默认认为“全部允许”一定正确。 |
| X-Robots-Tag 与 robots 一致性 | robots 允许抓取的核心页面不应被 HTTP `X-Robots-Tag: noindex` 或页面 meta robots 禁止索引。 | P1 | 抓取页面头部和 HTML | 统一抓取与索引控制，不要用 robots.txt 处理 canonical 或 noindex 目标。 |
| sitemap.xml 存在性 | 大型、新站、图片/视频/新闻丰富站点应提供 Sitemap；小型且内链完整站点可非强制。 | P2 | robots 发现与默认路径探测 | 使用 sitemap index 管理多个 sitemap。 |
| Sitemap 全面性 | 包含所有希望索引的核心规范 URL，包括静态页、产品页、服务页、博客页、文档页。 | P2 | 与抓取样本、CMS 导出、GSC 导出比对 | 缺失模板页或动态页时修复生成逻辑。 |
| Sitemap 准确性 | 不应包含 4xx、5xx、重定向 URL、noindex URL、重复 URL 或非规范 URL。 | P1/P2 | 抽样请求 loc | 仅提交返回 200、可索引、canonical 一致的 URL。 |
| Sitemap 限制 | 单个 Sitemap 不超过 50MB 或 50,000 URL；超出必须拆分。 | P1 | XML 解析和文件大小检查 | 使用 sitemap index。 |
| Sitemap 更新 | 高频更新站点应自动更新 `<lastmod>`，且避免虚假每天刷新。 | P3 | 比对 lastmod 与页面更新时间 | 建立 CMS/构建流程自动生成。 |
| llms.txt 位置 | 根目录 `/llms.txt` 可访问；可选扩展 `/llms-full.txt` 视业务需要提供。 | P3 | GET `/llms.txt` | 对依赖 AI 可读性、文档检索或开发者内容引用的站点建议提供，但不得承诺直接提升排名或 AI 引用。 |
| llms.txt 格式 | Markdown 格式；唯一 H1；H1 后摘要引用块；H2 分组；每组使用 `[标题](URL)` 链接，必要时附简短说明。 | P2/P3 | 文本规则检查 | 链接优先指向干净、信息密集、可抓取版本；确保链接 URL 返回 200 且不被 robots/noindex 阻断。 |
| llms.txt 内容质量 | 引用页面应去除广告、导航噪音、重复内容，并与 robots 允许路径一致。 | P3 | 自动检查 + 人工抽查 | 保持高事实密度、清晰分组、实体名称一致和稳定 URL。 |

## 2. 源代码关键 SEO 标签

| 检查项 | 检查标准 | 优先级 | 自动化方式 | 修复方向 |
| --- | --- | --- | --- | --- |
| Title 唯一性 | 每个可索引页面应有唯一、描述性 `<title>`。 | P1 | 抓取页面并聚合重复 title | 按页面主题、搜索意图和品牌名重写。 |
| Title 长度与关键词 | 通常控制在约 50–60 个英文字符或相近显示宽度，核心词靠前，品牌名可置后。 | P2 | 字符长度检查 | 避免堆砌，确保搜索结果可读。 |
| Meta description | 重要页面应有唯一、自然、有点击吸引力的描述；通常约 120–160 个英文字符或相近显示宽度。 | P2/P3 | 解析 meta | 过长不一定影响排名，但会影响展示可控性。 |
| Meta keywords | 现代 Google 排名基本不依赖该标签；若保留，不应冗长或堆砌。 | P3 | 解析长度 | 可删除或保持极简。 |
| Canonical | 可索引 HTML 页面应声明自引用或首选 URL；使用绝对 URL；避免与 Sitemap、重定向、hreflang 冲突。 | P1/P2 | 解析 `<link rel="canonical">` 和响应头 | 重复页指向主版本，主版本自引用。 |
| H1 | 每页通常一个 H1，准确反映页面主题。 | P2 | 解析 H1 | 多 H1 或缺失 H1 应修复模板。 |
| H2-H6 层级 | 标题层级应逻辑递进，不应频繁跳级；标题应反映下方内容。 | P3 | 解析标题序列 | 将视觉样式与语义标题分离。 |
| 图片 alt | 信息性图片应有描述性 alt；装饰图可空 alt；避免关键词堆砌。 | P2 | 统计 img alt | 补齐产品图、流程图、信息图、文章图。 |
| HTML lang | `<html lang="...">` 准确声明页面主语言。 | P2 | 解析 html 属性 | 多语言站每个版本单独设置。 |
| Open Graph/Twitter Card | 重要落地页、文章页、产品页应配置 title、description、image。 | P3 | 解析 meta property/name | 提升社交与部分预览场景展示质量。 |
| Meta viewport | 移动端页面应存在合理 viewport。 | P2 | 解析 meta viewport | 修复响应式体验与移动可用性。 |

## 3. 结构化数据 Schema

| 类型 | 适用页面 | 关键字段 | 优先级 | 复核重点 |
| --- | --- | --- | --- | --- |
| Organization | 首页、关于页、全站布局 | name、url、logo、sameAs、contactPoint | P2 | 强化品牌实体，不要与页面可见信息冲突。 |
| WebSite | 首页 | name、url、potentialAction（如站内搜索） | P3 | 适合品牌站与内容站。 |
| WebPage | 核心页面 | name、url、description、primaryImageOfPage | P3 | 可辅助页面类型理解。 |
| Product | 产品页 | name、description、image、sku、brand、offers、aggregateRating/review（真实存在时） | P1/P2 | offers、价格、库存、评价必须真实可见。 |
| SoftwareApplication | SaaS/工具页 | name、operatingSystem、applicationCategory、offers、aggregateRating | P2 | SaaS 官网常优先于 Product 或与 Product 配合。 |
| FAQPage | FAQ 或页面中真实问答 | Question、Answer | P3 | 只标记页面可见问答；不要滥用或虚构。Google FAQ 富结果主要面向权威政府/健康站点，但 FAQ 结构仍可提升内容清晰度。 |
| HowTo | 教程、操作指南 | HowToStep、name、text、image（可选） | P3 | 仅适合明确步骤型内容。Google HowTo 富结果展示受限，不应作为唯一优化理由。 |
| BreadcrumbList | 有层级导航页面 | itemListElement、position、name、item | P2 | 与页面面包屑和 URL 层级一致。 |
| Article/BlogPosting | 博客、新闻、报告 | headline、author、datePublished、dateModified、image、publisher | P2 | 作者、日期、图片需可见且真实。 |
| VideoObject | 视频页或含核心视频页面 | name、description、thumbnailUrl、uploadDate、duration、contentUrl/embedUrl | P3 | 若视频是核心内容，应提供转录文本。 |
| Person | 作者页、专家页 | name、jobTitle、sameAs、affiliation | P3 | 支撑 E-E-A-T。 |

结构化数据必须遵循 **页面可见内容一致性** 原则。优先使用 JSON-LD，并用 Rich Results Test、Schema Markup Validator 或 Search Console 增强报告验证。无效 JSON-LD、缺必填字段、评价造假、价格不可见、Schema 类型与页面不匹配应视为高风险问题。

## 4. GSC、GA4 与搜索工具检查

| 检查项 | 检查标准 | 优先级 | 数据来源 | 修复方向 |
| --- | --- | --- | --- | --- |
| GSC 所有权验证 | 验证主域或 URL 前缀属性，覆盖 HTTPS、HTTP、www、non-www，优先使用 Domain Property。 | P1 | GSC | 完成 DNS 或 HTML 等验证。 |
| Sitemap 提交 | 所有 Sitemap 或 sitemap index 已提交且状态正常。 | P1/P2 | GSC/Bing Webmaster Tools | 修复无法抓取、解析错误与提交 URL 异常。 |
| 索引覆盖率 | 定期检查“已抓取 - 尚未编入索引”“已发现 - 尚未编入索引”“重复网页”“替代网页”等。 | P1 | GSC 页面报告 | 按模板、目录、页面类型归因修复。 |
| URL 检查 | 对核心页面确认 Google 可抓取、可索引、canonical 选择正确、渲染资源可访问。 | P1 | GSC URL Inspection | 修复后请求重新索引。 |
| Core Web Vitals | 真实用户数据关注 LCP、INP、CLS；优先移动端问题 URL 组。 | P2 | GSC CWV、CrUX、PageSpeed Insights | 先处理 URL 组共同模板问题。 |
| 安全与人工操作 | 无安全问题、无人工处罚。 | P0/P1 | GSC | 立即处理恶意软件、垃圾内容、黑帽外链等。 |
| 国际定位/hreflang | 多语言站无 hreflang 冲突、缺失返回链、语言代码错误。 | P1/P2 | GSC、爬虫、hreflang checker | 保证自引用、互链、x-default 和 canonical 同语言逻辑。 |
| GA4/GTM | 关键转化、事件、流量来源、站内搜索、表单提交配置正确。 | P2/P3 | GA4/GTM | 保证审计能评估 SEO 流量业务价值。 |

## 5. 高级技术 SEO

| 检查项 | 检查标准 | 优先级 | 自动化方式 | 修复方向 |
| --- | --- | --- | --- | --- |
| HTTPS 强制 | HTTP 版本 301 到 HTTPS；证书有效；无混合内容。 | P0/P1 | 请求 HTTP 与 HTTPS、检查资源 | 配置全站 HTTPS、HSTS、CDN 回源。 |
| URL 规范化 | www/non-www、大小写、尾斜杠、index.html、参数版本统一；内部链接指向规范 URL。 | P1/P2 | URL 变体请求、内链抽样 | 用 301、canonical、内部链接一致性解决。 |
| Hreflang | 多语言/多地区页面应自引用、互相返回、完整 URL、语言/地区代码合法，必要时设置 x-default。 | P1/P2 | 解析 link 或 sitemap | 避免 canonical 指向不同语言版本。 |
| 页面状态码 | 核心页面 200；永久迁移用 301；不存在页面返回 404/410；避免 soft 404。 | P0/P1 | 请求样本 | 修复路由、CMS、重定向策略。 |
| 抓取预算 | 避免大量参数页、过滤页、搜索结果页、重复分页浪费抓取。 | P2 | 爬虫 + 日志/GSC | robots、canonical、nofollow、参数控制配合。 |
| JS 渲染 | 关键内容和链接应在初始 HTML 或可稳定渲染；不要只依赖交互后加载。 | P1/P2 | HTML 与浏览器渲染对比 | 使用 SSR/SSG、预渲染或保证可抓取 API。 |
| 网站速度 | CDN、缓存、图片压缩/WebP/AVIF、懒加载、CSS/JS 压缩、减少第三方脚本、优化 TTFB。 | P2 | PageSpeed、WebPageTest、基础请求 | 优先模板级问题。 |
| 安全头 | HSTS、CSP、X-Content-Type-Options、Referrer-Policy、必要时 X-Frame-Options。 | P2/P3 | 响应头检查 | 在 Web 服务器、CDN 或应用层统一配置。 |
| 自定义 404 | 不存在 URL 返回 404/410，同时展示导航、搜索、热门页面或返回首页入口。 | P1/P3 | 请求随机不存在 URL | 避免 200 soft 404。 |
| 内部链接 | 重要页面应从首页或分类页可达；锚文本描述性；避免孤岛页。 | P1/P2 | 爬虫深度分析 | 优化导航、面包屑、相关文章、HTML sitemap。 |
| 分页/筛选 | 分页可抓取；筛选参数控制索引；避免无限 URL 空间。 | P2 | URL 模式和模板分析 | 使用 canonical、robots、noindex 或参数路由策略。 |

## 6. GEO 与 AI 搜索优化

| 检查项 | 检查标准 | 优先级 | 自动化方式 | 修复方向 |
| --- | --- | --- | --- | --- |
| TL;DR 摘要 | 长篇内容、技术文档、报告开头提供 2–3 句摘要。 | P3 | 文本规则 | 让 AI 和用户快速获取核心结论；这是可读性建议，不是 Google AI Features 的硬性要求。 |
| 独立段落 | 每个段落或小节应自洽，即使被抽取也能表达完整事实。 | P3 | 人工复核 | 减少代词、空泛承接和上下文依赖。 |
| 标题直接回答 | H2/H3 下第一句直接回答该小节问题或定义。 | P3 | 人工复核 | 改写为问答友好结构。 |
| FAQ 模块 | 页面中可加入真实用户常见问题，采用清晰问答对；是否添加 FAQPage Schema 视页面类型决定。 | P3 | HTML/文本解析 | 避免虚构、堆砌和重复。 |
| 实体一致性 | 品牌、产品、人物、公司名在官网、社媒、第三方平台一致。 | P2/P3 | 人工/外部检索 | 用 Organization、Person、sameAs、关于页和第三方资料强化实体，减少 AI 摘要或知识图谱混淆。 |
| 内容新鲜度 | 核心页面标注 Last Updated；过期内容更新或合并。 | P2/P3 | 文本与日期解析 | 对比事实、截图、价格、政策、接口文档。 |
| 信息增益 | 发布原创数据、行业报告、实测结果、案例、对比表。 | P3 | 人工复核 | 增加 AI 引用价值。 |
| 专家审校 | 技术、金融、医疗、法律等高风险内容应有专家作者或审校。 | P2/P3 | 作者块解析 + 人工 | 补充作者资质、履历、sameAs。 |
| 多模态可理解 | 图片有 alt/caption；视频有字幕或转录；图表有文字解释。 | P2/P3 | 页面解析 | 让 AI 可抓取非文本内容中的关键信息。 |

## 7. E-E-A-T 与信任信号

| 维度 | 检查项 | 优先级 | 修复方向 |
| --- | --- | --- | --- |
| Experience | 真实用户案例、成功故事、产品演示、教程、截图、实测过程。 | P3 | 增加具体场景、数据、前后对比和可验证证据。 |
| Expertise | 作者资质、团队背景、技术深度、方法论透明。 | P2/P3 | 建作者页、审校说明、引用权威资料。 |
| Authoritativeness | 行业奖项、认证、媒体报道、权威外链、合作伙伴、知识图谱一致性。 | P3 | 展示真实背书，争取高质量第三方引用。 |
| Trustworthiness | 隐私政策、服务条款、联系方式、地址/邮箱、退款/保障、SSL、第三方评价。 | P1/P2 | 页脚和关于页必须清晰可访问。 |
| 品牌声誉 | 社媒提及、评论平台、G2/Trustpilot/行业论坛评价。 | P3 | 监控并及时响应负面反馈。 |

## 8. 常用工具组合

| 工具 | 主要用途 | 使用建议 |
| --- | --- | --- |
| Google Search Console | 索引、抓取、CWV、安全、增强报告。 | 必用；需要站点权限。 |
| Bing Webmaster Tools | Bing 索引与 Sitemap。 | 对英文站和 AI 搜索生态有价值。 |
| GA4 | 流量、转化、行为分析。 | 与 GSC 数据联动判断业务影响。 |
| GTM | 标签与事件管理。 | 检查是否重复触发或漏记转化。 |
| PageSpeed Insights | Lighthouse 与 CrUX 性能数据。 | 用于 CWV 与性能建议。 |
| Schema Markup Validator / Rich Results Test | 验证结构化数据。 | 部署前后都要验证。 |
| Screaming Frog / Sitebulb | 大规模爬虫审计。 | 用于深度站内结构分析。 |
| Ahrefs / Semrush | 竞争、关键词、外链。 | 补充站外权威与内容差距分析。 |
| Hotjar / Microsoft Clarity | 热图、会话录制。 | 辅助 UX 与转化诊断。 |
| WebPageTest / GTmetrix | 性能瀑布和全球节点。 | 对跨区域站点非常有用。 |

## 9. 官方规则校准要点

Google 官方资料强调，SEO 的目标是帮助搜索引擎理解内容并帮助用户发现网站；robots.txt 主要用于管理抓取流量，而不是隐藏页面；Sitemap 帮助搜索引擎更高效地发现重要 URL，但不保证索引；结构化数据必须描述页面真实可见内容，并优先保证准确完整；Core Web Vitals 当前关注 LCP、INP、CLS；多语言 hreflang 必须自引用、互链并使用完整 URL；图片 SEO 中 alt 文本既帮助可访问性，也帮助 Google 理解图片主题。Google 对 AI Overviews / AI Mode 的站长建议仍以 Search 基础最佳实践、Search 政策、可靠且以人为本的内容为核心，不存在额外保证进入 AI Features 的特殊标签。Skill 使用者应优先以 Google Search Central、web.dev、Schema.org、llms.txt 提案和搜索引擎官方工具的最新文档为准。
