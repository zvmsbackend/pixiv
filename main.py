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
session.headers['Cookie'] = 'first_visit_datetime_pc=2023-06-06+09%3A15%3A21; p_ab_id=9; p_ab_id_2=3; p_ab_d_id=867244837; yuid_b=KFWAJJM; _gcl_au=1.1.531833040.1686010525; _fbp=fb.1.1686010531308.1803574154; c_type=20; privacy_policy_notification=0; a_type=0; b_type=1; login_ever=yes; __utmv=235335808.|2=login%20ever=yes=1^3=plan=normal=1^5=gender=male=1^6=user_id=94420971=1^9=p_ab_id=9=1^10=p_ab_id_2=3=1^11=lang=zh=1; device_token=72023b8026c6437991e912f2d8ad04c5; PHPSESSID=94420971_vrFsDsup7LQh7pkNxZi8MEZ7gUoIKg2O; _ga_MZ1NL4PHH0=GS1.1.1689729909.3.1.1689730864.0.0.0; privacy_policy_agreement=0; __utmz=235335808.1689732651.6.2.utmcsr=pixivision|utmccn=article_parts__pixiv_illust|utmcmd=8848; __utmc=235335808; QSI_S_ZN_5hF4My7Ad6VNNAi=v:0:0; _gid=GA1.2.176077193.1691503248; _ga_ZPL8LPMDK3=GS1.1.1691503085.1.1.1691503423.0.0.0; __utma=235335808.527825603.1686010525.1691502799.1691507867.8; _ga=GA1.2.527825603.1686010525; __utmt=1; __utmb=235335808.19.9.1691508130159; _ga_75BBYNYN9J=GS1.1.1691502801.7.1.1691509307.0.0.0'


def download(url: str, i: int, result: list[None]) -> None:
    print('Start downloading', url)
    res = session.get(url, verify=False)
    if res.status_code != 200:
        raise RuntimeError(
            f'{res.status_code} returned while downloading {url}')
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
        open(os.path.join(output, f'{i}.jpg'), 'wb').write(content)


def main() -> None:
    warnings.filterwarnings('ignore', category=InsecureRequestWarning)
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--id', type=int, help='爬取的插画ID')
    parser.add_argument('-v', '--vision', type=int, help='爬取的Pixivision文章ID')
    parser.add_argument('-u', '--user', type=int, help='爬取的用户的ID')
    parser.add_argument('-o', '--output', default=None, help='输出的文件夹(默认为当前路径)')
    args = parser.parse_args()
    if args.id is not None:
        fetch_artwork(args.id, args.output)
    if args.user is not None:
        fetch_user(args.user, args.output)
    elif args.vision is not None:
        fetch_pixivision(args.vision, args.output)


def fetch_user(id: int, output: str | None) -> None:
    if output is None:
        res = requests.get(f'https://www.pixiv.net/users/{id}', verify=False)
        soup = bs4.BeautifulSoup(res.text, 'lxml')
        output = next(iter(json.loads(soup.find('meta', id='meta-preload-data')['content'])['user'].values()))['name']
    if not os.path.exists(output):
        os.mkdir(output)
    res = session.get(f'https://www.pixiv.net/ajax/user/{id}/profile/all?lang=zh', verify=False)
    works = json.loads(res.text)['body']['illusts'].keys()
    threads = []
    for work in works:
        thread = Thread(
            target=fetch_artwork,
            args=(work, output, True)
        )
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()


def fetch_pixivision(id: int, output: str | None) -> None:
    res = session.get(f'https://www.pixivision.net/zh/a/{id}', verify=False)
    soup = bs4.BeautifulSoup(res.text, 'lxml')
    if output is None:
        output = soup.title.string
    if not os.path.exists(output):
        os.mkdir(output)
    result = downloads(
        map(itemgetter('src'), soup.find_all('img', class_='am__work__illust')))
    writes(result, output)


def fetch_artwork(id: int, output: str | None, illust_title: bool = False) -> None:
    if output is None or illust_title:
        res = requests.get(f'https://www.pixiv.net/artworks/{id}', verify=False)
        soup = bs4.BeautifulSoup(res.text, 'lxml')
        title = next(iter(json.loads(soup.find('meta', id='meta-preload-data')['content'])['illust'].values()))['illustTitle']
        output = os.path.join(output or '', title)
    res = session.get(
        f'https://www.pixiv.net/ajax/illust/{id}/pages?lang=zh', verify=False)
    data = json.loads(res.text)['body']
    if not os.path.exists(output):
        os.mkdir(output)
    result = downloads(i['urls']['original'] for i in data)
    writes(result, output)
    print(output, 'done')


if __name__ == '__main__':
    main()
