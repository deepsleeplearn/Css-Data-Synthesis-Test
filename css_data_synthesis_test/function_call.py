from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import phonenumbers
import re
import sys
import time
from typing import Any, Mapping, Sequence

import jwt as pyjwt
import requests

from css_data_synthesis_test.config import load_config
from css_data_synthesis_test.llm import OpenAIChatClient


logger = logging.getLogger(__name__)

DEFAULT_ENV = "prod"
DEFAULT_FILTER_CONDITION = "CONDITION_1"
DEFAULT_CC_API_VERSION = "V2"
DEFAULT_CC_ADDRESS_API_TIMEOUT = "2"

PROD_CC_API_CONFIG = {
    "V1": (
        "https://apiprod.midea.com/C-CC/c-cc-api-service/cc/map/queryAddrForMcp",
        "cd60636051bd433db9bba2283e9bdb11",
        "cb58c8d1c0f84821ba418daad63884b0",
    ),
    "V2": (
        "https://apiprod.midea.com/C-CC/c-cc-api-service/cc/map/queryAddrForAIGC",
        "cd60636051bd433db9bba2283e9bdb11",
        "cb58c8d1c0f84821ba418daad63884b0",
    ),
}

ENV = os.environ.get("ENV", DEFAULT_ENV)
FILTER_CONDITION = os.environ.get("FILTER_CONDITION", DEFAULT_FILTER_CONDITION)
CC_API_VERSION = os.environ.get("CC_API_VERSION", DEFAULT_CC_API_VERSION)
CC_API_URL = os.environ.get("CC_API_URL", "").strip()
CC_API_KEY = os.environ.get("CC_API_KEY", "").strip()
CC_API_SECRET = os.environ.get("CC_API_SECRET", "").strip()
CC_ADDRESS_API_TIMEOUT = float(os.environ.get("CC_ADDRESS_API_TIMEOUT", DEFAULT_CC_ADDRESS_API_TIMEOUT))


def _resolve_address_api_config() -> tuple[str, str, str]:
    if CC_API_URL and CC_API_KEY and CC_API_SECRET:
        return CC_API_URL, CC_API_KEY, CC_API_SECRET

    if ENV in {"prod", "prod-gray"}:
        if CC_API_VERSION == "V1":
            return (
                "https://apiprod.midea.com/C-CC/c-cc-api-service/cc/map/queryAddrForMcp",
                "cd60636051bd433db9bba2283e9bdb11",
                "cb58c8d1c0f84821ba418daad63884b0",
            )
        return (
            "https://apiprod.midea.com/C-CC/c-cc-api-service/cc/map/queryAddrForAIGC",
            "cd60636051bd433db9bba2283e9bdb11",
            "cb58c8d1c0f84821ba418daad63884b0",
        )

    if ENV in {"uat", "uat-gray"}:
        if CC_API_VERSION == "V1":
            return (
                "https://apiuat.midea.com/C-CC/c-cc-api-service/cc/map/queryAddrForMcp",
                "3fe0d27f79a84be7b65883f035fe35e1",
                "b552380145574158b3578a59d863c81e",
            )
        return (
            "https://apiuat.midea.com/C-CC/c-cc-api-service/cc/map/queryAddrForAIGC",
            "3fe0d27f79a84be7b65883f035fe35e1",
            "b552380145574158b3578a59d863c81e",
        )

    if CC_API_VERSION == "V1":
        return (
            "https://apisit.midea.com/C-CC/c-cc-api-service/cc/map/queryAddrForMcp",
            "c6c5419cb5364e83ac684c72a5bb8ee9",
            "cd963357579d44ef80fc31436eead67b",
        )
    return (
        "https://apisit.midea.com/C-CC/c-cc-api-service/cc/map/queryAddrForAIGC",
        "c6c5419cb5364e83ac684c72a5bb8ee9",
        "cd963357579d44ef80fc31436eead67b",
    )


API_URL, API_KEY, API_SECRET = _resolve_address_api_config()
ADDRESS_QUESTION_REGEX = re.compile(
    r"(哪个镇)|(完整的说下省)|(详细的地址)|(详细地址)|(地址在)|(地址是)|(请问您的地址)|"
    r"(地址是哪)|(请问地址)|(具体地址是)|(具体地址在)|(城市是哪里)|(街道在哪里)|"
    r"(哪个区)|(哪个街道)|(哪个乡镇)|(哪个小区)|(门牌号)"
)
ADDRESS_CONFIRMATION_REGEX = re.compile(r"(确认)|(核对)|(地址.*吗)|(地点.*吗)|(位置.*吗)|(后台)|(系统)")
ADDRESS_CONFIRMATION_PATTERNS = (
    re.compile(
        r"^(?:机器人|客服)：.*?(?:本次服务地址|服务地址|地址).*?[：:]?\|?(.+?)\|?[，,]?(?:对吗|是吗|对不对|可以吗)\??？?$"
    ),
    re.compile(
        r"^(?:机器人|客服)：.*?确认.*?(?:地址|地点|位置).*?[：:]?\|?(.+?)\|?[，,]?(?:对吗|是吗|对不对|可以吗)\??？?$"
    ),
)

