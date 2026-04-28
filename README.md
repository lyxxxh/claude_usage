# Claude.ai 多账号限额查询
![run](images/run.png)

1. `config.example.json` 改名`config.json`
2. 修改`config.json`
3. ,代理修成你电脑的,并填写`session_key` 和 `org_id`
   - 获取方式:见下面的截屏
4. `python claude_web_usage.py`

建议做成一个全局命令,方便调用。

我的:claude_run.bat:
```python "C:\Users\Administrator\code\claude_usage\claude_web_usage.py"```

## session_key
![获取 sessionKey](images/sessionKey.png)

`session_key` 约一年,不担心过期。
## org_id
![获取 org_id](images/org_id.png)

