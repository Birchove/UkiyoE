# DailyHotApi 自部署文档(Docker)

> 浮世微言采集管道的数据源。[DailyHotApi](https://github.com/imsyy/DailyHotApi)
> 是一个聚合 60+ 平台热榜的开源服务(知乎 / 微博 / 百度 / 头条 / 抖音 / B站 ……),
> 返回统一 JSON。**本地自部署一个实例**,供 `scripts/crawl.py` 拉取。
>
> 说明:DailyHotApi 只负责「**发现选题**」,抓取结果不直接上站,须经人工筛选与撰写。

---

## 0. 前置

- 已安装 [Docker](https://docs.docker.com/get-docker/)(WSL2 下用 Docker Desktop 即可)。
- 默认端口 **6688**;若被占用,在下面命令里把宿主端口改掉(如 `-p 7788:6688`)。

---

## 1. 部署(三选一)

### 方式 A:直接拉取官方镜像(推荐,最省事)

```bash
docker pull imsyy/dailyhot-api:latest

docker run -d \
  --name dailyhot \
  --restart always \
  -p 6688:6688 \
  imsyy/dailyhot-api:latest
```

### 方式 B:Docker Compose

在项目外任意目录建 `docker-compose.yml`:

```yaml
services:
  dailyhot:
    image: imsyy/dailyhot-api:latest
    container_name: dailyhot
    restart: always
    ports:
      - "6688:6688"
```

然后:

```bash
docker compose up -d      # 旧版用 docker-compose up -d
```

### 方式 C:从源码构建镜像(需要自定义 / 追新时用)

```bash
git clone https://github.com/imsyy/DailyHotApi.git
cd DailyHotApi
docker build -t dailyhot-api .
docker run -d --name dailyhot --restart always -p 6688:6688 dailyhot-api
```

---

## 2. 配置(可选)

- 镜像内置默认配置,一般开箱即用。如需改端口等,可参考仓库根目录的
  `.env.example`:复制为 `.env` 后修改(如 `PORT=6688`),再以
  `-v $(pwd)/.env:/app/.env` 挂载进容器。
- 部分平台(如微博)在公共网络下可能需要 Cookie 才稳定;自部署后若某源长期返回空,
  参阅 DailyHotApi 仓库文档配置对应 Cookie。**采集脚本对单源失败已做隔离,不影响其余源。**

---

## 3. 自测

```bash
# 根路径,应返回接口列表 / 欢迎信息
curl http://localhost:6688/

# 抓取微博热搜,应返回含 data 数组的 JSON
curl http://localhost:6688/weibo
```

返回结构(各源字段略有出入,`crawl.py` 已做兼容):

```json
{
  "code": 200,
  "message": "OK",
  "name": "weibo",
  "title": "微博热搜",
  "total": 50,
  "data": [
    { "title": "词条", "hot": 1234567, "url": "https://...", "index": 1, "type": "热搜" }
  ]
}
```

常用路由:`/weibo` `/zhihu` `/baidu` `/toutiao` `/douyin` `/bilibili`(完整列表见仓库文档)。

---

## 4. 与采集脚本衔接

`scripts/crawl.py` 默认请求 `http://localhost:6688`。若实例在别处(如局域网另一台机器),
用环境变量 `DAILYHOT_API` 指定:

```bash
# 本机默认,无需设置
python3 scripts/crawl.py

# 指向其它实例
DAILYHOT_API=http://192.168.1.10:6688 python3 scripts/crawl.py
```

采集源在 `config/sources.json` 增删(`enabled` 可临时停用某源)。

---

## 5. 常用运维

```bash
docker logs -f dailyhot        # 看日志
docker restart dailyhot        # 重启
docker stop dailyhot && docker rm dailyhot   # 停止并删除
docker pull imsyy/dailyhot-api:latest && docker ... # 升级:重新拉取并重建容器
```

---

## 6. 完整流程(采集 → 过滤 → 看板)

```bash
python3 scripts/crawl.py                 # ① 采集,落盘 data/candidates/今天.json
python3 scripts/filter.py                # ② 过滤/去重,生成 data/board/今天.md 看板
# ③ 打开看板人工勾选选题 → 依 skill fushi-weiyan-writer 撰写 → 审核发布
```

> 全程手动、本地进行;候选 JSON 与看板均在 `data/`(已 git 忽略,不进 GitHub)。
