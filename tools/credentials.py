def validate_api_key(value):
    if not value:
        raise ValueError("请先配置 DEEPSEEK_API_KEY")
    if len(value) > 4096 or any(not 33 <= ord(char) <= 126 for char in value):
        raise ValueError("DEEPSEEK_API_KEY 只能包含可打印的 ASCII 字符，不能包含空白或控制字符")
    return value
