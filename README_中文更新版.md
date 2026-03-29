# FastAPI 电商后端接口测试项目

一个基于 **FastAPI** 的电商后端项目，并在当前版本中补全为一个更接近真实业务场景的 **后端接口测试项目**。  
项目主线围绕电商核心交易流程展开：

**注册登录 → 商品 → 购物车 → 地址 → 下单 → 支付 → 后台管理**

当前仓库不仅包含电商后端本身，也补充了围绕核心业务链路的自动化测试、CI 执行能力，以及 Redis / Elasticsearch / Prometheus / OpenTelemetry 等配套能力。

---

## 一、项目定位

这个项目不是 UI 自动化项目，核心定位是：

- 基于 FastAPI 的电商后端接口项目
- 面向真实业务链路的接口自动化测试项目
- 重点验证交易主流程、权限控制、异常分支和关键状态流转

当前自动化测试主要覆盖：

- 用户注册、登录、获取个人信息、修改个人信息
- 商品创建、查询、更新、删除
- 登录用户购物车流程
- 游客购物车流程与登录后购物车合并
- 用户地址新增、修改、地址归属校验
- 下单、订单查询、订单详情
- 空购物车下单失败、库存不足下单失败、使用他人地址下单失败
- Stripe 支付意图创建、Webhook 成功/失败回调
- 管理员订单列表、订单状态更新、发货操作
- 普通用户访问后台接口的越权拦截

---

## 二、技术栈

### 后端技术

- **Python 3.10+**
- **FastAPI**
- **SQLAlchemy**
- **Alembic**
- **Pydantic**
- **JWT** 身份认证
- **Redis**
- **Elasticsearch**
- **Stripe**

### 测试与工程化

- **Pytest**
- **FastAPI TestClient**
- **unittest.mock**
- **GitHub Actions**

### 可观测性与配套能力

- **Prometheus**
- **OpenTelemetry**
- **Tempo**
- **Loki**
- **Grafana**
- **Loguru**

---

## 三、当前项目的核心能力

### 1. 用户与认证

- 用户注册
- 用户登录并获取 JWT Token
- 获取当前登录用户信息
- 修改当前用户信息
- 用户地址管理

### 2. 商品能力

- 商品列表查询
- 商品详情查询
- 按 slug 查询商品
- 管理员创建商品
- 管理员更新商品
- 管理员删除商品

### 3. 购物车能力

- 登录用户购物车查询
- 登录用户加入购物车、修改数量、删除商品
- 游客购物车基于 session_id 运作
- 游客登录后购物车自动合并到用户购物车

### 4. 订单能力

- 基于购物车创建订单
- 查询当前用户订单列表
- 查询当前用户单个订单详情
- 下单时校验地址合法性
- 下单后清空购物车
- 下单后扣减商品库存

### 5. 支付能力

- 创建 Stripe Payment Intent
- Webhook 成功回调后更新支付状态与订单状态
- Webhook 失败回调后更新支付失败状态

### 6. 后台管理能力

- 管理员查看订单列表
- 管理员更新订单状态
- 管理员标记订单发货
- 普通用户访问后台接口时进行权限拦截

### 7. 其他已有能力

除当前重点测试的主交易链路外，项目中还保留了以下后端能力：

- 分类管理
- 商品搜索 / 自动补全 / Elasticsearch 集成
- 评论模块
- 收藏夹模块
- 健康检查
- 指标暴露与观测链路集成

---

## 四、测试覆盖说明

当前测试目录为 `tests/`，已经补全为围绕真实业务流程的后端接口测试集。

### 已覆盖测试文件

- `tests/test_auth.py`
- `tests/test_products.py`
- `tests/test_cart.py`
- `tests/test_user_address.py`
- `tests/test_orders.py`
- `tests/test_payments.py`
- `tests/test_admin.py`

### 当前测试重点

#### 认证模块

