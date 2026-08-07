
# 域名的查询工具

import asyncio

# 给我一个域名，我拿着去域名服务器比对，看是否被注册。如果已经被注册，已抢注。
async def check_domain(domain):
    # 判断后缀是否是 .com 结尾 或者没有 . 结尾后缀 (只做公司的域名 不考虑 .cn/.co/.net 。。。)
    if not domain.endswith('.com'):
        if '.' not in domain:
            domain += '.com'   # 如果没有 . 后缀说明大模型没给，自己补充完整
        else:
            return "⚠️ 仅支持.com校验"

    # reader, writer  开启网站，拿到读和写的工具
    reader, writer = await asyncio.wait_for(   # asyncio.wait_for 异步等待
        asyncio.open_connection('whois.verisign-grs.com', 43),  # 给大模型查询的工具，https://registrar.verisign-grs.com/webwhois-ui/index.jsp 43 端口号
        timeout=3.0  # 限制 3 秒超时，防止卡死
    )

    '''
    w.write(data)
    await w.drain()   
    '''
    writer.write((domain + "\r\n").encode('utf-8'))  # writer.write(str) 写入内容换出结果   (domain + "\r\n").encode('utf-8') 域名换行拼接，转成 UTF-8 的格式
    await writer.drain()   # 刷新写缓冲区。其预期用途是写入

    response = await asyncio.wait_for(reader.read(), timeout=3.0)  # 将放入缓冲区的数据转换成结果返回二进制字节

    writer.close()    # 关闭写
    await writer.wait_closed()  # 关闭读

    result = response.decode('utf-8', errors='ignore')   # 结果字符，英文结果

    if "No match for" in result:   # No match for domain "RMARON.COM". 判断是否注册
        return "✅ 未注册 (可买)"
    else:
        return "❌ 已被抢注"

