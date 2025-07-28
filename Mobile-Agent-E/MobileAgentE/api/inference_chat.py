def smart_model_chat(prompt, history=None):
    model_sequence = ["Gemini", "Qwen", "DashScope"]
    errors = []

    for model_type in model_sequence:
        try:
            if model_type == "Gemini":
                from MobileAgentE.api.gemini_chat import chat as gemini_chat
                return gemini_chat(prompt, history)
            elif model_type == "Qwen":
                from MobileAgentE.api.qwen_chat import chat as qwen_chat
                return qwen_chat(prompt, history)
            elif model_type == "DashScope":
                from MobileAgentE.api.dashscope_chat import chat as dash_chat
                return dash_chat(prompt, history)
        except Exception as e:
            errors.append(f"{model_type} failed: {str(e)}")
            continue

    raise RuntimeError("All models failed:\n" + "\n".join(errors))