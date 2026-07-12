"""Generate K8s YAML (Deployment + Service + Ingress) for deploy targets."""
from apps.deploy.models import AppProject

_DEPLOYMENT_TEMPLATE_DJANGO = """---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app: {app_name}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
    spec:
      containers:
        - name: {app_name}
          image: {image}
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: {port}
              protocol: TCP
          env:
            - name: APP_NAME
              value: {app_name}
            - name: APP_TAG
              value: {tag}
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          readinessProbe:
            tcpSocket:
              port: {port}
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            tcpSocket:
              port: {port}
            initialDelaySeconds: 30
            periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app: {app_name}
spec:
  type: ClusterIP
  selector:
    app: {app_name}
  ports:
    - name: http
      port: {port}
      targetPort: {port}
      protocol: TCP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app: {app_name}
spec:
  ingressClassName: nginx
  rules:
    - host: {domain}
      http:
        paths:
          - path: {path}
            pathType: Prefix
            backend:
              service:
                name: {app_name}
                port:
                  number: {port}
"""

_DEPLOYMENT_TEMPLATE_VUE = """---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app: {app_name}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
    spec:
      containers:
        - name: {app_name}
          image: {image}
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: {port}
              protocol: TCP
          env:
            - name: APP_NAME
              value: {app_name}
            - name: APP_TAG
              value: {tag}
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 128Mi
          readinessProbe:
            httpGet:
              path: /
              port: {port}
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /
              port: {port}
            initialDelaySeconds: 15
            periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app: {app_name}
spec:
  type: ClusterIP
  selector:
    app: {app_name}
  ports:
    - name: http
      port: {port}
      targetPort: {port}
      protocol: TCP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app: {app_name}
spec:
  ingressClassName: nginx
  rules:
    - host: {domain}
      http:
        paths:
          - path: {path}
            pathType: Prefix
            backend:
              service:
                name: {app_name}
                port:
                  number: {port}
"""


def generate_k8s_yaml(project: AppProject, image: str) -> str:
    """Generate Deployment + Service + Ingress YAML for a project.

    Args:
        project: AppProject instance
        image: Full image reference, e.g. "my-shop:v1.2.0"

    Returns:
        Multi-document YAML string ready for kubectl apply.

    Raises:
        ValueError: if app_type is unrecognized or required fields are empty.
    """
    if project.app_type not in ("django", "vue"):
        raise ValueError(f"不支持的应用类型: {project.app_type}")
    if not project.app_name or not project.domain or not project.namespace:
        raise ValueError("app_name, domain, namespace 不能为空")

    tag = image.split(":")[-1] if ":" in image else "latest"
    template = _DEPLOYMENT_TEMPLATE_VUE if project.app_type == "vue" else _DEPLOYMENT_TEMPLATE_DJANGO

    return template.format(
        app_name=project.app_name,
        namespace=project.namespace,
        replicas=project.replicas,
        port=project.port,
        domain=project.domain,
        image=image,
        tag=tag,
        path=project.ingress_path or "/",
    )
