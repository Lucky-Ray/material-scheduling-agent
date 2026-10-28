# GitHub 上传操作

首次编写本教程时，项目已初始化 Git，但尚无 commit、远端地址，也未上传。当前仓库地址为 https://github.com/Lucky-Ray/material-scheduling-agent ，以下命令保留作为复现步骤，不要在已有远端时重复执行 remote add。浏览器登录与 Git 命令行认证是两个环节，首次 push 仍可能要求认证。

## 1. 创建空仓库

打开 https://github.com/new ，仓库名可填 `material-scheduling-agent`。可见性由本人选择；私有仓库需按考试要求给指定评审账号读取权限。不要勾选初始化 README、.gitignore 或 License，本地已经包含相关工程文件。创建后复制 HTTPS 仓库地址。

## 2. 本地提交

打开 PowerShell：

```powershell
Set-Location 'E:\Desktop\秋招\小影校招-Agent'
git status --short
git add .
git diff --cached --stat
git commit -m "Add material scheduling agent, tests and documentation"
git branch -M main
```

提交前核对暂存文件：不包含真实密钥、运行数据库、缓存、题目截图。当前 .gitignore 已排除 .env、SQLite 数据库和 Python 缓存。

如果 commit 提示 Author identity unknown，仅为这个仓库设置真实提交身份后重新 commit：

```powershell
git config user.name '你的 GitHub 名称'
git config user.email '你的 GitHub 提交邮箱'
```

邮箱可使用 GitHub Settings → Emails 提供的本人 noreply 地址，不要照抄他人的邮箱。

## 3. 连接并上传

将下方地址替换成创建页面给出的真实地址：

```powershell
git remote add origin https://github.com/你的用户名/material-scheduling-agent.git
git remote -v
git push -u origin main
```

若 Git 提示认证，按已安装的 Git Credential Manager 提供的浏览器登录流程完成。不要将账户密码或 token 发给聊天窗口。若没有弹出浏览器认证，保留错误信息再排查；浏览器已登录本身不证明命令行可用。

若提示 remote origin already exists，先执行 `git remote -v` 核对现有地址；只有确认指向错误仓库时才用 `git remote set-url origin 正确地址` 修改。不要用 force push 绕过历史冲突。

## 4. 确认成功并取得 SHA

```powershell
git status
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

刷新 GitHub 仓库页面，核对 README、src、tests、data、docs 和 examples 都已存在。HEAD 与远端 main 的完整 SHA 应一致。交卷时填写题号 1、仓库页面 URL（通常不含 .git）和最终完整 commit SHA。

## 5. 后续更新

```powershell
git add .
git diff --cached --stat
git commit -m "Update verification evidence"
git push
git rev-parse HEAD
```

更新后要重新获取最终 SHA。上传代码不等于交卷，也不代表已补齐真实模型验证；当前缺口仍以评估报告为准。

官方说明：https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github
