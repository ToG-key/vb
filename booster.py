import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

import requests
import urllib3
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SuperViewBooster:
    def __init__(self):
        self.ua = UserAgent()
        self.session = self._make_session()
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        self.working_proxies = []
        self.MAX_WORKERS = 1000
        self.MAX_PROXIES = 100

    def _make_session(self):
        s = requests.Session()
        retry = Retry(total=2, backoff_factor=0.1,
                      status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(pool_connections=200, pool_maxsize=200,
                              max_retries=retry, pool_block=False)
        s.mount('http://', adapter)
        s.mount('https://', adapter)
        s.verify = False
        return s

    def get_proxies_from_file(self, filename="proxy.txt"):
        proxies = []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            proxies.append({
                                'ip': parts[0].strip(),
                                'port': parts[1].strip(),
                                'type': parts[2].strip() if len(parts) > 2 else 'http'
                            })
        except FileNotFoundError:
            pass
        return proxies

    def get_proxies_online(self):
        all_proxies = []
        seen = set()

        sources = [
            ("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all", "http"),
            ("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000&country=all&ssl=all&anonymity=all", "socks5"),
            ("https://cdn.jsdelivr.net/gh/proxyscrape/free-proxy-list@main/proxies/protocols/http/data.txt", "http"),
            ("https://cdn.jsdelivr.net/gh/proxyscrape/free-proxy-list@main/proxies/protocols/socks5/data.txt", "socks5"),
            ("https://raw.githubusercontent.com/maximilianfeix/proxy-scraper/proxy-list/http.txt", "http"),
            ("https://raw.githubusercontent.com/maximilianfeix/proxy-scraper/proxy-list/socks5.txt", "socks5"),
            ("https://raw.githubusercontent.com/komutan234/Proxy-List-Free/main/proxies/http.txt", "http"),
            ("https://raw.githubusercontent.com/komutan234/Proxy-List-Free/main/proxies/socks5.txt", "socks5"),
            ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", "http"),
            ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt", "socks5"),
            ("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt", "http"),
            ("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt", "socks5"),
        ]

        for url, default_type in sources:
            try:
                resp = self.session.get(url, timeout=8,
                                        headers={'User-Agent': self.ua.random})
                if resp.status_code != 200:
                    continue

                text = resp.text.strip()
                if text.startswith('[') or text.startswith('{'):
                    try:
                        data = resp.json()
                        items = data if isinstance(data, list) else data.get('data', [])
                        for item in items[:500]:
                            ip = item.get('ip') or item.get('host')
                            port = item.get('port')
                            ptype = item.get('protocol') or default_type
                            if ip and port:
                                key = f"{ip}:{port}"
                                if key not in seen:
                                    seen.add(key)
                                    all_proxies.append({
                                        'ip': str(ip), 'port': str(port),
                                        'type': ptype, 'source': 'api'
                                    })
                        continue
                    except Exception:
                        pass

                for line in text.splitlines()[:1000]:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '://' in line:
                        ptype, rest = line.split('://', 1)
                        parts = rest.split(':')
                        if len(parts) >= 2:
                            ip, port = parts[0], parts[1]
                            if ip and port:
                                key = f"{ip}:{port}"
                                if key not in seen:
                                    seen.add(key)
                                    all_proxies.append({
                                        'ip': ip, 'port': port,
                                        'type': ptype, 'source': 'github'
                                    })
                    elif ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            ip, port = parts[0].strip(), parts[1].strip()
                            if ip and port:
                                key = f"{ip}:{port}"
                                if key not in seen:
                                    seen.add(key)
                                    all_proxies.append({
                                        'ip': ip, 'port': port,
                                        'type': default_type, 'source': 'github'
                                    })
            except Exception:
                continue

        print(f"Thu thập được {len(all_proxies)} proxy từ online")
        return all_proxies

    def test_proxy_fast(self, proxy):
        try:
            proxy_url = f"{proxy['type']}://{proxy['ip']}:{proxy['port']}"
            start = time.time()
            r = self.session.get(
                'http://httpbin.org/ip',
                proxies={'http': proxy_url, 'https': proxy_url},
                timeout=4,
                headers={'User-Agent': self.ua.random}
            )
            latency = time.time() - start
            if r.status_code == 200:
                return latency
        except Exception:
            pass
        return None

    def test_proxies(self, proxies, max_workers=500):
        test_list = proxies[:5000] if len(proxies) > 5000 else proxies
        print(f"Đang test {len(test_list)} proxy với {max_workers} luồng...")

        working = []
        with ThreadPoolExecutor(max_workers=min(max_workers, self.MAX_WORKERS)) as executor:
            future_map = {executor.submit(self.test_proxy_fast, p): p for p in test_list}
            for future in as_completed(future_map):
                p = future_map[future]
                latency = future.result()
                if latency is not None:
                    p['latency'] = round(latency, 3)
                    working.append(p)

        working.sort(key=lambda x: x.get('latency', 999))
        self.working_proxies = working[:self.MAX_PROXIES]

        print(f"Tìm thấy {len(working)} proxy hoạt động, giữ lại {len(self.working_proxies)} proxy tốt nhất")
        return self.working_proxies

    def create_view(self, url, proxy, visit_id):
        try:
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': random.choice([
                    'https://www.google.com/',
                    'https://www.facebook.com/',
                    'https://www.youtube.com/',
                    'https://www.thivien.net/'
                ]),
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-Fetch-User': '?1',
            }

            proxy_url = f"{proxy['type']}://{proxy['ip']}:{proxy['port']}"
            proxies = {'http': proxy_url, 'https': proxy_url}

            r = self.session.get(url, proxies=proxies, headers=headers,
                                 timeout=10, verify=False)

            if r.status_code == 200:
                with self.lock:
                    self.success_count += 1
                    if self.success_count % 1000 == 0:
                        print(f"Đã thành công {self.success_count} view")
                return True
            else:
                with self.lock:
                    self.fail_count += 1
                return False
        except Exception:
            with self.lock:
                self.fail_count += 1
            return False

    def boost_views(self, url, total_views=100, delay=0.1, workers=100,
                    stop_flag=None, progress_cb=None):
        if not self.working_proxies:
            print("Không có proxy hoạt động!")
            return

        workers = min(workers, self.MAX_WORKERS)
        print(f"\nBẮT ĐẦU TĂNG {total_views} LƯỢT XEM")
        print(f"Proxy: {len(self.working_proxies)}")
        print(f"Workers: {workers}")
        print(f"Delay: {delay}s")
        print("=" * 60)

        start_time = time.time()
        submitted = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = set()
            while submitted < total_views:
                if stop_flag and stop_flag():
                    print("Dừng theo yêu cầu")
                    break

                if len(futures) >= workers * 2:
                    done, futures = wait(futures, return_when=FIRST_COMPLETED)
                    for f in done:
                        f.result()
                    if progress_cb:
                        progress_cb(self.success_count, self.fail_count, submitted)
                    continue

                proxy = random.choice(self.working_proxies)
                f = executor.submit(self.create_view, url, proxy, submitted + 1)
                futures.add(f)
                submitted += 1
                time.sleep(delay)

            for f in as_completed(futures):
                f.result()

        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        print("HOÀN THÀNH")
        print(f"Đã gửi: {submitted}")
        print(f"Thành công: {self.success_count}")
        print(f"Thất bại: {self.fail_count}")
        print(f"Thời gian: {elapsed:.1f}s")
        if elapsed > 0:
            print(f"Tốc độ: {submitted / elapsed:.2f} views/s")
        print("=" * 60)
