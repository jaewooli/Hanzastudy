from colorama import Fore, Style

import hanzadata


def main():
    stylex = Style.RESET_ALL
    while 1:
        content = input(f"사전에서 {Fore.RED}삭제{stylex}할 한자를 입력하세요.\n")
        if content == "H" or content == 'h' or content == 'help':
            print(f"사전에서 {Fore.RED}삭제{stylex}할 한자를 입력해주세요!\n{Fore.RED}종료{stylex} : 한자 삭제를 종료합니다")
        elif content == "종료":
            break
        elif content == "all":
            hanzadata.clear_all()
            break
        else:
            deletehanza(content)


def deletehanza(content):
    stylex = Style.RESET_ALL
    entry = hanzadata.find_entry(content)
    if entry:
        hanja, means, grade = entry
        print(f"{Fore.RED}해당 한자를 삭제합니다{stylex}")
        print(hanja, ':', ', '.join(means), "\n")
        hanzadata.delete_entry(hanja)
    else:
        print(f"{Fore.RED}해당 한자가 사전에 등록되어있지 않습니다.{stylex}\n")
