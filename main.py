from urllib3.exceptions import InsecureRequestWarning
from operator import itemgetter
from threading import Thread
import argparse
import warnings
import os.path
import json

import requests
import bs4

session = requests.Session()
session.headers['Referer'] = 'https://www.pixiv.net/'

def download(url: str, i: int, result: list[None]) -> None:
    print('Start downloading', url)
    res = session.get(url, verify=False)
    if res.status_code != 200:
        raise RuntimeError('{} returned while downloading {}'.format(res.status_code, url))
    result[i] = res.content
    print(url, 'done')

def downloads(urls: list[str]) -> list[bytes]:
    threads = []
    result = []
    for i, url in enumerate(urls):
        thread = Thread(
            target=download,
            args=(url, i, result)
        )
        result.append(None)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    return result

def writes(result: list[bytes], output: str):
    for i, content in enumerate(result):
        open(os.path.join(output, '{}.jpg'.format(i)), 'wb').write(content)

def main() -> None:
    warnings.filterwarnings('ignore', category=InsecureRequestWarning)
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--id', type=int, help='爬取的插画ID')
    parser.add_argument('-v', '--vision', type=int, help='爬取的Pixivision文章ID')
    parser.add_argument('-o', '--output', default='.', help='输出的文件夹(默认为当前路径)')
    args = parser.parse_args()
    if args.id is not None:
        fetch_artword(args.id, args.output)
    elif args.vision is not None:
        fetch_pixivision(args.vision, args.output)

def fetch_pixivision(id: int, output: str) -> None:
    res = session.get('https://www.pixivision.net/zh/a/{}'.format(id), verify=False)
    soup = bs4.BeautifulSoup(res.text, 'lxml')
    result = downloads(map(itemgetter('src'), soup.find_all('img', class_='am__work__illust')))
    writes(result, output)

def fetch_artword(id: int, output: str) -> None:
    res = session.get('https://www.pixiv.net/ajax/illust/{}/pages?lang=zh&version=dce12e1f9118277ca2839d13e317c59d7ae9ac6e'.format(id), verify=False)
    data = json.loads(res.text)['body']
    if not os.path.exists(output):
        os.mkdir(output)
    result = downloads(i['urls']['original'] for i in data)
    writes(result, output)
    print('Done')
    
if __name__ == '__main__':
    main()