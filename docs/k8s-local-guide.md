# 本地 Kubernetes 集群使用指南

> **最后更新**: 2026-07-11 | **K8s 版本**: v1.34.3 | **节点**: 1 (control-plane)

---

## 1. 集群概览

本集群由 **Docker Desktop** 内置的 Kubernetes 提供，运行在本机 WSL Ubuntu 环境之上。

| 项目 | 值 |
|------|-----|
| K8s Server 版本 | v1.34.3 |
| kubectl 版本 | v1.34.1 |
| 容器运行时 | Docker v29.5.3 |
| 节点名称 | `desktop-control-plane` |
| 集群名称 | `docker-desktop` |
| API Server | `https://127.0.0.1:55270` |
| CPU | 24 核 |
| 内存 | ~32 GiB |
| 存储 | ~1 TB ephemeral |

### 核心组件

| 组件 | Namespace | 状态 |
|------|-----------|------|
| `kube-apiserver` | kube-system | ✅ Running |
| `kube-controller-manager` | kube-system | ✅ Running |
| `kube-scheduler` | kube-system | ✅ Running |
| `etcd` | kube-system | ✅ Running |
| `kube-proxy` | kube-system | ✅ Running |
| `CoreDNS` (2副本) | kube-system | ✅ Running |
| `kindnet` (CNI) | kube-system | ✅ Running |
| `local-path-provisioner` | local-path-storage | ✅ Running |

### 默认 StorageClass

| 名称 | 是否默认 | Provisioner | 回收策略 |
|------|----------|-------------|----------|
| `standard` | ✅ | `rancher.io/local-path` | Delete |
| `hostpath` | ❌ | `rancher.io/local-path` | Delete |

---

## 2. 环境准备

### 2.1 kubectl 自动补全 (推荐设置)

将以下内容追加到 `~/.bashrc`:

```bash
source <(kubectl completion bash)
alias k=kubectl
complete -F __start_kubectl k
```

然后执行 `source ~/.bashrc` 生效。

### 2.2 kubectl 配置文件

配置路径: `~/.kube/config`

```yaml
current-context: docker-desktop
apiServer: https://127.0.0.1:55270
```

无需手动干预，Docker Desktop 自动维护。

---

## 3. 常用命令速查

### 3.1 集群状态

```bash
# 查看节点
kubectl get nodes

# 查看节点详情
kubectl describe node desktop-control-plane

# 查看集群信息
kubectl cluster-info

# 查看所有命名空间的 Pod
kubectl get pods -A

# 查看所有命名空间的 Service
kubectl get svc -A
```

### 3.2 工作负载

```bash
# 创建 Deployment
kubectl create deployment <name> --image=<image>:<tag>

# 查看 Deployment
kubectl get deployments

# 查看 Pod
kubectl get pods

# 查看 Pod 日志
kubectl logs <pod-name>
kubectl logs <pod-name> -f          # 实时跟踪

# 进入 Pod 内部
kubectl exec -it <pod-name> -- /bin/sh

# 扩容
kubectl scale deployment <name> --replicas=3

# 删除 Deployment
kubectl delete deployment <name>
```

### 3.3 服务与网络

```bash
# 暴露服务（NodePort 模式）
kubectl expose deployment <name> --port=<port> --type=NodePort

# 查看 Service
kubectl get svc
kubectl get svc -o wide             # 含端口信息

# 删除 Service
kubectl delete svc <name>

# 端口转发（不暴露 Service 时调试用）
kubectl port-forward pod/<pod-name> 8080:80
# 然后访问 http://localhost:8080
```

### 3.4 存储

```bash
# 查看 StorageClass
kubectl get sc

# 创建 PVC
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
EOF

# 查看 PVC
kubectl get pvc

# 删除 PVC
kubectl delete pvc my-pvc

# 在 Deployment 中挂载 PVC
# volumes:
#   - name: data
#     persistentVolumeClaim:
#       claimName: my-pvc
```

### 3.5 配置与密钥

```bash
# 创建 ConfigMap
kubectl create configmap my-config --from-literal=key1=value1
kubectl create configmap my-config --from-file=config.json

# 查看 ConfigMap
kubectl get configmaps
kubectl describe configmap my-config

# 创建 Secret
kubectl create secret generic my-secret --from-literal=password=xxxxx

# ===== 命令行快速创建（不玩 YAML 文件）=====

# 一条命令创建完整应用
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80 --type=NodePort
kubectl get svc nginx             # 看 NodePort 端口 → 浏览器访问

# 从环境变量生成 ConfigMap
kubectl create configmap app-config \
  --from-literal=DB_HOST=localhost \
  --from-literal=DB_PORT=5432 \
  --from-literal=LOG_LEVEL=info

# 给 Deployment 注入环境变量（ConfigMap 方式）
kubectl set env deployment/nginx --from=configmap/app-config

# 直接设环境变量（不需要 ConfigMap）
kubectl set env deployment/nginx DEBUG=true

# 创建带环境变量和挂载卷的 Deployment 最简命令
kubectl create deployment myapp --image=myimage:latest --dry-run=client -o yaml \
  > /tmp/deploy.yaml
kubectl apply -f /tmp/deploy.yaml

# 查看 Secret（值会以 base64 显示，直觉判断是否正确）
kubectl get secret my-secret -o yaml

# 像 Linux 命令行一样操作 Pod
kubectl exec -it <pod> -- ls -la      # 看目录结构
kubectl exec -it <pod> -- cat /etc/config/app.conf   # 看某个文件
kubectl exec -it <pod> -- curl http://localhost:8080/health  # 打健康检查
kubectl exec -it <pod> -- sh           # 进入交互式 shell
kubectl delete pod <pod>              # 删掉 Pod（Deployment 会自动重建）
kubectl scale deployment <name> --replicas=0  # 停掉所有副本
```

