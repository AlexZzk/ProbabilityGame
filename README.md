# ProbabilityGame

双色球（红 1-33 选 6 + 蓝 1-16 选 1）历史频率分析与预测系统。

## 功能

1. **训练集管理**：单条录入、CSV 批量上传开奖记录。
2. **生成预测**：可指定组数（1-100）和策略，绑定到目标期号。
3. **真实结果回填评估**：录入真实开奖后，自动评估所有以该期为目标的预测，按双色球规则判奖。同时该期数据自动并入训练集，下次预测会用上。
4. **历史频率统计**：可视化红/蓝球冷热分布，支持窗口（最近 N 期）。

### 预测策略
- `frequency_weighted` —— 按历史频率（Laplace 平滑后）加权随机
- `hot` / `cold` —— 最热 / 最冷号
- `balanced` —— 3 热 + 3 冷
- `scarcity` —— 偏好「历史中红球二元对很少同时出现」的稀缺组合
- `random` —— 均匀随机（基线对照）

## 技术栈

- 后端: FastAPI + SQLAlchemy 2 + MySQL 8（`red_balls` 字段用 JSON 列存储）
- 前端: React + Vite + TypeScript
- 部署: docker-compose（MySQL + API）

## 快速开始

```bash
# 启动 DB + API
docker compose up -d --build

# 前端
cd frontend
npm install
npm run dev
# 打开 http://localhost:5173
```

本地直接跑后端（不用 docker）：

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 按需修改 DATABASE_URL
uvicorn app.main:app --reload
```

连接本地已有的 MySQL 时，把 `.env` 里的 `DATABASE_URL` 改成你自己的库即可，格式：

```
mysql+pymysql://<user>:<password>@<host>:3306/<db>?charset=utf8mb4
```

首次启动会自动 `CREATE TABLE`（数据库本身需要先存在）。要求 MySQL ≥ 5.7（依赖 JSON 列类型）。

API 文档: http://localhost:8000/docs

## CSV 格式

```
period,red1,red2,red3,red4,red5,red6,blue,draw_date
2024001,1,5,12,19,22,30,7,2024-01-02
2024002,3,8,14,17,25,28,11,2024-01-05
```

`draw_date` 列可选。

## 数据模型

- `draws` —— 每期真实开奖记录（即训练集）
- `predictions` —— 每次预测调用
- `prediction_items` —— 预测中的每条号码组合，评估字段（红命中数、蓝命中、奖级）在录入对应真实开奖后自动回填

## 后续

- 玩家投注上传 + 组合冷门度排序（当前预留 `scarcity` 策略框架，可扩展）
- 模型评估指标（不同策略历次命中率对比）