- 注册成功
- 登录成功
- 错误账号密码登录失败
- 重复邮箱注册失败
- 未登录访问个人信息失败
- 获取当前用户信息成功
- 更新个人信息成功

#### 商品模块

- 管理员创建商品成功
- 商品列表查询成功
- 普通用户创建商品被拒绝
- 按 slug 查询商品成功
- 管理员更新商品成功
- 管理员删除商品成功

#### 购物车模块

- 登录用户空购物车查询
- 登录用户加购成功
- 修改购物车商品数量成功
- 删除购物车商品成功
- 游客访问购物车自动生成 session_id
- 游客加购成功
- 游客登录后购物车合并成功

#### 地址与订单模块

- 用户新增地址成功
- 用户修改地址成功
- 正常下单成功
- 查询订单列表成功
- 查询订单详情成功
- 空购物车下单失败
- 使用他人地址下单失败
- 库存不足时下单失败
- 下单后购物车被清空
- 下单后商品库存被正确扣减
- 其他用户无权查看当前订单

#### 支付模块

- 创建支付意图成功
- 无签名的 Webhook 请求失败
- 对不存在订单创建支付意图失败
- 已支付订单重复支付失败
- 支付成功回调后订单与支付状态更新成功
- 支付失败回调后状态更新成功

#### 后台模块

- 普通用户访问后台订单接口被拒绝
- 管理员查看订单列表成功
- 管理员更新订单状态成功
- 管理员标记订单发货成功

### 当前测试特点

这套测试不是只校验接口状态码，而是进一步校验关键业务结果是否真正落地，例如：

- 注册后校验用户是否真实写入数据库
- 创建商品后校验商品是否真实入库
- 下单后校验订单和订单明细是否生成
- 下单后校验购物车是否清空
- 下单后校验库存是否正确扣减
- 支付成功/失败后校验支付记录与订单状态是否联动更新
- 购物车合并后校验数据库中的购物车归属变化

---

## 五、测试设计思路

为了让测试更稳定、可复用、可在 CI 中直接执行，当前测试做了这些处理：

### 1. 使用独立测试数据库

测试通过 SQLite 内存数据库运行，不依赖本地真实 MySQL 或线上数据库，保证执行快、隔离性强。

### 2. 使用依赖覆盖

通过 FastAPI 的 `dependency_overrides` 替换生产依赖，把测试数据库会话和假的 Redis 注入到应用中。

### 3. Mock 外部依赖

对以下外部依赖做了 Mock 或隔离处理，避免影响测试稳定性：

- Redis 连接
- Elasticsearch 初始化与建索引
- Stripe 接口调用
- Loki 日志发送
- OpenTelemetry trace 导出

### 4. 公共 fixture 复用

在 `tests/conftest.py` 中封装了常用测试夹具，统一处理：

- 用户注册与登录
- 管理员构造
- 商品构造
- 地址创建
- 加购
- 下单
- 订单工厂

这样可以减少样板代码，让每条测试更聚焦于业务断言本身。

---

## 六、项目结构

```text
fastapi-ecommerce/
├── app/
│   ├── api/v1/routes/          # 路由层
│   ├── services/               # 业务逻辑层
│   ├── crud/                   # 数据访问层
│   ├── models/                 # ORM 模型
│   ├── schema/                 # 请求/响应模型
│   ├── core/                   # 配置、日志、Redis、ES 等基础能力
│   ├── middleware/             # 中间件
│   ├── utils/                  # 工具方法
│   ├── db/                     # 数据库连接与 Base
│   └── main.py                 # 应用入口
├── tests/                      # 自动化测试
├── alembic/                    # 数据库迁移
├── .github/workflows/          # CI 工作流
├── docker-compose.yml          # 本地容器编排
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── pytest.ini
└── README.md
```

---

## 七、接口概览

### 用户与地址