DEFAULT_SPLIT_TOKEN = "+"
IE_PROMPT_TEMPLATE = """
请从以下用户与客服之间的语音对话中提取关键信息，并按照给定的示例严格遵从以JSON格式输出，不需要任何其他补充文本。

**通用规则**：
1.如果某个字段的信息在对话中未提及或不符合白名单范围，则其值必须为空字符''。
2.如果某个字段的取值存在多个值，则多个取值之间使用'|'分割。

**字段具体要求**：
{key_maps}

**输出格式示例**：
{examples}
"""

COPIED_CUSTOMER_AGENT_KEYS_CONFIG = {
    "familyName": {
        "description": "<用户的姓氏，string类型>",
        "rule": "用户的姓氏，通常是用户名字的第一个汉字或前两个汉字（即复姓）。",
    },
    "contactNumber": {
        "description": "<用户的联系电话号码，string类型>",
        "rule": "用户的联系电话号码，通常是手机号码或座机号码，一般由数字组成，不包含其他符号（如空格、中划线）。",
    },
    "serviceAddress": {
        "description": "<用户的上门服务地址，string类型>",
        "rule": "用户的上门服务地址，通常由省、市、区/县、乡镇/街道和详细地址组成。",
    },
    "productModel": {
        "description": "<产品型号，string类型>",
        "rule": "产品型号，通常是产品的唯一标识，通常由字母、数字和符号组成。若某型号没有被用户确认，则该字段必须输出空字符''。",
    },
    "productCategory": {
        "description": "<产品品类，string类型>",
        "rule": "产品品类，通常是指用户已确认需要服务的家电产品大类。若某品类没有被用户确认，则该字段必须输出空字符''。",
    },
}

COPIED_CUSTOMER_AGENT_ADDRESS_PROMPT = (
    "你是一个顶级的地址信息处理专家。你的任务是分析【机器人】和【用户】之间的对话，并根据用户的回应，"
    "严格遵循以下规则，推断出最终的、最准确的地址。#核心规则"
    "用户肯定:如果用户使用“嗯”、“对”、“是的”等词语或未提出异议，最终地址应为【机器人】提供的完整地址。"
    "用户补充/追加:如果用户在机器人地址的基础上补充了额外信息（如小区名、楼栋号），最终地址应是【机器人】地址和【用户】补充信息的无缝结合。"
    "用户否定/移除:如果用户明确否定了地址的某个部分（如“不是这个村”），并且没有提供新的信息，则应将该部分及之后的所有信息从地址中移除。"
    "用户更正/替换(截断规则):当用户对地址的任何部分（无论是省、市、区、街道、路名、小区名，还是门牌号）进行更正或替换时，"
    "最终地址应采纳用户的更正，并丢弃机器人原地址中位于被更正层级之后的所有信息。"
    "-例外：如果用户提供了一个全新的、结构完整的地址，则完全采纳用户的新地址。"
    "用户澄清/选择:如果【机器人】提供的地址中包含重复或冲突的同级地址信息，而【用户】的回应明确指出了其中一个，"
    "那么最终地址应采纳用户指出的部分，并移除其他冲突的同级地址。"
    "无法判断:如果用户的回答语义模糊、答非所问、没有听清，最终地址应为“无法判断”。"
    "#输出要求你的回答必须且只能是一个严格的JSON格式字符串。绝对不要包含任何JSON之外的文字、解释、理由或代码块标记(例如json...)。"
    "最终格式必须是：{\"serviceAddress\":\"提取出的最终地址或'无法判断'\"}"
)


def create_jwt(key: str, secret: str) -> str:
    current_time = int(time.time())
    expiration_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": key,
        "nbf": current_time,
        "exp": int(expiration_time.timestamp()),
    }
    return pyjwt.encode(payload=payload, key=secret, algorithm="HS256", headers=header)


def _normalize_turn_text(turn: Any) -> str:
    if isinstance(turn, str):
        return turn.strip()
    speaker_attr = getattr(turn, "speaker", None)
    text_attr = getattr(turn, "text", None)
    if speaker_attr is not None or text_attr is not None:
        speaker = str(speaker_attr or "").strip()
        text = str(text_attr or "").strip()
        if speaker and text:
            return f"{speaker}：{text}"
        return text
    if isinstance(turn, Mapping):
        speaker = str(
            turn.get("speaker")
            or turn.get("role")
            or turn.get("from")
            or turn.get("name")
            or ""
        ).strip()
        text = str(
            turn.get("text")
            or turn.get("content")
            or turn.get("utterance")
            or turn.get("message")
            or ""
        ).strip()
        if speaker and text:
            return f"{speaker}：{text}"
        return text
    return str(turn or "").strip()


def _dialogue_lines(dialogue: Sequence[Any] | str) -> list[str]:
    if isinstance(dialogue, str):
        return [line.strip() for line in dialogue.splitlines() if line.strip()]
    return [line for line in (_normalize_turn_text(turn) for turn in dialogue) if line]


def _dialogue_text(dialogue: Sequence[Any] | str) -> str:
    return "\n".join(_dialogue_lines(dialogue))


def _get_llm_client() -> OpenAIChatClient:
    return OpenAIChatClient(load_config())


