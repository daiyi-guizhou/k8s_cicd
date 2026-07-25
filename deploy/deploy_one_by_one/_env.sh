#!/bin/bash
# deploy/_env.sh — 所有部署/清理脚本共用的环境兼容层
#
# 问题背景:
#   在 Git Bash (MINGW64) 下，若用户环境设置了 MSYS_NO_PATHCONV / MSYS2_ARG_CONV_EXCL
#   （Docker / Git 安装常会设置，或写在 ~/.bashrc），MSYS 会关闭 "/d/xxx -> D:\xxx" 的
#   自动路径转换。而 kubectl.exe / docker.exe 是 Windows 二进制，必须收到 Windows 路径，
#   否则会报 "the path /d/... does not exist"。
#
# 本文件由各 deploy/clean 脚本在 shebang 之后、业务逻辑之前 source 引入，统一处理：
#   1) 恢复 MSYS 默认路径转换（unset 两个变量）
#   2) 兜底：把 docker 强制指到 docker.exe，避免 sh 包装脚本二次转换带来的路径问题
#
# 注意: gateway/start.sh 的 docker run 自带 MSYS_NO_PATHCONV=1 前缀（它用 pwd -W 拿
#       Windows 路径、且容器路径 /etc/nginx/... 不能被转换），与本文件不冲突。

# 1) 恢复 MSYS 默认路径转换：让 /d/xxx 自动转成 D:\xxx 给 Windows 二进制
unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL 2>/dev/null

# 2) 兜底 docker：确保走 docker.exe（Windows 二进制），路径会被正确转换
#    仅当 docker 还不是函数、且 docker.exe 可用时定义
if command -v docker.exe >/dev/null 2>&1 && ! declare -F docker >/dev/null 2>&1; then
  docker() { command docker.exe "$@"; }
  export -f docker
fi

# 3) 安全删除命名空间并确保其真正消失
#    背景: kubectl 1.27+ 的 delete 默认 --wait=true 且无超时，若有资源卡在
#          Terminating（如带 finalizer 的 PVC、LoadBalancer、ingress-nginx），
#          kubectl delete -f <dir> 会永久挂起。这里：
#          - 用 --wait=false 让 delete 立即返回（不阻塞）
#          - 循环强制清空 namespace 的 finalizers，直到该 ns 真正消失（有界 ~90s）
#    用法: k8s_delete_ns <name>
k8s_delete_ns() {
  local ns="$1"
  kubectl delete namespace "$ns" --ignore-not-found --wait=false 2>/dev/null || true
  for _ in $(seq 1 45); do
    if kubectl get ns "$ns" --no-headers 2>/dev/null | grep -q Terminating; then
      kubectl patch namespace "$ns" -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
      sleep 2
    else
      break
    fi
  done
}