- `POST /users/register` 注册
- `POST /users/login` 登录
- `GET /users/me` 获取当前用户信息
- `PUT /users/me` 修改当前用户信息
- `POST /users/me/address` 新增地址
- `PUT /users/me/address/{address_id}` 修改地址

### 商品

- `GET /product` 商品列表
- `GET /product/{slug}` 商品详情
- `POST /product` 创建商品（管理员）
- `PUT /product/{id}` 更新商品（管理员）
- `DELETE /product/{id}` 删除商品（管理员）

### 购物车

- `GET /cart` 查询购物车
- `POST /cart/items` 加入购物车
- `PUT /cart/items/{item_id}` 修改购物车商品数量
- `DELETE /cart/items/{item_id}` 删除购物车商品

### 订单

- `POST /order` 下单
- `GET /order` 查询当前用户订单列表
- `GET /order/{order_id}` 查询当前用户订单详情

### 支付

- `POST /payments/create-intent` 创建支付意图
- `POST /payments/webhook` Stripe Webhook 回调

### 后台

- `GET /admin/orders` 后台订单列表
- `PATCH /admin/orders/{order_id}/status` 修改订单状态
- `PATCH /admin/orders/{order_id}/shipping` 标记发货

---

## 八、快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd fastapi-ecommerce-main
```

### 2. 创建并激活虚拟环境

```bash
python -m venv venv
source venv/bin/activate
```

Windows：

```bash
venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

项目根目录下创建 `.env` 文件，可参考：

```env
DATABASE_URL=sqlite:///./ecommerce.db
JWT_ALGORITHM=HS256
JWT_SECRET_KEY=your-secret-key
REDIS_URL=redis://localhost:6379/0
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
ELASTIC_URL=http://localhost:9200
```

### 5. 执行数据库迁移

```bash
alembic upgrade head
```

### 6. 启动服务

```bash
uvicorn app.main:app --reload
```

启动后可访问：

- Swagger 文档：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`

> 说明：应用在 `main.py` 中设置了 `root_path=/api/v1`，具体部署场景下如果使用反向代理或网关，需要结合实际访问路径确认文档地址。

---

## 九、运行测试

### 本地运行

```bash
pytest -q
```

当前这套测试主要依赖测试内的依赖覆盖与 mock，不要求必须先启动 Redis、Elasticsearch、Stripe 等外部服务。

### 通过 Makefile 运行

```bash
make test
```

---

## 十、CI

项目已补充 GitHub Actions 的 pytest 工作流：

- 触发时机：`push`、`pull_request`
- Python 版本：`3.12`
- 执行命令：`pytest -q --junitxml=pytest-report.xml`
- 产物：上传 `pytest-report.xml`

同时仓库中也保留了 `pylint.yml` 工作流用于基础静态检查。

---

## 十一、Docker 与本地配套环境

项目提供了 `docker-compose.yml`，可拉起以下服务：

- FastAPI App
- Redis
- Elasticsearch
- Kibana
- Loki
- Tempo
- Prometheus
- Grafana

启动：

```bash
docker-compose up -d
```

停止：

```bash
docker-compose down
```

这部分更偏向本地联调、搜索能力和观测链路验证；而当前自动化测试本身通过 mock 隔离了这些外部依赖，因此测试执行不强依赖完整容器环境。

---

## 十二、当前版本总结

相较于原始仓库，当前版本更突出的是“真实业务接口测试项目”这一定位，已经补上了以下关键内容：

- 补全了购物车、地址、订单、支付、后台权限等核心接口测试
- 补全了关键异常流程测试，而不只是 happy path
- 增加了游客购物车与登录后合并这类更贴近业务的场景
- 强化了数据库状态校验，避免只看接口返回
- 增加了 GitHub Actions 中的 pytest 自动执行能力

因此，这个项目当前既可以作为一个 FastAPI 电商后端项目来看，也可以作为一个围绕电商主交易链路设计的后端接口自动化测试项目来看。
