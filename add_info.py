import logging, time
import requests, json, sys
from requests.auth import HTTPBasicAuth
from pypinyin import pinyin, lazy_pinyin, Style

def get_manga_list() -> list:
    r = requests.get('http://127.0.0.1:8080/api/v1/series?page=0&size=500', auth=HTTPBasicAuth('username','password'))
    if r.status_code != 200:
        logging.error(f"获取列表失败，错误码{r.status_code} \n {r.text}")
        return sys.exit(1)
    cookie = r.cookies.get_dict().get('SESSION')
    data = json.loads(r.text)['content']
    data_list = []
    for i in data:
        if not i['metadata']['titleSortLock']:
            d = {}
            d['id'] = i['id']
            d['name'] = i['name']
            data_list.append(d)
    return data_list, cookie


def get_bgm(keywords: str) -> dict:
    r = requests.get(f'https://api.bgm.tv/search/subject/{keywords}?type=1&responseGroup=small&max_results=1', headers={"user-agent": "Ukenn/UCoin-Manga"})
    if r.status_code != 200:
        logging.error(f"获取bgm搜索失败，错误码{r.status_code} \n {r.text}")
        return sys.exit(1)
    data = json.loads(r.text)
    if data['list']:
        bgm_id = data['list'][0]['id']
    else:
        logging.error(f"没有搜索到bgm")
        return sys.exit(1)
    rs = requests.get(f'https://api.bgm.tv/v0/subjects/{bgm_id}', headers={"user-agent": "Ukenn/UCoin-Manga"})
    if rs.status_code != 200:
        logging.error(f"获取bgm详情失败，错误码{rs.status_code} \n {rs.text}")
        return sys.exit(1)
    info_data = {}
    dataa = json.loads(rs.text)
    if dataa['name_cn']:
        info_data['name_cn'] = dataa['name_cn']
        info_data['name'] = dataa['name']
    else:
        info_data['name_cn'] = None
        info_data['name'] = dataa['name']
    info_data['summary'] = dataa['summary']
    if dataa['tags']:
        info_data['tags'] = [i['name'] for i in dataa['tags']]
    else:
        info_data['tags'] = []
    info_data['image'] = dataa['images']['large']
    return info_data


def send_info(manga_id: int, info_data: dict, cookie: str) -> None:
    p = ''
    if info_data['name_cn']:
        p = pinyin(info_data['name_cn'], style=Style.FIRST_LETTER, strict=False)[0][0]
    data = {
        "statusLock": False,
        "readingDirectionLock": False,
        "ageRatingLock": False,
        "publisherLock": False,
        "languageLock": False,
        "genresLock": False,
        "tagsLock": True,
        "totalBookCountLock": False,
        "sharingLabelsLock": False,
        "tags": info_data['tags'],
        "titleLock": False,
        "titleSortLock": True,
        "summaryLock": True,
        "titleSort": p + info_data['name'],
        "summary": info_data['summary']
        }
    r = requests.patch(f'http://127.0.0.1:8080/api/v1/series/{manga_id}/metadata', data=json.dumps(data), headers={"Cookie": f"SESSION={cookie}", "content-type": "application/json"})
    if r.status_code != 204:
        logging.error(f"发送简介失败，错误码{r.status_code} \n {r.text}")
        return sys.exit(1)
    for i in range(1, 5):
        jpg = requests.get(info_data['image'], headers={"user-agent": "Ukenn/UCoin-Manga"})
        if jpg.status_code == 200:
            break
        logging.error('[E] 下载失败')
        if i == 5:
            return sys.exit(1)
        time.sleep(3)

    with open(f"{info_data['image'].split('/')[-1]}", "wb") as code:
        code.write(jpg.content)
    rs = requests.post(f'http://127.0.0.1:8080/api/v1/series/{manga_id}/thumbnails', files={'file': open(f"{info_data['image'].split('/')[-1]}", 'rb')}, headers={"Cookie": f"SESSION={cookie}"})
    if rs.status_code != 200:
        logging.error(f"发送简介图片失败，错误码{rs.status_code} \n {rs.text}")
        return sys.exit(1)

if __name__ == '__main__':
    manga_list, cookie = get_manga_list()
    for i in manga_list:
        info_data = get_bgm(i['name'])
        send_info(i['id'], info_data, cookie)