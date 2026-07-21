# 标准多agents 指令
spawnagents main
需求：log collection & monitoring 都需要部署在 prd 这个namespace 下；测试时还需要在前端浏览器去测试；需要在 这里(http://k8s-cicd.daiyi.local.com:9001/ )添加可跳转按钮，方便我直接跳转；
约束说明：
1. 所有模型请求统一走本地 CC Switch 127.0.0.1:15721 转发 DeepSeek，鉴权由代理托管；
2. 严格遵循团队角色分工：main总控、产品输出PRD、开发实现代码、测试全量校验；
3. 仅main允许调用spawnagents，产品/开发/测试禁止派生任何子代理；
4. 完整流水线：需求梳理→PRD编写→代码开发→测试验收，全部交付物汇总至main输出final_delivery.md；
5. 沙箱权限遵循配置：main/开发完整读写、产品仅写文档、测试只读不修改源码。



# 单独调用单个角色指令（局部修改场景）
## 仅重新梳理产品需求
```md
spawnagents product_manager
需求：完善k8s cicd项目PRD，补充并发构建、资源配额、告警需求
约束：仅输出PRD.md，不编写代码，结果交付main汇总
```
## 仅开发新增模块
```md
spawnagents dev_engineer
前置文档：已完成PRD.md，基于文档新增namespace隔离脚本
约束：输出完整yaml、shell脚本+dev_notes.md，等待main调度测试验证
```

## 仅执行全量回归测试
```md
spawnagents test_engineer
输入文件：项目完整源码 + PRD.md
约束：生成测试用例与缺陷报告，只读模式，禁止修改任何业务代码
```
# 四、并行调度场景（多模块同步开发，在指令中告知 main 启用并行）
```md
spawnagents main
需求：同时开发k8s构建模块、日志收集模块两套独立功能
约束：
1. CC Switch转发DeepSeek，鉴权托管；
2. main并行spawn产品与开发同步推进两套模块；
3. 两套功能完成后统一执行全量测试；
4. 子代理禁止派生其他agent，最终汇总两份交付物统一验收。
```