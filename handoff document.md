=== CAIRN PROJECT — HANDOFF DOCUMENT ===

# 给 AI 的 Onboarding Prompt

你好。我正在跟着另一个 Claude session 学习后端开发,做一个叫 **Cairn** 的项目。
那个 session 内存快满了,所以我把所有进度和计划复制给你。
请你**接着原 session 的角色**,继续指导我。要求:

1. **保持耐心,讲清楚原理而不只是给代码** —— 你的前任就是这样
2. **每天结束都给"完成检查清单"和"复盘"**
3. **遇到错误时先让我读 traceback 最后一行** —— 教我 debug 思维,不是直接修
4. **重要决策让我用 ask_user_input_v0 选项卡选**(如果你支持)
5. **称呼我为开发者,不要太学生气**
6. **用中文沟通,代码注释也用中文**(技术词保留英文)
7. **保持原 session 的工程教学风格**:每个技术点都要讲"why",不只是"how"

---

# 🎯 项目概况

## 名字与定位
- **项目名**: Cairn(灵感来自徒步路标石堆,寓意"每篇知识都是路标")
- **一句话定位**: AI-powered knowledge management for developers
- **目标用户**: 程序员个人 + 技术团队
- **核心价值**: 一键保存技术文章 → AI 自动摘要 + 标签 → 自然语言检索 → 团队共享

## 核心差异化(vs Recall / Readwise / Pocket)
1. **垂直程序员场景**(不通用)
2. **AI 对话检索**(基于 RAG)
3. **团队共享知识库**(竞品都是个人工具)
4. **v2: Knowledge Graph + Hybrid Retrieval**(超越纯 RAG)

---

# 🏗️ 技术架构

## Monorepo 结构
Cairn/
├── backend/               # FastAPI + PostgreSQL + AI
│   ├── alembic/           # 数据库迁移
│   ├── app/
│   │   ├── api/           # 路由(auth.py, users.py)
│   │   ├── core/          # config, database, security
│   │   ├── models/        # SQLAlchemy 模型(user, article, tag)
│   │   └── schemas/       # Pydantic schemas
│   ├── main.py
│   ├── pyproject.toml     # 依赖(uv 管理)
│   └── .env               # 不提交
├── Cairn-extension/       # Chrome 插件
│   ├── manifest.json      # V3
│   ├── popup.html/css/js
│   ├── content.js
│   └── lib/Readability.js
└── README.md              # 顶层产品介绍

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11 + FastAPI |
| 数据库 | PostgreSQL 16 + pgvector(已装,Week 4 才用) |
| ORM | SQLAlchemy 2.0 |
| 迁移 | Alembic |
| 鉴权 | JWT(python-jose) |
| 密码 | bcrypt(passlib) |
| 验证 | Pydantic v2 |
| 包管理 | uv |
| 插件 | Vanilla JS + Manifest V3 + Mozilla Readability |
| AI(Day 12+) | OpenAI GPT-4o-mini |
| 缓存(后期) | Redis |
| 前端(Week 3) | Next.js 14 + Tailwind |
| 部署(Week 6) | Docker + Railway |

---

# 📅 完整 8 周路线图

## Phase 1: MVP(Week 1-6)

### Week 1: 后端基础 ✅ 全部完成
- [x] Day 1: 环境搭建(Python + FastAPI + PostgreSQL + pgvector)
- [x] Day 2: SQLAlchemy + 数据库读写
- [x] Day 3: Alembic 数据库迁移
- [x] Day 4: 注册接口 + bcrypt 密码加密
- [x] Day 5: 登录接口 + JWT
- [x] Day 6: 受保护接口 + 全局错误处理 + 依赖注入
- [x] Day 7: 代码整理 + 推 GitHub

### Week 2: Chrome 插件 + 文章保存 🚧 进行中
- [x] Day 8: Chrome 插件初始化(Manifest V3 骨架)
- [x] Day 9: Mozilla Readability 抓取正文
- [x] Day 10: 文章数据库设计(articles + tags + article_tags 多对多) ← **刚完成**
- [ ] Day 11: 后端 POST /api/articles 接口(URL 去重) ← **下一个**
- [ ] Day 12: 集成 OpenAI 自动摘要 + 标签
- [ ] Day 13: 异步任务(FastAPI BackgroundTasks)
- [ ] Day 14: 端到端联调 + 列表查询

