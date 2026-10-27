---
name: frontend-scaffold
description: 用户要新建或初始化前端项目、定技术栈与脚手架配置（Vite/Next、TS、Biome 或 ESLint+Prettier、路由、UI 库等）时使用；输出可落地的配置清单与关键文件要点，不直接写业务页面。
---

# 目标

根据用户约束，给出一套可落地的前端脚手架配置细节：技术选型、目录、关键配置文件内容要点、安装命令、验收标准。

# 先问清（缺什么补什么，已知则跳过）

1. 框架：Vite + React / Vue3，或 Next.js（App Router / Pages）
2. 语言：TypeScript 是否强制
3. 包管理：pnpm / npm / yarn / bun
4. UI：shadcn/ui、Ant Design、无 UI 库等
5. 样式：Tailwind / CSS Modules / UnoCSS
6. 路由与状态：有无需要
7. 部署目标：Vercel / 静态托管 / cloudflare / 其他
8. 约束：Node 版本、要不要 ESLint+Prettier、要不要测试、要不要 i18n

# 输出结构（必须按此顺序）

## 1. 选型结论（3～6 行）
- 框架 + 构建工具 + 语言 + 包管理
- UI / 样式 / 路由 / 状态（不用的写「暂无」）
- 一句「为什么这样选」

## 2. 初始化命令
给出可复制的创建命令（示例）：
- `pnpm create vite@latest <name> --template react-ts`
- `pnpm create next-app@latest <name> --ts --tailwind --eslint --app --src-dir --import-alias "@/*"`
- 随后安装依赖的命令列表

## 3. 推荐目录结构
用树状列出 `src/` 关键目录与职责（components、pages/app、hooks、lib、types、styles 等），注明哪些是可选。

## 4. 关键配置文件细节
对每个会改的文件，写清：**路径、是否新建/改现有、核心字段与推荐值、注意点**。至少覆盖实际用到的：
- `package.json`：scripts（dev/build/lint/preview）、engines
- `tsconfig` / `tsconfig.app`：strict、paths 别名
- Vite：`vite.config`（alias、server.port、proxy 如有）
- Next：`next.config`（如有）、`app` 布局约定
- ESLint / Prettier：规则粒度（先「能跑 + 少吵」） 
- Tailwind：`tailwind.config`、`postcss`、全局 CSS 入口
- 环境变量：`.env.example` 命名约定（`VITE_` / `NEXT_PUBLIC_`）
- Git：`.gitignore` 要点
- 若用 shadcn：初始化命令与 `components.json` 要点
- 仅在用户明确要兼容旧浏览器或指定目标时再给 browserslist / 构建目标
- Ts：写「按需生成 src/vite-env.d.ts 或 next-env.d.ts，不要空造一堆 .d.ts」。

不要整文件无脑粘贴超长默认配置；只写**相对模板的差异与必改项**，必要时给最短可运行片段。

## 5. 依赖清单
分「必装」与「按需」两列，写包名 + 一句用途，避免堆砌。

## 6. 验收清单
勾选式：
- [ ] `dev` 能起
- [ ] `build` 能过
- [ ] 路径别名可用
- [ ] lint（若启用）能跑
- [ ] 环境变量示例齐全

## 7. 不要做的事
- 不生成完整业务页面/CRUD
- 不擅自换成用户没选的框架
- 不引入未说明的重型状态库/微前端
- 配置保持可复制、可粘贴，术语能白话就白话

# 成功标准

用户拿着本 skill 的输出，能在空目录按命令建好项目，并知道每个关键配置改了什么、为什么改。给出的命令必须对应当前包管理器（pnpm/npm/bun），别混用。