def _map_local_entity_type_to_customer_agent(entity_type: str) -> str:
    mapping = {
        "address": "serviceAddress",
        "addressInfo": "serviceAddress",
        "telephone_number": "contactNumber",
        "telephone": "contactNumber",
        "last_name": "familyName",
        "product_model": "productModel",
        "product_category": "productCategory",
        "all": "all",
    }
    return mapping.get(entity_type, entity_type)


def _gen_copied_key_maps(entity_types: list[str] | str) -> str:
    if entity_types == "all":
        keys = list(COPIED_CUSTOMER_AGENT_KEYS_CONFIG.keys())
    else:
        keys = list(entity_types)
    return "".join(
        f"- **{key}**:\n{COPIED_CUSTOMER_AGENT_KEYS_CONFIG[key]['rule']}\n"
        for key in keys
        if key in COPIED_CUSTOMER_AGENT_KEYS_CONFIG
    )


def _gen_copied_examples(entity_types: list[str] | str) -> str:
    if entity_types == "all":
        keys = list(COPIED_CUSTOMER_AGENT_KEYS_CONFIG.keys())
    else:
        keys = list(entity_types)
    examples = {
        key: COPIED_CUSTOMER_AGENT_KEYS_CONFIG[key]["description"]
        for key in keys
        if key in COPIED_CUSTOMER_AGENT_KEYS_CONFIG
    }
    return json.dumps(examples, ensure_ascii=False)


def _get_copied_customer_agent_sys_prompt(entity_type: str) -> str:
    mapped_entity_type = _map_local_entity_type_to_customer_agent(entity_type)
    if mapped_entity_type == "serviceAddress":
        return COPIED_CUSTOMER_AGENT_ADDRESS_PROMPT
    entity_types: list[str] | str
    if mapped_entity_type == "all":
        entity_types = "all"
    else:
        entity_types = mapped_entity_type.split(DEFAULT_SPLIT_TOKEN)
    return IE_PROMPT_TEMPLATE.format(
        key_maps=_gen_copied_key_maps(entity_types),
        examples=_gen_copied_examples(entity_types),
    )


def _normalize_customer_agent_ie_response(
    entity_type: str,
    response: Mapping[str, Any] | None,
) -> dict[str, Any]:
    normalized = dict(response or {})

    if entity_type in {"address", "addressInfo"}:
        normalized["address"] = str(
            normalized.get("serviceAddress")
            or normalized.get("address")
            or ""
        ).strip()
    elif entity_type in {"telephone", "telephone_number"}:
        normalized["telephone_number"] = str(
            normalized.get("contactNumber")
            or normalized.get("telephone_number")
            or normalized.get("telephone")
            or ""
        ).strip()
    elif entity_type == "last_name":
        normalized["last_name"] = str(
            normalized.get("familyName")
            or normalized.get("last_name")
            or ""
        ).strip()
    elif entity_type == "product_model":
        normalized["product_model"] = str(
            normalized.get("productModel")
            or normalized.get("product_model")
            or ""
        ).strip()
    elif entity_type == "product_category":
        normalized["product_category"] = str(
            normalized.get("productCategory")
            or normalized.get("product_category")
            or ""
        ).strip()
    elif entity_type == "all":
        normalized["telephone_number"] = str(
            normalized.get("contactNumber")
            or normalized.get("telephone_number")
            or normalized.get("telephone")
            or ""
        ).strip()
        normalized["address"] = str(
            normalized.get("serviceAddress")
            or normalized.get("address")
            or ""
        ).strip()
        normalized["product_model"] = str(
            normalized.get("productModel")
            or normalized.get("product_model")
            or ""
        ).strip()
        normalized["product_category"] = str(
            normalized.get("productCategory")
            or normalized.get("product_category")
            or ""
        ).strip()
        normalized["last_name"] = str(
            normalized.get("familyName")
            or normalized.get("last_name")
            or ""
        ).strip()

    return normalized


def _ie_instruction(entity_type: str) -> str:
    return _get_copied_customer_agent_sys_prompt(entity_type)