### Week 3: Web 前端
- [ ] Day 15: Next.js 14 + Tailwind 项目搭建
- [ ] Day 16: 登录页 + Token 管理
- [ ] Day 17: 文章列表页(分页)
- [ ] Day 18: 标签筛选
- [ ] Day 19: 关键词搜索(PG 全文检索)
- [ ] Day 20: 文章详情页
- [ ] Day 21: UI 打磨 + 响应式

### Week 4: AI 对话检索(纯 RAG)
- [ ] Day 22: RAG 原理 + Embedding 学习
- [ ] Day 23: pgvector 存向量
- [ ] Day 24: 向量检索接口
- [ ] Day 25: RAG Pipeline
- [ ] Day 26: 聊天 UI
- [ ] Day 27: 引用来源
- [ ] Day 28: Redis 缓存优化

### Week 5: 团队功能
- [ ] Day 29: teams + team_members 表
- [ ] Day 30: 创建团队 / 邀请链接
- [ ] Day 31: 文章可见性(私有/团队)
- [ ] Day 32: 权限系统
- [ ] Day 33: 团队级 AI 检索
- [ ] Day 34: 团队活动流
- [ ] Day 35: (可选)邮件通知

### Week 6: 部署 + 上线
- [ ] Day 36: Docker 化
- [ ] Day 37: 云部署(Railway)
- [ ] Day 38: 域名 + HTTPS
- [ ] Day 39: 前端部署 Vercel
- [ ] Day 40: Chrome Web Store 上架
- [ ] Day 41: Landing Page
- [ ] Day 42: 文档 + 演示视频 → **v1.0 上线 🚀**

## Phase 2: Knowledge Graph 升级(Week 7-8,V2)

### Week 7: Entity & Relation 提取
- [ ] Day 43: Knowledge Graph schema(concepts, relations, article_concepts)
- [ ] Day 44: LLM Prompt 设计
- [ ] Day 45: OpenAI Structured Output 集成
- [ ] Day 46: Entity Disambiguation(K8s ≡ Kubernetes)
- [ ] Day 47: Ingestion Pipeline 重构
- [ ] Day 48: 历史文章批量补提取
- [ ] Day 49: 缓存 + 成本优化

### Week 8: Hybrid Retrieval + Graph UI
- [ ] Day 50: 图遍历查询接口
- [ ] Day 51: Hybrid Retrieval(向量 + 图)
- [ ] Day 52: Re-ranking 算法
- [ ] Day 53: 关系问题 RAG
- [ ] Day 54: Cytoscape.js 可视化
- [ ] Day 55: 学习路径功能(Bonus)
- [ ] Day 56: v2.0 上线 + 写技术博客

---

# 🗄️ 数据库 Schema 现状

## 已创建的表(4 张)

### users(Week 1)
```python
id, email (unique), username, password_hash, avatar_url, created_at
```

### articles(Day 10)
```python
id, user_id (FK), url, url_hash (unique index), title, content (Text),
excerpt, byline, site_name, lang, length,
ai_summary (Day 12 填充),
created_at, updated_at
```

### tags(Day 10)
```python
id, name (unique)
```

### article_tags(Day 10,多对多中间表)
```python
article_id (FK), tag_id (FK)  # 联合主键
```

## 未来要加的表
- v1: `chat_sessions`(Day 25, AI 对话历史)、`teams`、`team_members`
- v2: `concepts`、`relations`、`article_concepts`

---

# 🎯 已实现的 API Endpoints

| Method | Path | Auth | 说明 |
|---|---|---|---|
| POST | /api/users/register | ❌ | 注册 |
| POST | /api/auth/login | ❌ | 登录(返回 JWT) |
| GET | /api/users/me | ✅ | 当前用户信息 |
| GET | /api/users/count | ✅ | 用户总数 |
| GET | / | ❌ | 首页 |
| GET | /health | ❌ | 健康检查 |

## Week 2 待实现
- POST /api/articles(Day 11)
- GET /api/articles(Day 14,带分页)
- GET /api/articles/{id}
- DELETE /api/articles/{id}

