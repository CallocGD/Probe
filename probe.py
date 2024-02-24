"""
Probe is a small Proxy Tester for Probing boomlings.com
"""

from aiohttp import ClientSession
from aiohttp_socks import ProxyConnector, ProxyType, ProxyTimeoutError, ProxyConnectionError
import asyncio, attrs
import asyncclick as click
from colorama import Fore, init, deinit
from typing import NamedTuple, Optional



class ProxyPart(NamedTuple):
    ip:str
    port:int
    def to_connector(self, _type:ProxyType):
        return ProxyConnector(_type, self.ip, self.port)
    
    @classmethod
    def from_str(cls, s:str):
        _host, _port = s.strip().split(":", 1)
        return cls(_host, _port)

    def to_str(self):
        return self.ip + f":{self.port}"


def read_proxies(file:str):
    with open(file, "r") as r:
        for line in r:
            yield ProxyPart.from_str(line)


class AsyncHandle:
    def __init__(self, func, threads: int = 2, queue_limit:int = None, timer:int = None) -> None:
        self.q = asyncio.Queue(maxsize=queue_limit if queue_limit else 0)
        self.func = func
        self.threads = threads
        self.workers = [asyncio.create_task(self.run()) for _ in range(threads)]
        self.timer = timer
        self.loop = asyncio.get_event_loop()
    
    async def add_async(self, *args, **kwargs):
        await self.q.put((args, kwargs))

    def add(self, *args, **kwargs):
        self.q.put_nowait((args, kwargs))

    async def join(self):
        """Joins all results together"""
        await self.q.join()
        for w in self.workers:
            await self.q.put(None)
        for w in self.workers:
            w.cancel()
            
    async def cancel(self):
        """Shuts down and kill all the workers and queues..."""
        for w in self.workers:
            await self.q.put(None)
            
        for w in self.workers:
            w.cancel()

    async def run(self):
        while True:
            ak = await self.q.get()
            if ak is None:
                break
            a, k = ak
            try:
                if self.timer is not None:
                    await asyncio.wait_for(self.func(*a, **k), self.timer)
                else:
                    await self.func(*a, **k)
            except Exception as e:
                self.loop.call_soon(print, e)
            self.q.task_done()


@attrs.define()
class Probe:
    threads:int = 4
    output:Optional[str] = None
    echo:bool = True
    disable_color:bool = False
    file_lock:asyncio.Lock = attrs.field(init=False, factory=asyncio.Lock)
    loop:asyncio.AbstractEventLoop = attrs.field(init=False, factory=asyncio.get_event_loop)


    def __attrs_post_init__(self):
        if self.disable_color:
            init(strip=True)
        else:
            init(autoreset=True)

    def _print(self, text:str):
        if self.echo:
            self.loop.call_soon(print, text)

    async def test_single_proxy(self, proxy:ProxyPart, proxy_type:ProxyType):
        """Tests to see if a proxy failed or not..."""
        try:
            success = True
            async with ClientSession(skip_auto_headers=["User-Agent"],  connector=proxy.to_connector(proxy_type), cookies={"gd": 1}) as client:
                async with client.post("https://www.boomlings.com/database/getGJDailyLevel.php", data={"secret" :"Wmfd2893gb7"}) as resp:
                    if resp.status != 200:
                        success = False
                    text = await resp.text()
                    # Captcha check...
                    # TODO ADD echo_failed flag check...
                    if text.startswith("<html>"):
                        # self._print(Fore.LIGHTRED_EX + "[-] " + proxy.to_str() + Fore.RESET)
                        success = False
                    # CloudFlare error...
                    elif text.startswith("error"):
                        # self._print(Fore.LIGHTRED_EX + "[-] " + proxy.to_str() + Fore.RESET)
                        success = False
            if not success:
                return False
            self._print(Fore.LIGHTGREEN_EX + "[+] " + proxy.to_str() + Fore.RESET)
            if self.output:
                async with self.file_lock:
                    with open(self.output, "a") as a:
                        a.write(proxy.to_str() + "\n")
            return True
        except (ProxyTimeoutError, ProxyConnectionError):
            return False
        except:
            return False
    
    async def test_file(self, file:str, proxy_type:ProxyType):
        """Tests an entire file of proxies..."""
        handle = AsyncHandle(self.test_single_proxy, self.threads, 100)
        for proxy in read_proxies(file):
            await handle.add_async(proxy=proxy, proxy_type=proxy_type)
        return await handle.join()



@click.command()
@click.argument("files", type=click.Path(exists=True), nargs = -1)
@click.option("--type","--proxy-type", "type", prompt=True , type=click.Choice(["socks4", "socks5", "http"]))
@click.option("--output",type=click.Path() ,help="Where to output working proxies to...")
@click.option("--threads",type=click.IntRange(min=1, clamp=True), default=20)
async def cli(files:list[str], type:str, output:Optional[str], threads:int):
    """Used for finding alive and valid proxy connections to boomlings.com..."""
    pmap = {k.lower(): v for k , v in ProxyType._member_map_.items()}
    ptype = pmap[type.lower()]
    probe = Probe(threads, output=output)
    for p in files:
        await probe.test_file(p, ptype)
    deinit()


if __name__ == "__main__":
    cli()

