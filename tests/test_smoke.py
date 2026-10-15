"""产品级冒烟测试：验证"整套装配"是否工作。

和单服务测试的本质区别：
  - demo-backend 的 pytest   → 只测后端自己的逻辑（mock，进程内）
  - demo-frontend 的 e2e     → 测 前端→后端 两个服务的连接
  - 本文件                    → 按清单(compose)拉起整个产品后，
                               验证每个容器活着 + 容器之间的网络/DNS/配置都对

冒烟测试不追求覆盖率，只回答一个问题：
  "这个版本的产品能不能正常跑起来、串起来？"
"""

import os

import httpx

# 两个服务的对外访问地址（由 docker-compose.yml 的 ports 映射出来）
FRONTEND = os.getenv("FRONTEND_URL", "http://127.0.0.1:8000")
BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")


def test_backend_container_healthy():
    """后端容器本身活着（清单里钉的这个镜像能启动）

    注意路径是 /api/health：后端的路由都挂在 /api 前缀下，
    和前端的 /health 不一样，别写错（上次超时就是这个原因）。
    """
    resp = httpx.get(f"{BACKEND}/api/health", timeout=10)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_frontend_container_healthy():
    """前端容器本身活着"""
    resp = httpx.get(f"{FRONTEND}/health", timeout=10)
    assert resp.status_code == 200


def test_full_stack_request():
    """核心冒烟：请求穿过整个产品。

    路径：测试进程 → 前端容器(/ask) → 容器内网(http://backend:8010) → 后端容器
    能拿到 from==backend，说明：
      1. 两个镜像版本装配后互相兼容（接口契约没破）
      2. compose 网络、BACKEND_URL 环境变量、DNS 解析全部正确
    """
    resp = httpx.get(f"{FRONTEND}/ask", params={"name": "Product"}, timeout=15)
    assert resp.status_code == 200
    data = resp.json()
    assert data["from"] == "backend", f"请求没有真正走到后端: {data}"
    assert "Hello, Product" in data["message"], f"后端响应内容不对: {data}"