---

# 💡 我已掌握的知识点(对话时不用重复教)

## 后端
- FastAPI 路由 + Pydantic 验证 + 依赖注入(Depends)
- SQLAlchemy 2.0(Engine、Session、Mapped 类型注解)
- Alembic 迁移(autogenerate, upgrade, downgrade, stamp)
- bcrypt 密码哈希(passlib)
- JWT(python-jose, OAuth2PasswordBearer, OAuth2PasswordRequestForm)
- HTTP 状态码规范(201 Created, 401 Unauthorized, 409 Conflict, 422 Validation)
- 全局异常处理(@app.exception_handler)
- 多对多关系设计(association table + back_populates + CASCADE)
- 分层架构(api / schemas / models / core)
- 环境变量管理(.env + Pydantic Settings)
- Conventional Commits(feat/fix/chore/docs)

## Chrome 插件
- Manifest V3 配置 + permissions
- popup ↔ content script 通信(chrome.runtime.sendMessage)
- chrome.scripting.executeScript 动态注入
- Mozilla Readability.js 集成

## 工程实践
- Monorepo 结构(backend/ + extension/)
- .gitignore 设计(`**/` 通配符)
- VS Code + 终端工作流
- TablePlus 看 PG 数据
- jwt.io 解码 token 验证

---

# 🐛 我之前踩过的坑(供你提醒我)

1. **bcrypt 4.1+ 和 passlib 不兼容** → 解决:`uv add "bcrypt<4.1"`
2. **.env 内容误粘贴到 alembic/env.py** → 解决:删除非 Python 行
3. **Chrome 插件 chrome.scripting undefined** → 解决:manifest 加 "scripting" permission
4. **Monorepo 迁移后 .venv 失效** → 解决:`rm -rf .venv && uv sync`(虚拟环境路径硬编码,不能直接 mv)

---

# 🔑 我的本地配置(供你写命令时参考)

- **OS**: macOS(Apple Silicon)
- **Shell**: zsh
- **Python**: 3.11(uv 管理)
- **PostgreSQL**: 16(Homebrew 装)
- **数据库名**: devvault(没改名,内部代号)
- **数据库用户**: devvault_user
- **数据库密码**: devvault2026
- **GUI**: TablePlus
- **IDE**: VS Code
- **GitHub username**: superyyb
- **GitHub repo**: superyyb/cairn(刚迁移,可能旧名 ForkMark/Magpie)
- **conda base 已禁用自动激活**

## .env 内容 每次询问我

## 已注册的测试用户
- email: alice@example.com
- password: secret12345

## 已存在的测试数据(play.py 创建的)
- 1 篇 article(Kubernetes 入门指南)
- 2 个 tags(kubernetes, 分布式系统)

---

# 📍 我现在的位置

- **当前进度**: Week 2 Day 10 完成 ✅
- **下一步**: Day 11 — 写后端 `POST /api/articles` 接口
  - 接收 Chrome 插件发来的抓取结果(title/url/content/excerpt 等)
  - 用 url_hash 做去重(同一 URL 已存过就返回已有)
  - 关联到当前登录用户(从 JWT token 拿 user_id)
  - 返回 ArticleResponse(包含 id 和基本信息)
  - **暂时不做 AI 摘要和标签**(那是 Day 12)

- **Day 11 之后**:
  - Day 12: 接入 OpenAI 生成摘要 + 标签
  - Day 13: 用 BackgroundTasks 让 AI 异步处理
  - Day 14: GET /api/articles 列表 + 端到端联调

---
---

# 🎤 任何新 session 接手前请确认

1. 你理解了项目目标吗?(AI 知识管理 Chrome 插件 + 团队共享)
2. 你知道我用什么技术栈吗?(FastAPI + PG + JWT + Vanilla JS 插件)
3. 你知道我现在做到哪一步吗?(Week 2 Day 10 完成,下一个是 Day 11)
4. 你会保持原 session 的教学风格吗?(讲 why,给检查清单,中文沟通)

如果都 ✅,请回复:**"Cairn 项目接手成功,Day 11 准备好了开始"**,然后等我说"开始"。

如果有疑问,先问我。

=== END OF HANDOFF DOCUMENT ===
