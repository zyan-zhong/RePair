# V1.8.5 原生函数签名兼容入口

实际首启在请求发送前触发 FIXED_HEAD_CALLABLE_SIGNATURE_DRIFT:execute_one。原因是进度包装丢失可检查的原生函数签名。此薄入口用 functools.update_wrapper 保留签名；调用原V1.8.5 prepare/run、原G3、原one-shot身份和预算，不覆盖任何已封存包、停止记录或科研资产。

TESTS.py 重现旧签名失败，再验证兼容后原生load_cores成功；零发送。VERIFY.py --server执行原完整预检。RUN.sh后台续跑；STATUS.sh --watch只读常驻进度。已经启动时无需重复RUN。

本入口与V1.8.5主包及执行后完整总账共同交付。Git仍staging only。实际进展以追加执行记录为准。
