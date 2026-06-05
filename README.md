# Claude.ai 多账号限额查询
![run](images/run.png)

1. `config.example.json` 改名`config.json`
2. 修改`config.json`
3. 填写`session_key` 和 `org_id`
   - 获取方式:见下面的截屏
   - `proxy` 字段默认是我本机抓包代理(`http://127.0.0.1:9999`),**请改成你自己的代理;若不需要代理,留空字符串 `""` 即可**
4. `python claude_web_usage.py`

建议做成一个全局命令,方便调用。

我的:claude_run.bat:
```bat
python "C:\Users\Administrator\code\claude_usage\claude_web_usage.py"
```



## 搭配定时任务,让用量窗口错峰刷新

本工具只负责**查看**多账号的 5 小时 / 7 天用量。如果想让 5 小时重置窗口持续滚动、覆盖一整天,建议搭配 Claude Code 的 `/schedule` 定时任务,在固定时间点(如 6:00 / 11:00 / 16:00)各发一次请求来刷新窗口,几个窗口相互重叠即可。

思路详见:https://www.v2ex.com/t/1216409

## session_key


打开:https://claude.ai/settings/usage


sessionKey 有效期约一年,且活跃使用会自动续期,基本不用担心过期。

![获取 sessionKey](images/sessionKey.png)

## org_id
![获取 org_id](images/org_id.png)

