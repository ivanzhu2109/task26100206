# task26100206

SoloBooks 客户消息脱敏库。上层在保存消息前调用,原文只在内存中处理,
本组件不负责持久化。

## 用法

```python
from redact import redact_message

redact_message("回电 (202) 555-1234 ext. 89", ["某敏感词"])
# => "回电 【已隐藏】"
```

`redact_message(body, sensitive_words)` 一次接收正文与敏感词集,
返回脱敏后的正文。识别敏感词(规范化后任意子串)、SSN、电话号码,
命中处替换为 `【已隐藏】`;相交的替换区间合并,仅相邻的不合并;
未命中部分逐码点保持原样。

识别语义:忽略 Unicode Cf 字符 -> NFKC -> casefold ->
Unicode 十进制数字转 ASCII,敏感词与正文遵循同样规则。

## 测试

```sh
python3 -m pytest
```
