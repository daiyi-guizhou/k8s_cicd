# Custom Fluentd image: base elasticsearch daemonset + Kafka (rdkafka2) plugin
FROM fluent/fluentd-kubernetes-daemonset:v1-debian-elasticsearch
USER root
RUN gem install fluent-plugin-kafka --no-document
USER fluent
