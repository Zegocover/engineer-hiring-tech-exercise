from aiohttp import ClientSession

async def get_html(url: str)-> str:
    async with ClientSession() as session:
        async with session.get(url) as response:
            is_html = response.content_type.startswith('text/html')
            if is_html:
                return await response.text()
            else:
                return ""
