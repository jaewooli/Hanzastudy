import re
import time
import urllib.parse

from bs4 import BeautifulSoup
import requests
from colorama import Fore, Style

import hanzadata

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}
GRADE_LIST_URL = "https://namu.wiki/w/" + urllib.parse.quote("한자/목록/급수별")


def does_save(hanzaimg, hanzamean, a, grade=0):
    stylex = Style.RESET_ALL
    if a == "Y" or a == 'y' or a == 'ㅛ':
        hanzadata.append_entry(hanzaimg, hanzamean, grade)
        print(f'{Fore.GREEN}해당 한자를 저장합니다.{stylex}\n')
    elif a == "N" or a == 'n' or a == 'ㅜ':
        pass
    else:
        a = input(f"{Fore.RED}Y 혹은 N 을 입력해주세요.{stylex}\n{Fore.GREEN}Y{stylex}/{Fore.GREEN}N{stylex} : ")
        does_save(hanzaimg, hanzamean, a, grade)


def main():
    stylex = Style.RESET_ALL
    geaupsu = [8, 7, 6, 5, 4, 3, 2, 1, 0]
    while 1:
        hanza = u"{hanza}".format(hanza=input(f"{Fore.GREEN}등록할 한자: {stylex}\n"))
        if hanza == 'h' or hanza == "help" or hanza == "도움말":
            print(f"{Fore.GREEN}등록할 한자의 뜻을 입력해주세요!{stylex}\n{Fore.RED}나가기: 종료{stylex}")
        if hanza == '종료':
            break
        if hanza[-1] == '급' and len(hanza) == 2:
            if int(hanza[0]) in geaupsu:
                hanzasave2(int(hanza[0]))
        else:
            hanzasave1(hanza)


def _parse_readings(sub_read_text):
    """'학교 교, 달릴 교, 풍길 효' -> ['학교 교', '학교', '교', '달릴 교', '달릴', '풍길 효', '풍길', '효']
    붙여 쓴 훈음(예: '학교 교')과 훈/음을 따로 뗀 형태를 모두 정답으로 인정하도록 함, 중복 제거."""
    means = []
    for phrase in sub_read_text.split(","):
        phrase = phrase.strip()
        if not phrase:
            continue
        means.append(phrase)
        parts = phrase.rsplit(" ", 1)
        if len(parts) == 2:
            means.extend(parts)
    seen = set()
    result = []
    for m in means:
        if m and m not in seen:
            seen.add(m)
            result.append(m)
    return result


def _fetch_daum_entry(hanza):
    """한 번 시도해서 (hanzaimg, hanzamean)을 돌려주거나, 못 찾으면 None을 돌려준다."""
    page = requests.get("https://dic.daum.net/search.do", params={"q": hanza, "dic": "hanja"}, timeout=15)
    soup = BeautifulSoup(page.content, 'html.parser')
    headword = soup.find("strong", class_="tit_searchword")
    if headword is None:
        return None
    span = headword.find("span", class_="txt_emph1")
    sub_read = headword.find("a", class_="sub_read")
    if span is None or sub_read is None:
        return None
    hanzaimg = span.get_text(strip=True)
    hanzamean = _parse_readings(sub_read.get_text(strip=True))
    if not hanzaimg or not hanzamean:
        return None
    return hanzaimg, hanzamean


def searchhanza(hanza, attempts=3):
    stylex = Style.RESET_ALL
    for attempt in range(attempts):
        try:
            result = _fetch_daum_entry(hanza)
        except requests.exceptions.RequestException:
            result = None
        if result is not None:
            return result
        if attempt < attempts - 1:
            time.sleep(0.5)
    print(f'{Fore.RED}입력하신 한자를 찾을 수 없습니다.{stylex}', end='')
    return ";", ";"


def hanzasave1(hanza, group=1, grade=0):
    stylex = Style.RESET_ALL
    if hanzadata.find_entry(hanza):
        print(f'{Fore.RED}해당 한자가 이미 저장되어 있습니다{stylex}')
        return
    hanzaimg, hanzamean = searchhanza(hanza)
    if type(hanzamean) != list:
        print('\n')
        return
    if group:
        if hanza not in hanzamean:
            print(f"{Fore.RED}검색된 한자가 입력한 한자와 뜻이 다릅니다.{stylex}\n{Fore.GREEN}찾는 한자인가요?{stylex}")
            print(hanzaimg)
            print(",".join(hanzamean))
            a = input(f"{Fore.GREEN}Y{stylex}/{Fore.RED}N{stylex} : ")
            does_save(hanzaimg, hanzamean, a, grade)
        else:
            print(hanzaimg)
            print(hanzamean)
            a = input(f"{Fore.GREEN}저장할까요?\n\nY{stylex}/{Fore.RED}N{stylex} : ")
            does_save(hanzaimg, hanzamean, a, grade)
    else:
        print(hanzaimg, ':', hanzamean)
        does_save(hanzaimg, hanzamean, 'y', grade)
        return 1


def _fetch_soup(url):
    page = requests.get(url, headers=BROWSER_HEADERS, timeout=15)
    return BeautifulSoup(page.content, 'html.parser')


def _is_cjk_char(text):
    return len(text) == 1 and 0x4E00 <= ord(text) <= 0x9FFF


def _chars_from_tables(tables):
    chars = []
    for table in tables:
        for a in table.find_all('a'):
            text = a.get_text(strip=True)
            if _is_cjk_char(text):
                chars.append(text)
    return chars


def _section_tables(target_heading, section_headings):
    tables = []
    for el in target_heading.find_all_next():
        if any(el is h for h in section_headings):
            break
        if getattr(el, "name", None) == "table":
            tables.append(el)
    return tables


def _get_from_grade_list_page(grade):
    """5~8급: 나무위키 '한자/목록/급수별' 문서의 해당 급수 및 준N급(N급Ⅱ) 소제목 아래 표에서 가져온다.
    한국어문회 공식 배정한자는 N급Ⅱ 한자를 N급 시험 범위에 포함하므로 두 절을 합쳐서 반환한다."""
    soup = _fetch_soup(GRADE_LIST_URL)
    anchors = soup.find_all(id=re.compile(r"^s-2\.\d+$"))
    section_headings = [h for h in (a.find_parent(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) for a in anchors) if h]
    base_label = f"{grade}급[편집]"
    junior_label = f"준{grade}급[편집]"
    chars = []
    for heading in section_headings:
        text = heading.get_text(strip=True)
        match = re.search(r"([가-힣0-9]+급\[편집\])$", text)
        label = match.group(1) if match else text
        if label in (base_label, junior_label):
            chars.extend(_chars_from_tables(_section_tables(heading, section_headings)))
    return chars


def _get_from_grade_document(grade):
    """1~4급: 급수별 문서가 분리되어 있어 '전국한자능력검정시험/배정한자/N급' 문서에서 가져온다."""
    title = f"전국한자능력검정시험/배정한자/{grade}급"
    url = "https://namu.wiki/w/" + urllib.parse.quote(title)
    soup = _fetch_soup(url)
    return _chars_from_tables(soup.find_all("table"))


def get_hanza_list_by_grade(grade):
    """급수(1~8)에 해당하는 한자 목록을 나무위키에서 가져온다."""
    if grade >= 5:
        return _get_from_grade_list_page(grade)
    return _get_from_grade_document(grade)


def hanzasave2(inpu):
    chars = get_hanza_list_by_grade(inpu)
    for c in chars:
        hanzasave1(c, 0, inpu)
