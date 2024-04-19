#!/bin/bash

# 更新 apt 包列表
sudo apt update

# 安装 Node.js v16.20.0 依赖
sudo apt install -y curl gnupg

# 添加 NodeSource 的 GPG key
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/nodesource.gpg

# 添加 Node.js v16.x 的源
echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_16.x $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/nodesource.list > /dev/null

# 更新 apt 包列表，以获取 Node.js v16.x 的包信息
sudo apt update

# 安装 Node.js v16.20.0
sudo apt install -y nodejs

# 验证安装的 Node.js 版本
node --version

# 安装 PM2 全局工具
npm install -g pm2

# 验证 PM2 是否安装成功
pm2 --version

echo "Node.js v16.20.0 和 PM2 已经成功安装！"