def ie(
    context: Sequence[Any] | str,
    entity_type: str,
    *,
    client: OpenAIChatClient | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    dialogue_text = _dialogue_text(context)
    llm_client = client or _get_llm_client()
    resolved_model = model or llm_client.config.default_model
    messages = [
        {"role": "system", "content": _ie_instruction(entity_type)},
        {"role": "user", "content": f"<conversation>\n{dialogue_text}\n</conversation>"},
    ]
    response = llm_client.complete_json(
        model=resolved_model,
        messages=messages,
        temperature=0,
        max_tokens=400,
    )
    return _normalize_customer_agent_ie_response(entity_type, response)


def extract_address_from_confirmation(text: str) -> str:
    normalized = str(text or "").strip()
    for pattern in ADDRESS_CONFIRMATION_PATTERNS:
        match = pattern.fullmatch(normalized)
        if match:
            return match.group(1).strip(" |，,。")
    return ""


def extract_history_address(dialogue_history: Sequence[Any]) -> str:
    for turn in reversed(list(dialogue_history)):
        utterance = _normalize_turn_text(turn)
        if not utterance:
            continue
        if "机器人" not in utterance and "客服" not in utterance:
            continue
        address = extract_address_from_confirmation(utterance)
        if address:
            return address
    return ""


def extract_user_info(
    dialogue: Sequence[Any] | str,
    *,
    client: OpenAIChatClient | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    response = ie(dialogue, "all", client=client, model=model)
    address_response = ie(dialogue, "address", client=client, model=model)
    response["address"] = str(address_response.get("address") or "").strip()
    response["history_address"] = extract_history_address(_dialogue_lines(dialogue))
    return response


def extract_address_from_text(
    text: Sequence[Any] | str,
    *,
    client: OpenAIChatClient | None = None,
    model: str | None = None,
) -> str:
    response = ie(text, "address", client=client, model=model)
    return str(response.get("address") or "").strip()


def simplify_municipality_address(address: str) -> str:
    simplified = str(address or "")
    for city in ("北京", "上海", "天津", "重庆"):
        simplified = re.sub(f"({city}市){city}市", r"\1", simplified)
        simplified = re.sub(f"({city}){city}市", f"{city}市", simplified)
        simplified = re.sub(f"({city}市){city}市辖区", r"\1", simplified)
        simplified = re.sub(f"({city}市)辖区", r"\1", simplified)
    return simplified


def simplify_address_for_confirmation(address: str) -> str:
    simplified = simplify_municipality_address(address)
    simplified = simplified.replace("广西壮族自治区", "广西")
    simplified = simplified.replace("新疆维吾尔自治区", "新疆")
    simplified = simplified.replace("内蒙古自治区", "内蒙古")
    return simplified


def is_ask_address(content: str) -> bool:
    return bool(ADDRESS_QUESTION_REGEX.search(str(content or "")))


def maybe_address_confirmation(content: str) -> bool:
    return bool(ADDRESS_CONFIRMATION_REGEX.search(str(content or "")))


def convert_json_format_v1(response: Mapping[str, Any], raw_address: str) -> dict[str, Any]:
    address_data = response.get("data", {}) if isinstance(response, Mapping) else {}
    if not address_data:
        return {
            "message": f"请求地址标准化失败，原因：{response.get('errorList', []) if isinstance(response, Mapping) else []}",
            "code": 510,
            "status": "fail",
            "data": {"raw_address": raw_address},
        }

    is_addr_complete = address_data.get("isAddrComplete", "")
    sf_addr_vo = address_data.get("sfAddrVO")
    gis_addr_vo = address_data.get("gisAddrVO")
    if not sf_addr_vo:
        return {
            "message": "请求地址标准化失败，原因：调用丰图地址失败",
            "code": 510,
            "status": "fail",
            "data": {"raw_address": raw_address},
        }
    if not sf_addr_vo and not gis_addr_vo:
        return {
            "message": "请求地址标准化失败，原因：缺少足够的地址信息",
            "code": 510,
            "status": "fail",
            "data": {"raw_address": raw_address},
        }
    if is_addr_complete and not gis_addr_vo:
        logger.error("地址标准化返回错误，原因：gisAddrVO is NULL and isAddrComplete=True")

    if is_addr_complete and gis_addr_vo:
        province_code = gis_addr_vo.get("provinceCode") or ""
        city_code = gis_addr_vo.get("cityCode") or ""
        county_code = gis_addr_vo.get("countyCode") or ""
        town_code = gis_addr_vo.get("countryCode") or ""
        area_code = gis_addr_vo.get("areaNumber") or ""
        detail_addr = gis_addr_vo.get("address") or ""
        province = gis_addr_vo.get("province") or ""
        city = gis_addr_vo.get("city") or ""
        county = gis_addr_vo.get("county") or ""
        town = gis_addr_vo.get("countryName") or ""
        road = gis_addr_vo.get("road") or ""
        address = province + city + county + town + detail_addr
        res_data = {
            "raw_address": raw_address,
            "address": address,
            "province": province,
            "province_code": province_code,
            "city": city,
            "city_code": city_code,
            "county": county,
            "county_code": county_code,
            "town": town,
            "town_code": town_code,
            "road": road,
            "detail": detail_addr,
            "area_code": area_code,
            "isAddrComplete": is_addr_complete,
        }
    else:
        province_code = "1" + (sf_addr_vo.get("provinceCode") or "")[:-4]
        city_code = "1" + (sf_addr_vo.get("cityLevCode") or "")[:-2]
        county_code = "1" + (sf_addr_vo.get("countyCode") or "")
        town_code = "1" + (sf_addr_vo.get("townCode") or "")[:-3]
        area_code = "0" + (sf_addr_vo.get("citycode") or "")
        detail_addr = sf_addr_vo.get("detailAddr") or ""
        province = sf_addr_vo.get("province") or ""
        city = sf_addr_vo.get("city") or ""
        county = sf_addr_vo.get("county") or ""
        town = sf_addr_vo.get("town") or ""
        road = sf_addr_vo.get("road") or ""
        address = province + city + county + town + detail_addr
        res_data = {
            "raw_address": raw_address,
            "address": address,
            "province": province,
            "province_code": province_code,
            "city": city,
            "city_code": city_code,
            "county": county,
            "county_code": county_code,
            "town": town,
            "town_code": town_code,
            "road": road,
            "detail": "",
            "area_code": area_code,
            "isAddrComplete": is_addr_complete,
        }

    return {"message": "success", "code": 200, "status": "success", "data": res_data}


def convert_json_format_v2(response: Mapping[str, Any], raw_address: str) -> dict[str, Any]:
    address_data = response.get("data", {}) if isinstance(response, Mapping) else {}
    if not address_data:
        return {
            "message": f"请求地址标准化失败，原因：{response.get('errorList', []) if isinstance(response, Mapping) else []}",
            "code": 510,
            "status": "fail",
            "data": {"raw_address": raw_address},
        }

    is_addr_complete = address_data.get("isAddrComplete", "")
    sys_addr_vo = address_data.get("sysAddrVO")
    if not sys_addr_vo:
        return {
            "message": f"请求地址标准化失败，原因：{response.get('errorList', []) if isinstance(response, Mapping) else []}",
            "code": 510,
            "status": "fail",
            "data": {"raw_address": raw_address},
        }

    res_data = {
        "raw_address": raw_address,
        "address": simplify_municipality_address(sys_addr_vo.get("address") or ""),
        "from": sys_addr_vo.get("addressType") or "",
        "valid_code_flag": sys_addr_vo.get("pubValidly") or "",
        "province": sys_addr_vo.get("province") or "",
        "province_code": sys_addr_vo.get("provinceCode") or "",
        "city": sys_addr_vo.get("city") or "",
        "city_code": sys_addr_vo.get("cityLevCode") or "",
        "county": sys_addr_vo.get("county") or "",
        "county_code": sys_addr_vo.get("countyCode") or "",
        "town": sys_addr_vo.get("town") or "",
        "town_code": sys_addr_vo.get("townCode") or "",
        "road": sys_addr_vo.get("road") or "",
        "detail": sys_addr_vo.get("detailAddr") or "",
        "area_code": sys_addr_vo.get("citycode") or "",
        "isAddrComplete": is_addr_complete,
    }
    return {"message": "success", "code": 200, "status": "success", "data": res_data}


def convert_address_mcp_format(
    address: str,
    post_result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    resp_data = post_result.get("data", {}) if isinstance(post_result, Mapping) else {}
    is_addr_complete = bool(resp_data.get("isAddrComplete", False))
    detail_address = str(resp_data.get("detail") or "")
    province = str(resp_data.get("province") or "")
    city = str(resp_data.get("city") or "")
    county = str(resp_data.get("county") or "")
    town = str(resp_data.get("town") or "")
    town_code = str(resp_data.get("town_code") or "")
    county_code = str(resp_data.get("county_code") or "")
    area_num = str(resp_data.get("area_code") or "")
    parent_area_name = "".join([province, city, county])
    area_name = "".join([province, city, county, town])
    std_address = str(resp_data.get("address") or "")

    if is_addr_complete:
        status = "success"
        message = "已成功获取完整地址"
        std_address = str(resp_data.get("address") or "")
    elif province and city and county and town and not detail_address:
        status = "fail"
        message = "已成功获取四级地址，缺少详细地址信息"
        std_address = str(resp_data.get("address") or "")
    elif province and city and county and not town and detail_address:
        status = "fail"
        message = "缺少乡镇或街道"
        std_address = str(resp_data.get("address") or "")
    elif province and city and county and not town and not detail_address:
        status = "fail"
        message = "缺少乡镇或街道以及详细地址"
        std_address = str(resp_data.get("address") or "")
    elif not county and ("市" in address or "市" in std_address):
        status = "fail"
        message = "缺少区县、乡镇或街道以及详细地址"
        std_address = str(resp_data.get("raw_address") or resp_data.get("llm_address") or address)
    elif not city and ("省" in address or "省" in std_address):
        status = "fail"
        message = "缺少市、区县、乡镇或街道以及详细地址"
        std_address = str(resp_data.get("raw_address") or resp_data.get("llm_address") or address)
    elif address == "无法判断":
        status = "fail"
        message = "未成功获取有效地址"
        std_address = "无法判断"
    else:
        status = "fail"
        message = "未成功获取有效地址"
        std_address = str(resp_data.get("address") or address or "")

    return {
        "raw_address": address,
        "address": std_address,
        "detail": detail_address,
        "message": message,
        "status": status,
        "parentAreaCode": county_code,
        "parentAreaName": parent_area_name,
        "areaCode": town_code,
        "areaName": area_name,
        "areaNum": area_num,
    }


def call_address_normalize(raw_address: str, timeout: float = CC_ADDRESS_API_TIMEOUT) -> dict[str, Any] | None:
    token = create_jwt(API_KEY, API_SECRET)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    data = {
        "restParams": {
            "ccAigcValidationCondition": FILTER_CONDITION.split(","),
            "address": raw_address,
        }
    }
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        logger.info("地址标准化原始结果: %s", json.dumps(payload, ensure_ascii=False))
        if CC_API_VERSION == "V1":
            return convert_json_format_v1(payload, raw_address)
        return convert_json_format_v2(payload, raw_address)
    except requests.exceptions.RequestException as exc:
        logger.error("请求地址标准化失败: %s", exc)
        return None


async def async_call_address_normalize(
    raw_address: str,
    timeout: float = CC_ADDRESS_API_TIMEOUT,
) -> dict[str, Any] | None:
    import aiohttp

    token = create_jwt(API_KEY, API_SECRET)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    data = {
        "restParams": {
            "ccAigcValidationCondition": FILTER_CONDITION.split(","),
            "address": raw_address,
        }
    }
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    try:
        async with aiohttp.ClientSession(timeout=client_timeout) as session:
            async with session.post(API_URL, json=data, headers=headers) as resp:
                payload = await resp.json()
        logger.info("地址标准化原始结果: %s", json.dumps(payload, ensure_ascii=False))
        if CC_API_VERSION == "V1":
            return convert_json_format_v1(payload, raw_address)
        return convert_json_format_v2(payload, raw_address)
    except Exception as exc:
        logger.error("异步地址标准化失败: %s", exc)
        return None


def build_address_info(address: str, normalized_result: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized_address = str(address or "").strip()
    if not normalized_address:
        return {
            "raw_address": "",
            "address": "",
            "detail": "",
            "message": "未提取到地址",
            "status": "fail",
            "parentAreaCode": "",
            "parentAreaName": "",
            "areaCode": "",
            "areaName": "",
            "areaNum": "",
            "normalized_result": normalized_result,
        }
    if normalized_result is None:
        return {
            "raw_address": normalized_address,
            "address": normalized_address,
            "detail": "",
            "message": "请求地址标准化失败",
            "status": "fail",
            "parentAreaCode": "",
            "parentAreaName": "",
            "areaCode": "",
            "areaName": "",
            "areaNum": "",
            "normalized_result": None,
        }
    address_info = convert_address_mcp_format(normalized_address, normalized_result)
    address_info["normalized_result"] = normalized_result
    return address_info


def convert_address_info_to_model_dict(address_info: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(address_info, Mapping):
        return {
            "address": "",
            "error_code": 1,
            "error_msg": "failed to call worksheet ie tool with addressInfo",
        }

    response = dict(address_info)
    response.pop("normalized_result", None)
    message = str(response.pop("message", "") or "")
    status = str(response.pop("status", "") or "")
    if status == "success":
        response["error_code"] = 0
        response["error_msg"] = message
    else:
        response["error_code"] = 1
        response["error_msg"] = message

    response.pop("detail", None)
    response.pop("parentAreaCode", None)
    response.pop("parentAreaName", None)
    response.pop("areaCode", None)
    response.pop("areaName", None)
    response.pop("areaNum", None)
    response.pop("raw_address", None)
    return {
        "address": str(response.get("address") or ""),
        "error_code": int(response.get("error_code", 1)),
        "error_msg": str(response.get("error_msg") or ""),
    }


def get_last_assistant_turn(dialogue: Sequence[Any] | str) -> str:
    for line in reversed(_dialogue_lines(dialogue)):
        if line.startswith("机器人：") or line.startswith("客服："):
            return line
    return ""


def build_address_model_observation(
    dialogue: Sequence[Any] | str,
    *,
    client: OpenAIChatClient | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    try:
        extracted = ie(dialogue, "address", client=client, model=model)
        extracted_address = str(extracted.get("address") or "").strip()
        if not extracted_address:
            return convert_address_info_to_model_dict(build_address_info("", None))
        normalized_result = call_address_normalize(extracted_address)
        address_info = build_address_info(extracted_address, normalized_result)
        return convert_address_info_to_model_dict(address_info)
    except Exception as exc:
        logger.exception("构造地址 observation 失败: %s", exc)
        return {
            "address": "",
            "error_code": 1,
            "error_msg": str(exc) or "failed to build address observation",
        }


def normalize_number(number: str) -> str:
    return number.replace("-", "").replace(" ", "")


def _fallback_extract_phone_from_dialogue(dialogue: Sequence[Any] | str) -> str:
    lines = _dialogue_lines(dialogue)
    for line in reversed(lines):
        digits = re.sub(r"\D", "", line)
        if digits:
            return digits
    return ""


def validate_phone_number(number_str: str, default_region: str = "CN") -> dict[str, str]:
    clean_number = normalize_number(number_str)
    try:
        parsed_number = phonenumbers.parse(clean_number, default_region)
        if phonenumbers.is_valid_number(parsed_number):
            number_type = phonenumbers.number_type(parsed_number)
            if number_type == phonenumbers.PhoneNumberType.MOBILE:
                resolved_type = "手机号"
            elif 10 <= len(clean_number) <= 12 and clean_number.startswith("0"):
                resolved_type = "座机号(带区号)"
            elif (len(clean_number) == 7 or len(clean_number) == 8) and not clean_number.startswith("1"):
                resolved_type = "座机号(无区号)"
            else:
                resolved_type = "无效号码"
        elif 10 <= len(clean_number) <= 12 and clean_number.startswith("0"):
            resolved_type = "座机号(带区号)"
        elif (len(clean_number) == 7 or len(clean_number) == 8) and not clean_number.startswith("1"):
            resolved_type = "座机号(无区号)"
        else:
            resolved_type = "无效号码"
        return {"number": clean_number, "type": resolved_type}
    except Exception as exc:
        logger.error("phone number validate Error: %s", exc)
        return {"number": clean_number, "type": "无效号码"}


def build_telephone_model_observation(
    dialogue: Sequence[Any] | str,
    *,
    client: OpenAIChatClient | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    try:
        telephone_result = ie(dialogue, "telephone_number", client=client, model=model)
        telephone = str(
            telephone_result.get("telephone_number")
            or telephone_result.get("telephone")
            or ""
        ).strip()
        if not telephone:
            return {
                "telephone": "",
                "numberType": "无效号码",
                "error_code": 1,
                "error_msg": "无效号码",
            }

        normalized = validate_phone_number(telephone)
        number = str(normalized.get("number") or "").strip()
        number_type = str(normalized.get("type") or "无效号码").strip() or "无效号码"
        if number_type in {"无效号码", "座机号(无区号)"}:
            return {
                "telephone": number,
                "numberType": number_type,
                "error_code": 1,
                "error_msg": "无效号码",
            }
        return {
            "telephone": number,
            "numberType": number_type,
            "error_code": 0,
            "error_msg": "有效号码",
        }
    except Exception as exc:
        logger.exception("构造电话 observation 失败: %s", exc)
        fallback_digits = _fallback_extract_phone_from_dialogue(dialogue)
        if fallback_digits:
            normalized = validate_phone_number(fallback_digits)
            number = str(normalized.get("number") or "").strip()
            number_type = str(normalized.get("type") or "无效号码").strip() or "无效号码"
            return {
                "telephone": number,
                "numberType": number_type,
                "error_code": 0 if number_type in {"手机号", "座机号(带区号)"} else 1,
                "error_msg": "有效号码" if number_type in {"手机号", "座机号(带区号)"} else "无效号码",
            }
        return {
            "telephone": "",
            "numberType": "无效号码",
            "error_code": 1,
            "error_msg": str(exc) or "failed to build telephone observation",
        }


def build_ie_model_observation(
    dialogue: Sequence[Any] | str,
    entity_type: str,
    *,
    client: OpenAIChatClient | None = None,
    model: str | None = None,
    brand: str | None = None,
    product: str | None = None,
) -> dict[str, Any]:
    if entity_type in {"address", "addressInfo"}:
        return build_address_model_observation(dialogue, client=client, model=model)
    if entity_type in {"telephone", "telephone_number"}:
        return build_telephone_model_observation(dialogue, client=client, model=model)
    response = ie(
        dialogue,
        entity_type,
        client=client,
        model=model,
    )
    if isinstance(response, Mapping):
        return dict(response)
    return {"error_code": 1, "error_msg": "unexpected ie response type"}


def format_telephone_observation_line(
    dialogue: Sequence[Any] | str,
    *,
    client: OpenAIChatClient | None = None,
    model: str | None = None,
) -> str:
    observation = build_telephone_model_observation(
        dialogue,
        client=client,
        model=model,
    )
    return f"observation: {json.dumps(observation, ensure_ascii=False)}"


def format_address_observation_line(
    dialogue: Sequence[Any] | str,
    *,
    client: OpenAIChatClient | None = None,
    model: str | None = None,
) -> str:
    observation = build_address_model_observation(
        dialogue,
        client=client,
        model=model,
    )
    return f"observation: {json.dumps(observation, ensure_ascii=False)}"


def suggest_address_collection_reply(
    address_info: Mapping[str, Any] | None,
    *,
    previous_assistant_turn: str = "",
) -> str:
    if not isinstance(address_info, Mapping):
        return ""

    message = str(address_info.get("message") or "")
    address = simplify_address_for_confirmation(str(address_info.get("address") or ""))
    if message == "已成功获取完整地址":
        if address and not maybe_address_confirmation(previous_assistant_turn):
            return f"跟您确认下，地址是{address}，对吗？"
        return ""
    if message == "请求地址标准化失败":
        if address and address != "无法判断" and not maybe_address_confirmation(previous_assistant_turn):
            return f"跟您确认下，地址是{address}，对吗？"
        return "地址解析失败，请您再说下完整地址是在哪里。"
    if message == "已成功获取四级地址，缺少详细地址信息":
        return "请您说下详细的地址，具体是在哪个小区或村？"
    if message == "缺少乡镇或街道以及详细地址":
        return "麻烦您再补充下乡镇或街道以及详细地址。"
    if message == "缺少乡镇或街道":
        return "请问您的地址是在哪个乡镇或街道？"
    if message == "缺少区县、乡镇或街道以及详细地址":
        return "麻烦您再说下完整地址是在哪里。"
    if message == "缺少市、区县、乡镇或街道以及详细地址":
        return "好的，请问您的完整地址是在哪里？"
    return ""


def extract_and_normalize_history_address(dialogue_history: Sequence[Any]) -> dict[str, Any] | None:
    history_address = extract_history_address(dialogue_history)
    if not history_address:
        return None
    return call_address_normalize(history_address)


async def async_extract_and_normalize_history_address(
    dialogue_history: Sequence[Any],
) -> dict[str, Any] | None:
    history_address = extract_history_address(dialogue_history)
    if not history_address:
        return None
    return await async_call_address_normalize(history_address)


def run_function_call_for_text(
    text: Sequence[Any] | str,
    *,
    normalize_extracted_address: bool = False,
    client: OpenAIChatClient | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    dialogue_lines = _dialogue_lines(text)
    result = extract_user_info(dialogue_lines, client=client, model=model)
    previous_assistant_turn = get_last_assistant_turn(dialogue_lines)

    normalized_history_address = None
    history_address_info = None
    if result.get("history_address"):
        normalized_history_address = call_address_normalize(str(result["history_address"]))
        history_address_info = build_address_info(str(result["history_address"]), normalized_history_address)

    normalized_address = None
    address_info = None
    extracted_address = str(result.get("address") or "").strip()
    if extracted_address and normalize_extracted_address:
        normalized_address = call_address_normalize(extracted_address)
        address_info = build_address_info(extracted_address, normalized_address)
    elif extracted_address:
        address_info = build_address_info(extracted_address, None)

    address_collection_suggestion = suggest_address_collection_reply(
        address_info,
        previous_assistant_turn=previous_assistant_turn,
    )
    address_model_dict = convert_address_info_to_model_dict(address_info)

    return {
        "dialogue": dialogue_lines,
        "user_info": result,
        "history_address_info": history_address_info,
        "address_info": address_info,
        "address_model_dict": address_model_dict,
        "address_collection_suggestion": address_collection_suggestion,
        "normalized_history_address": normalized_history_address,
        "normalized_address": normalized_address,
    }


if __name__ == "__main__":
    """
    [{"name": "ie", "arguments": {"entity_type": "addressInfo"}}]
    [{"name": "ie", "arguments": {"entity_type": "telephone"}}]
    """
    sample_dialogue = [
        "用户：空气能热水器需要维修",
        "客服：您好，很高兴为您服务，请问是美的空气能热水机需要维修吗？",
        "用户：是的,面板破裂",
        "客服：非常抱歉，给您添麻烦了，我这就安排师傅上门维修，请问您的空气能是什么具体品牌或系列呢？",
        "用户：科目的",
        "客服：好的，请问您贵姓？",
        "用户：郭",
        "客服：请问您当前这个来电号码能联系到您吗？",
        "用户：可以的",
        "客服：您的地址是重庆市渝中区上清寺街道康乐社区3号楼1单元2104室，对吗？",
        "用户：我在沧浪街道三多巷小区",
        "客服：好的，请您说一下完整的省市区信息。",
        "用户：姑苏区",
        # "客服：请问具体是在哪个小区或村呢？尽量详细到门牌号。",
        # "用户：西郊一区40号楼 402 室",
    ]
    sample_phone_dialogue = [
        "客服：请问您当前这个来电号码能联系到您吗？",
        "用户：这个号码不太方便，您记一下我的新号码吧。",
        "客服：好的，麻烦您说一下联系电话。",
        "用户：13800138000。",
    ]
    sample_address = os.environ.get("ADDRESS_TEST_INPUT", "").strip()
    sample_dialogue_text = os.environ.get("DIALOGUE_TEXT_INPUT", "").strip()
    cli_text = "\n".join(arg.strip() for arg in sys.argv[1:] if arg.strip())

    print("ENV =", ENV)
    print("CC_API_VERSION =", CC_API_VERSION)
    print("CC_API_URL =", API_URL)
    print("FILTER_CONDITION =", FILTER_CONDITION)
    print("sample_dialogue =")
    print(json.dumps(sample_dialogue, ensure_ascii=False, indent=2))
    print("sample_history_address =", extract_history_address(sample_dialogue))

    target_text = cli_text or sample_dialogue_text
    if target_text:
        print("dialogue_text_input =")
        print(target_text)
        try:
            result = run_function_call_for_text(
                target_text,
                normalize_extracted_address=True,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as exc:
            print(f"给定文本调用失败: {exc}")
        sys.exit(0)

    if sample_address:
        print("normalize_input =", sample_address)
        result = call_address_normalize(sample_address)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("ie_address_test_dialogue =")
        print("\n".join(sample_dialogue))
        try:
            ie_address_result = ie(sample_dialogue, "address")
            print("ie_address_result =")
            print(json.dumps(ie_address_result, ensure_ascii=False, indent=2))
            extracted_address = str(ie_address_result.get("address") or "").strip()
            if extracted_address:
                normalized_result = call_address_normalize(extracted_address)
                address_info = build_address_info(extracted_address, normalized_result)
                print("ie_address_info =")
                print(json.dumps(address_info, ensure_ascii=False, indent=2))
                print("ie_address_model_dict =")
                print(
                    json.dumps(
                        convert_address_info_to_model_dict(address_info),
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                print(
                    "ie_address_collection_suggestion =",
                    suggest_address_collection_reply(
                        address_info,
                        previous_assistant_turn=get_last_assistant_turn(sample_dialogue),
                    ),
                )
        except Exception as exc:
            print(f"ie地址提取测试失败: {exc}")
        
        print("telephone_test_dialogue =")
        print("\n".join(sample_phone_dialogue))
        try:
            telephone_result = build_telephone_model_observation(sample_phone_dialogue)
            print("telephone_model_dict =")
            print(json.dumps(telephone_result, ensure_ascii=False, indent=2))
        except Exception as exc:
            print(f"ie电话提取测试失败: {exc}")
