from transformers import VoxtralForConditionalGeneration, AutoProcessor
import torch, json, re

device = "cuda" if torch.cuda.is_available() else "cpu"
repo_id = "mistralai/Voxtral-Mini-3B-2507"

processor = AutoProcessor.from_pretrained(repo_id)
model = VoxtralForConditionalGeneration.from_pretrained(
    repo_id, torch_dtype=torch.bfloat16 if device=="cuda" else torch.float32, device_map=device
)

# 1) 工具/函数定义：拍照
tools = [
    {
        "type": "function",
        "function": {
            "name": "take_photo",
            "description": "打开摄像头并拍照；仅当用户明确要求拍照或同义表述时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "camera_id": {"type": "integer", "description": "摄像头索引（默认0）", "default": 0},
                    "flash": {"type": "boolean", "description": "是否开启闪光灯", "default": False},
                    "mode": {"type": "string", "description": "拍照模式", "enum": ["auto", "portrait", "night"], "default": "auto"}
                },
                "required": []
            }
        }
    }
]

# 2) 对话：仅使用 user 消息（含音频+规则文本），避免含音频时的 system 限制
conversation = [
    {
        "role": "user",
        "content": [
            {"type": "audio", "path": "../data/test_3.wav"},
            {
                "type": "text",
                "text": (
                    "规则：若音频中有明确拍照意图（如拍照、帮我拍、打开相机、拍一张等），"
                    "请仅输出一个JSON对象，不要输出任何其他文字。\n"
                    "有意图时输出：{\"name\":\"take_photo\",\"arguments\":{\"camera_id\":0,\"flash\":true,\"mode\":\"auto\"}}\n"
                    "无意图时输出：{\"message\":\"...\"}"
                )
            }
        ]
    }
]

# 4) 构造输入（带tools），让模型自行决定是否调用函数
inputs = processor.apply_chat_template(conversation, tools=tools)
inputs = inputs.to(device, dtype=torch.bfloat16 if device=="cuda" else torch.float32)

outputs = model.generate(**inputs, max_new_tokens=128, do_sample=False, temperature=0.0, top_p=1.0)
gen_text_raw = processor.batch_decode(outputs[:, inputs.input_ids.shape[1]:], skip_special_tokens=False)[0]
gen_text = processor.batch_decode(outputs[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)[0]
print("Model output (raw):\n", gen_text_raw)
print("Model output:\n", gen_text)

# 5) 检测函数调用（示例：匹配JSON结构或约定片段；不同模型可能格式不同，按需调整）
def extract_tool_call(text: str):
    # 尝试提取 {"name": "...", "arguments": {...}} 结构
    match = re.search(r'\{.*"name"\s*:\s*"take_photo".*"arguments"\s*:\s*\{.*\}.*\}', text, re.S)
    if not match:
        return None
    try:
        # 宽松解析：找到第一个大括号json片段
        start = text.find("{", match.start())
        end = text.rfind("}")
        candidate = text[start:end+1]
        data = json.loads(candidate)
        if data.get("name") == "take_photo":
            return data.get("arguments", {})
    except Exception:
        return None
    return None

tool_args = extract_tool_call(gen_text)

# 6) 本地拍照函数（示例桩：在你的环境里替换为真实摄像头调用）
def take_photo(camera_id: int = 0, flash: bool = False, mode: str = "auto"):
    print(f"[take_photo] camera_id={camera_id}, flash={flash}, mode={mode}")
    # TODO: 在此接入真实摄像头逻辑
    return {"status": "ok", "path": "photos/last_shot.jpg", "camera_id": camera_id, "flash": flash, "mode": mode}

# 7) 决策：若模型请求函数调用，则执行；否则按普通对话处理
if tool_args is not None:
    print("=> 检测到函数调用请求：take_photo，参数：", tool_args)
    result = take_photo(
        camera_id=tool_args.get("camera_id", 0),
        flash=tool_args.get("flash", False),
        mode=tool_args.get("mode", "auto"),
    )
    print("函数执行结果：", result)
else:
    print("=> 未检测到函数调用：按普通回复处理")