### 3.6 其他资源

```bash
# 查看日志
kubectl logs <pod-name> -f

# 查看事件
kubectl get events --sort-by=.metadata.creationTimestamp

# 查看 API 资源列表
kubectl api-resources

# 查看资源 YAML
kubectl get pod <pod-name> -o yaml

# 删除资源
kubectl delete <resource-type> <name>
```

### 3.7 快速测试

```bash
# 启动 nginx
kubectl create deployment test-nginx --image=nginx:latest
kubectl expose deployment test-nginx --port=80 --type=NodePort

# 查看端口
kubectl get svc test-nginx
# 输出示例: test-nginx   NodePort   10.96.x.x   <none>   80:3xxxx/TCP
# 浏览器访问: http://localhost:3xxxx

# 清理
kubectl delete deployment test-nginx
kubectl delete svc test-nginx
```

---

## 4. PV/PVC 快速上手

**核心概念：管理员创建 PV（物理存储），用户创建 PVC（申请存储），Pod 绑定 PVC。**

```bash
# ===== 第一步：创建 PV（管理员操作）=====
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: my-pv
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /data/my-pv       # 数据存在节点本地
  persistentVolumeReclaimPolicy: Retain
EOF

# ===== 第二步：创建 PVC（用户申请 500Mi）=====
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 500Mi        # 只要 500Mi，绑定 my-pv（1Gi）
EOF

# 查看绑定状态
kubectl get pv
kubectl get pvc
# PVC STATUS=Bound 表示绑定成功

# ===== 第三步：Pod 挂载 PVC =====
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: test-pv-pod
spec:
  containers:
    - name: nginx
      image: nginx
      volumeMounts:
        - mountPath: /usr/share/nginx/html
          name: data-vol
  volumes:
    - name: data-vol
      persistentVolumeClaim:
        claimName: my-pvc
EOF

# ===== 验证：写入数据 → 删除 Pod → 新 Pod 读取 =====
kubectl exec test-pv-pod -- sh -c "echo hello > /usr/share/nginx/html/test.txt"
kubectl delete pod test-pv-pod
# 重新创建相同的 Pod，数据仍在

# ===== 清理 =====
kubectl delete pod test-pv-pod
kubectl delete pvc my-pvc
kubectl delete pv my-pv
```

### 4.1 不创建 PV，直接用默认 StorageClass 自动创建

集群有默认 StorageClass `standard`，只创建 PVC 就行：

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: auto-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
EOF

kubectl get pvc
kubectl get pv   # 自动创建了一个 PV 并绑定了
```

---

## 5. Ingress 配置（可选）

Docker Desktop K8s **默认无 Ingress Controller**。如果需要域名路由，安装 nginx-ingress：

```bash
# 安装最新版 nginx-ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml

# 等待就绪
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
```

安装后即可使用 Ingress 资源：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
spec:
  ingressClassName: nginx
  rules:
    - host: myapp.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-service
                port:
                  number: 80
```

访问时绑定 hosts: `127.0.0.1 myapp.local`

---

## 6. 监控仪表盘（可选）

### 6.1 Kubernetes Dashboard

```bash
# 安装 Dashboard
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

# 创建管理员账号（仅供本地使用！）
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin-user
  namespace: kubernetes-dashboard
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-user
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin-user
  namespace: kubernetes-dashboard
EOF

# 获取 Token
kubectl -n kubernetes-dashboard create token admin-user

# 启动代理访问
kubectl proxy
# 浏览器打开: http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/
```

---

## 7. 集群管理

### 7.1 启停集群

K8s 随 Docker Desktop 自动启动。如需手动管理：

- **重启**: Docker Desktop → Settings → Kubernetes → **Reset Kubernetes Cluster**
- **暂停 K8s**: 取消勾选 "Enable Kubernetes"（保留配置）
- **重置 K8s**: Reset Kubernetes Cluster（清除所有数据 ⚠️）

### 7.2 资源限制

```bash
# 对 Deployment 设置资源限制
kubectl set resources deployment <name> --limits=cpu=500m,memory=512Mi --requests=cpu=200m,memory=256Mi
```

### 7.3 排错常用

```bash
# 查看 Pod 事件
kubectl describe pod <pod-name>

# 查看最近事件
kubectl get events --sort-by=.metadata.creationTimestamp | tail -20

# 查看 Pod 日志（包括已崩溃的容器）
kubectl logs <pod-name> --previous

# 调试用临时 Pod
kubectl run -it --rm debug --image=busybox -- sh
```

---

## 8. 与其他方案的对比

| 特性 | 当前 (Docker Desktop K8s) | Minikube | k3s | Kind |
|------|---------------------------|----------|-----|------|
| 安装难度 | 一键勾选 | 简单 | 一条命令 | 一条命令 |
| 占用资源 | 较低 | 中 | 低 | 低 |
| 与生产相似度 | 低 | 中 | 高 | 低 |
| 多节点 | ❌ | ✅ | ✅ | ✅ |
| Ingress 内置 | ❌ | ❌ | ✅ (Traefik) | ❌ |
| 适合场景 | 学习/简单测试 | 学习/开发 | 本地开发/轻量生产 | CI 测试 |

**当前方案建议**: 学习和日常开发够用。后续需要多节点或 CI/CD 模拟时，可考虑切换到 k3s 或 Kind。

---

## 9. 参考链接

- [Kubernetes 官方文档](https://kubernetes.io/docs/home/)
- [kubectl 命令参考](https://kubernetes.io/docs/reference/kubectl/)
- [Docker Desktop K8s 文档](https://docs.docker.com/desktop/kubernetes/)
- [Ingress-Nginx 文档](https://kubernetes.github.io/ingress-nginx/)
