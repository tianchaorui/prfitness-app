# 🚀 Streamlit Cloud 部署指南

## 📋 前置条件
- ✅ GitHub 账户
- ✅ Streamlit Community Cloud 账户（免费）

---

## 📦 部署步骤

### 1️⃣ 初始化 Git 并推送到 GitHub

```bash
cd d:\fitness_app

# 初始化 Git
git init
git add .
git commit -m "Initial commit: AI 身材管家 Streamlit 应用"

# 添加 GitHub 远程仓库
# 替换 YOUR_USERNAME 和 YOUR_REPO 为你的信息
git remote add origin https://github.com/YOUR_USERNAME/fitness_app.git
git branch -M main
git push -u origin main
```

**GitHub 创建新仓库：**
- 访问 https://github.com/new
- 仓库名：`fitness_app`
- 描述：`AI 身材管家 - 个人健身管理助手`
- 选择 Public（Streamlit Cloud 需要）
- 创建仓库

### 2️⃣ 连接 Streamlit Cloud

1. 访问 https://share.streamlit.io/
2. 用 GitHub 账户登录
3. 点击 **"Create app"**
4. 选择你的 GitHub 仓库：`YOUR_USERNAME/fitness_app`
5. 设置：
   - Branch: `main`
   - File path: `app.py`
   - App URL: https://fitness-app.streamlit.app（自动生成）

### 3️⃣ 配置 Secrets（部署你的 API Key）

在 Streamlit Cloud 部署页面：

1. 点击 **"Advanced settings"**
2. 在 **"Secrets"** 部分粘贴：

```toml
# DeepSeek API
DEEPSEEK_API_KEY = "sk-clesioplbfktnwvgaqlmlypppsypynunzxodlnahdituiudfv"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
```

3. 点击 **"Deploy"**

---

## ✅ 验证部署

部署完成后（通常 2-3 分钟）：
- 访问 https://fitness-app.streamlit.app
- 应该看到和本地一样的界面
- 点击左侧菜单测试各功能

---

## 🔄 更新应用

每次更新代码：

```bash
cd d:\fitness_app
git add .
git commit -m "更新说明"
git push origin main
```

Streamlit Cloud 会自动重新部署（通常 1-2 分钟）。

---

## 💡 常见问题

### Q: 部署时出现"ModuleNotFoundError"
**A:** 检查 `requirements.txt` 是否包含所有依赖，然后 `git push` 重新部署。

### Q: 部署后 API 报错
**A:** 确认 Secrets 中的 `DEEPSEEK_API_KEY` 配置正确。

### Q: 能分享给朋友吗？
**A:** 可以！直接分享 `https://fitness-app.streamlit.app` 的 URL。

### Q: 部署的应用需要付费吗？
**A:** 
- Streamlit Cloud：免费
- DeepSeek API：按 tokens 计费（¥5 充值能用很久）

---

## 📚 更多资源

- [Streamlit Cloud 文档](https://docs.streamlit.io/streamlit-community-cloud)
- [Secrets 管理](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)
- [自定义域名](https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app#use-your-own-domain)
