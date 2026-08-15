# 💪 AI 身材管家

> 你的私人 AI 健身数据管家 —— 基于 Streamlit + DeepSeek + 飞书

## 🎯 核心定位

和豆包等通用 AI 助手的差异：

| 维度 | 豆包 | AI 身材管家 |
|------|------|-------------|
| **数据持久化** | ❌ 聊完就忘 | ✅ 所有数据存在你的飞书表格 |
| **拍照对比** | ❌ 单图分析 | ✅ 跨时间对比 + AI 评分 |
| **进度跟踪** | ❌ 无法看趋势 | ✅ 体重/围度曲线 + AI 月报 |
| **个性化建议** | ⚠️ 通用答案 | ✅ 基于你的档案 + 历史数据 |

---

## 🚀 功能

- 📸 **拍照对比**：上传两张身材照，AI 自动对比变化，给出评分和改进建议
- 💬 **AI 教练**：基于健身知识库的智能问答，有上下文、可引用
- 📋 **训练计划**：输入档案 → AI 生成个性化周训练 + 营养计划
- 🍽️ **饮食记录**：每日卡路里和宏量营养素追踪
- 📊 **我的数据**：体重曲线、围度趋势、AI 月报生成

---

## 📦 项目结构

```
fitness_app/
├── app.py                       # 主页入口
├── pages/                       # 5 个功能页面
│   ├── 1_📸_拍照对比.py
│   ├── 2_💬_AI教练.py
│   ├── 3_📋_训练计划.py        # 借鉴自 quantum-fit
│   ├── 4_🍽️_饮食记录.py
│   └── 5_📊_我的数据.py
├── core/                        # 核心模块
│   ├── config.py               # 配置加载（借鉴自 quantum-fit）
│   ├── ai_client.py            # DeepSeek API 封装
│   ├── feishu_client.py        # 飞书 API 封装
│   ├── prompts.py              # 所有 Prompt 模板
│   ├── plan_generator.py       # 训练计划生成
│   ├── photo_analyzer.py       # 拍照对比分析（核心差异化）
│   └── rag.py                  # 健身知识 RAG
├── data/knowledge/             # RAG 知识库（Markdown）
│   ├── 训练原则.md
│   ├── 动作要领.md
│   ├── 营养基础.md
│   └── 常见问题.md
├── .streamlit/config.toml       # Streamlit 主题
├── .env.example                 # 环境变量示例
├── requirements.txt             # Python 依赖
└── README.md
```

---

## 🛠️ 本地运行

### 1. 准备 API Key

#### DeepSeek API
1. 访问 https://platform.deepseek.com/
2. 注册并实名认证
3. 在「API Keys」创建新 key
4. 充值（一般 ¥5 就够用很久）

#### 飞书配置（可选，没有也能体验 AI 功能）
1. 访问 https://open.feishu.cn/app 创建企业自建应用
2. 添加权限：
   - `bitable:app:readonly` 和 `bitable:app:readonly`
   - `drive:file`
3. 在「飞书工作台」手动创建 5 张多维表格：

#### 表格 1：身体记录
| 字段名 | 类型 |
|--------|------|
| 日期 | 日期 |
| 体重(kg) | 数字 |
| 体脂率(%) | 数字 |
| 胸围(cm) | 数字 |
| 腰围(cm) | 数字 |
| 臀围(cm) | 数字 |
| 臂围(cm) | 数字 |
| 今日照片 | 附件 |
| 备注 | 文本 |

#### 表格 2：训练记录
| 字段名 | 类型 |
|--------|------|
| 日期 | 日期 |
| 训练类型 | 单选（力量/有氧/柔韧/休息）|
| 时长(分钟) | 数字 |
| 动作记录 | 文本 |
| 强度感受 | 单选（轻松/适中/吃力）|
| 备注 | 文本 |

#### 表格 3：饮食记录
| 字段名 | 类型 |
|--------|------|
| 日期 | 日期 |
| 餐次 | 单选（早餐/午餐/晚餐/加餐）|
| 食物 | 文本 |
| 卡路里 | 数字 |
| 蛋白质(g) | 数字 |
| 碳水(g) | 数字 |
| 脂肪(g) | 数字 |
| 备注 | 文本 |

#### 表格 4：AI 对话历史
| 字段名 | 类型 |
|--------|------|
| 时间 | 日期 |
| 角色 | 单选（user/assistant）|
| 会话ID | 文本 |
| 内容 | 文本 |

#### 表格 5：用户档案
| 字段名 | 类型 |
|--------|------|
| 姓名 | 文本 |
| 年龄 | 数字 |
| 性别 | 单选（男/女）|
| 身高(cm) | 数字 |
| 目标 | 单选 |
| 经验水平 | 单选 |
| 每周可用时间 | 数字 |

4. 获取每张表的 table_id（在表格 URL 中能找到）
5. 获取多维表格的 app_token（在多维表格 URL 中）

### 2. 安装和启动

```bash
# 克隆项目
cd /d
mkdir fitness_app && cd fitness_app
# （或 git clone）

# 创建虚拟环境
python -m venv venv
source venv/Scripts/activate  # Windows
# 或 source venv/bin/activate  # Mac/Linux

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入真实的 API Key

# 启动
streamlit run app.py
```

### 3. 浏览器访问

打开 http://localhost:8501 即可使用。

---

## 📱 部署到手机访问

### 推荐：Streamlit Cloud 免费版

1. 把代码推到 GitHub
2. 访问 https://share.streamlit.io/
3. 连接 GitHub 仓库
4. 在「Secrets」里填入 `.env` 的内容
5. 部署完成后会得到一个网址
6. **手机浏览器打开** → 分享按钮 → 添加到主屏幕 → 像 App 一样使用

---

## 💡 使用建议

### 第一次使用
1. 进入「训练计划」→ 生成第一份计划 → 体验 AI 生成能力
2. 进入「AI 教练」→ 随便问个问题 → 体验对话
3. 进入「拍照对比」→ 上传两张照片 → 体验核心差异化功能

### 日常使用
- 每天：饮食记录 + 体重打卡
- 每周：上传身材照 + 训练记录
- 每月：查看 AI 月报 + 调整目标

---

## 🔮 后续规划

- [ ] 拍照食物识别（DeepSeek-Vision）
- [ ] 食物 + 身体状态智能算卡路里
- [ ] 主动推送（微信/邮件提醒）
- [ ] 硬件接入（Apple Health、Mi Band）
- [ ] 多用户支持

---

## 📚 技术栈

- **Streamlit**：Python Web 框架
- **DeepSeek-V3**：国产 LLM，支持 Vision
- **飞书多维表格**：可视化的「数据库」
- **Python 3.8+**

---

## 🙏 致谢

- 借鉴自 [quantum-fit](https://github.com/aditya-raaj/quantum-fit) 的 UI 模式（用 Gemini，现已替换为 DeepSeek）

---

## ⚖️ License

MIT - 自由使用、修改、分发

---

## 💬 反馈

有问题或建议？欢迎提 Issue 或 PR。