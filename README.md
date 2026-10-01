# task26100206
## SoloBooks 客户消息脱敏库

上层在保存消息前调用；原文只在内存中处理，本组件不负责持久化。

```python
from solobooks_redact import redact_message

redact_message("电话 (212) 555-0123 x894", [])   # -> "电话 【已隐藏】"
redact_message("Ａﬃ é", ["fi", "é"])             # -> "Ａ【已隐藏】 【已隐藏】"
```

识别语义：忽略 Cf 字符 -> NFKC -> casefold -> Unicode 数字转 ASCII；
敏感词按同样规则做子串匹配；同时识别 SSN 与北美电话（含分机）。
命中统一替换为 `【已隐藏】`，相交区间合并，未命中内容逐码点保留。

运行测试：

```sh
python3 -m unittest discover -s tests -v
```
