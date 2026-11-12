# 从旧版迁移，只保留一个正式入口

目标：modules/loop_b_unified。

## 可以删除的范围

在loop-b-mock分支，新目录已确认上传后，整体删除你之前提交的 modules/loop_b_mock。
它包含旧合同/维护查询、旧日志/升级单、旧私有工单代码、旧工单数据和历史演示结果。新版交接能力在新目录，不靠这些旧文件运行。

不要删除modules本身；不要删除其他组的模块。不能删除dynamic_evidence、modules/confidence_a_mvp、.github、LICENSE或仓库根README。
无需删除或关闭PR #6；在同一分支提交新目录和旧目录删除，仍是该PR的更新。

## 顺序

1. 上传modules/loop_b_unified。
2. 检查GitHub新目录可见，provider_setup.py、README.md、runtime_data和vendor均在。
3. 告知搭档停用旧路径，改用新入口。
4. 在旧目录页面执行整个目录的删除操作，并提交到loop-b-mock。
5. 检查PR的Files changed：应保留其他组原文件，仅移除旧模块并新增统一模块。

如果页面没有整目录删除选项，不要逐个盲删；可以通过Git客户端做目录删除，或把当前界面截图给助手确认下一步。
本地旧包可作为备份留着；不需要再上传到仓库。

## 核对记录

2026-11-13读取GitHub：旧分支提交956e501，PR #6开放；PR #5固定提交8d544b865e19c5bd286e14201af777efb694b81d。
已检查PR5工具入口和相关测试：其通过外部函数注入，没有直接导入modules/loop_b_mock。组员未提交的本地脚本无法核查，迁移通知仍必需。

## 给组员的话

Loop B准备统一到modules/loop_b_unified，工单只用PR5原实现。旧modules/loop_b_mock将在迁移提交中清理，请勿新增旧路径引用。新入口是provider_setup.create_provider()；日志和人工复核包接口见README及UNIFIED_HANDOFF。维护planned/excluded语义仍需规则与审核负责人对齐。
