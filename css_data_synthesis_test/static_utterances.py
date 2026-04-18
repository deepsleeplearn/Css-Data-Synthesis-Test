from __future__ import annotations

from datetime import time


def demand_text_from_request_type(request_type: str) -> str:
    if request_type == "installation":
        return "安装"
    return "维修"


def appointment_utterance(
    *,
    brand: str,
    category: str,
    request_type: str,
    call_start_time: str,
) -> str:
    _ = category
    _ = demand_text_from_request_type(request_type)
    current = _parse_time(call_start_time)
    if current < time(8, 0, 0):
        return "好的，您的工单已受理成功，上午10点前会有专人与您确认服务时间。"
    if current < time(17, 0, 0):
        if brand not in {"COLMO", "东芝"}:
            return "好的，您的工单已受理成功，2小时内服务人员会电话联系，预约具体上门时间。"
        return "好的，您的工单已受理成功，1小时内服务人员会电话联系，预约具体上门时间。"
    return "好的，您的工单已受理成功，明天上午10点前会有专人与您确认服务时间。"


def fee_collect_utterance(*, request_type: str) -> str:
    if request_type == "installation":
        return "温馨提示，产品首次安装免费，但辅材及改造环境等可能涉及收费，具体以安装人员现场勘查为准。"
    return "温馨提示，如维修服务产生费用，工程师会详细说明并出示收费标准。"


def ask_satisfaction_utterance() -> str:
    return "还需要麻烦您对本次通话服务打分，1、非常满意，2、较满意，3、一般，4、较不满，5、非常不满"


def end_utterance(*, brand: str) -> str:
    if brand == "东芝":
        return "感谢您选择TOSHIBA，再见！"
    if brand == "COLMO":
        return "感谢您选择COLMO，微信关注“COLMO公众号”，更多服务随心享，再见！"
    return "谢谢您的宝贵意见，微信关注“美的官方”，更多服务随心享，再见！"


def _parse_time(value: str) -> time:
    try:
        hour, minute, second = [int(part) for part in str(value).split(":", 2)]
        return time(hour, minute, second)
    except Exception:
        return time(10, 0, 0)
