# -*- coding: utf-8 -*-
# @Time    : 2024-04-04 15:11
# @Author  : WANG HAORAN
# @Email   : contact@haoran.co
# @PROJECT : emby_pinyin
# @File    : emby_pinyin.py
# Copyright (c) 2019-2023 WANG HAORAN


import argparse
import difflib
import re
from datetime import datetime
from pathlib import Path
from xml.dom import minidom

# pip install pypinyin
import pypinyin


class Config:
    VERSION = '1.0.0'
    SELECT_PINYIN = False
    PROCESS_TYPE = ['movie', 'tvshow']
    ORIG_TITLE_MODE = '$orig_title #($pinyin)'
    SORT_TITLE_MODE = '$pinyin #($title)'
    ORIG_TITLE_RE = (ORIG_TITLE_MODE.replace('(', r'\(').
                     replace(')', r'\)').
                     replace(' ', r'\s').
                     replace('$pinyin', '(.*?)').
                     replace('$orig_title', '(.*?)'))
    DIFF_DIR = './diff'
    BK_NODE_NAME = 'emby_pinyin_bk'
    LOG_FILE = f'./emby_pinyin.{datetime.now().strftime("%Y%m%d_%H%M")}.log'
    _LOG_FILE_OPEN = None
    NUM = 1

    @classmethod
    def init(cls):
        Path(cls.DIFF_DIR).mkdir(exist_ok=True)
        Path(cls.LOG_FILE).parent.mkdir(exist_ok=True)

    @classmethod
    def print(cls, text: str):
        if cls._LOG_FILE_OPEN is None:
            cls._LOG_FILE_OPEN = Path(cls.LOG_FILE).open('a', encoding='utf8')
        _time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        text = text.strip().replace('\n', f'\n{_time} ')
        text = f"{_time} {text}\n"
        cls._LOG_FILE_OPEN.write(text)
        print(text.strip())

    @classmethod
    def exit(cls):
        if cls._LOG_FILE_OPEN is not None:
            cls._LOG_FILE_OPEN.flush()
            cls._LOG_FILE_OPEN.close()
            cls._LOG_FILE_OPEN = None


def _print(text):
    Config.print(text)


def get_pinyin(text: str) -> str:
    """
    根据字符串，获取其拼音首字母
    几个逻辑：如果有其他数字、英文等字符的，如果有空格分开，那么就当作是一个个单词，添加单词的首字母，比如cute girl就会变成cg
    但是如果是连在一起的，没有空格分隔，就当作一整个字符串加入结果，比如3D就会加到结果里面
    :param text: 要处理的字符串
    :return: 返回拼音首字母，全小写
    """
    if not text:
        return ''
    pinyin = pypinyin.pinyin(text, style=pypinyin.NORMAL, heteronym=True)
    _count = 0
    # 先初步处理，包括多音字以及数字英文等
    for index, _p in enumerate(pinyin):
        if len(_p) > 1 and len(set([_i[0].lower() for _i in _p])) > 1:
            if Config.SELECT_PINYIN:
                _print('\n'.join(['\n-----注意------', f'处理文字 {text} 的过程中发现了多音字【{text[_count]}】，请选择哪一个发音'] +
                                 [f'{_n}. {_p[_n - 1]}' for _n in range(1, 1 + len(_p))]))
                _s = input('请输入您选择的序号，默认为1：').strip()
                _s = int(_s) if re.match(r'^\d+$', _s) else 1
                _s = _s if 1 <= _s <= len(_p) else 1
                _print(f'使用 {_p[_s - 1]} 作为结果！')
                pinyin[index] = [_p[_s - 1]]
                _count += 1
                continue

        # 返回了原本的字符串
        if len(_p) == 1 and _p[0] == text[_count:_count + len(_p[0])]:
            _count += len(_p[0])
            # 如果没有空格，是整体的英文+数字，那么就全部加入到结果中
            if re.match(r'^[0-9a-zA-Z]+$', _p[0]):
                pinyin[index] = [_t for _t in _p[0]]
            else:
                pinyin[index] = re.findall(r'[0-9a-zA-Z]+', _p[0])
            continue

        pinyin[index] = [_p[0]]
        _count += 1
    # 组合成拼音首字母
    _result = []
    for _p in pinyin:
        if len(_p) == 1:
            _result.append(_p[0][0])
        elif len(_p) > 1:
            _result.extend([_t[0] for _t in _p if _t])
    return ''.join(_result).replace(' ', '').lower()


def read_file(file_path):
    with Path(file_path).open('r', encoding='utf8') as _f:
        return _f.read()


def save_file(file_path, content: str):
    with Path(file_path).open('w', encoding='utf8') as _f:
        _f.write(content)
    return str(Path(file_path).absolute())


def diff_show(t1, t2, file_path):
    _diff = difflib.HtmlDiff()
    _result = _diff.make_file(t1.split('\n'), t2.split('\n'), context=True)
    with Path(file_path).open('w', encoding='utf8') as result_file:
        result_file.write(_result)


def judge_nfo_type(content: str) -> str:
    """
    根据nfo文件内容，判断这是一个电影，还是tvshow
    :param content: 文件内容
    :return: ['movie', 'tvshow', 'other']
    """
    try:
        _xml = minidom.parseString(content)
        _xml_roots = [_r.nodeName for _r in _xml.childNodes]
        for _t in ['movie', 'tvshow']:
            if _t in _xml_roots:
                return _t
    except:
        pass
    return 'other'


def _create_text_ele(node_name: str, text: str) -> minidom.Element:
    """
    创建一个文本的element，类似<title>xxx</title>
    :param node_name: node的名称
    :param text: 内容
    :return: text
    """
    _tmp = minidom.Element(node_name)
    _tmp.appendChild(minidom.Document().createTextNode(text))
    return _tmp


def process_nfo(content: str, xml_type: str, restore=False):
    """
    根据传进来的电影或者电视节目nfo文件内容，返回处理后的文件内容
    :param content: 电影或者电视节目nfo文件内容
    :param xml_type: movie or tvshow
    :param restore: 是要处理还是还原
    :return: 处理完毕的内容
    """
    _xml = minidom.parseString(content)
    _root_node = _xml.getElementsByTagName(xml_type)[0]
    _t_node: minidom.Element = [*_root_node.getElementsByTagName('title'), None][0]
    _ot_node: minidom.Element = [*_root_node.getElementsByTagName('originaltitle'), None][0]
    _st_node: minidom.Element = [*_root_node.getElementsByTagName('sorttitle'), None][0]

    # 先读取备份
    _bk_node: minidom.Element = [*_xml.getElementsByTagName(Config.BK_NODE_NAME), None][0]
    _bk_list = [_n.nodeName for _n in _bk_node.childNodes] if _bk_node else []
    # 只根据bk_node是否存在来判断这个文件是不是以前已经处理过了
    if _bk_node and not restore:
        # print('该文件已经处理过，将跳过！') # 可以在外面处理
        return content
    if restore and _bk_node is None:
        # 该文件没有处理过
        return content

    _title = _original_title = _sort_title = ''  # 初始化
    # 获取原数据
    _title = _t_node.firstChild.data if _t_node is not None and _t_node.firstChild is not None else _title
    _original_title = _ot_node.firstChild.data if _ot_node is not None and _ot_node.firstChild is not None else _original_title
    _sort_title = _st_node.firstChild.data if _st_node is not None and _st_node.firstChild is not None else _sort_title
    # 判断一下如果之前已经处理过，在这里恢复_original_title，保险起见
    _ot_match = re.match(r'(.*?)\s#\((.*?)\)', _original_title)
    if _ot_match:
        # original_title已经符合被处理后的文本，则恢复信息
        _original_title = _ot_match.group(1)

    # 开始处理，处理拼音排序以及拼音搜索
    if not restore:
        _pinyin = get_pinyin(_title if _title else _original_title)
        _result_ot = Config.ORIG_TITLE_MODE.replace('$orig_title', _original_title).replace('$pinyin', _pinyin).strip()
        _result_st = Config.SORT_TITLE_MODE.replace('$pinyin', _pinyin).replace('$title', _title).strip()

        # 生成并替换新的element
        if _original_title != _result_ot:
            _print(f"替换originaltitle：{_original_title} --> {_result_ot}")
            _root_node.replaceChild(_create_text_ele('originaltitle', _result_ot), _ot_node) \
                if _ot_node else _root_node.appendChild(_create_text_ele('originaltitle', _result_ot.replace(')', f' {_title})')))
        if _sort_title != _result_st:
            _print(f"替换sorttitle：{_sort_title} --> {_result_st}")
            _root_node.replaceChild(_create_text_ele('sorttitle', _result_st), _st_node) \
                if _st_node else _root_node.appendChild(_create_text_ele('sorttitle', _result_st))

        # 生成备份信息
        _new_bk = minidom.Element(Config.BK_NODE_NAME)
        if _t_node:
            _new_bk.appendChild(_create_text_ele('title', _title))
        if _ot_node:
            _new_bk.appendChild(_create_text_ele('originaltitle', _original_title))
        if _st_node:
            _new_bk.appendChild(_create_text_ele('sorttitle', _sort_title))
        _new_bk.appendChild(_create_text_ele('bk_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        # 添加备份信息
        _print(f'添加了备份信息：{_new_bk.toxml()}')
        _root_node.appendChild(_new_bk)

    # 恢复原貌
    else:
        # 还原标题
        _print(f"恢复以下信息：{[_x for _x in ['title', 'originaltitle', 'sorttitle'] if _x in _bk_list]}")
        for _name, _node in zip(['title', 'originaltitle', 'sorttitle'], [_t_node, _ot_node, _st_node]):
            if _name in _bk_list:
                _root_node.replaceChild(
                    _bk_node.getElementsByTagName(_name)[0], _node
                ) if _node else _root_node.appendChild(_bk_node.getElementsByTagName(_name)[0])
            else:
                _root_node.removeChild(_node) if _node else None

        # 删除备份信息
        _root_node.removeChild(_bk_node)

    _str = (_xml.toprettyxml(indent='  ', standalone=True).
            replace('version="1.0"', 'version="1.0" encoding="UTF-8"'))
    _str = re.sub(r' +\n+', '\n', _str)
    _str = re.sub(r'\n\n+', '\n', _str).strip()
    return _str


def process_dir(root_dir, restore=False, dry_run=True):
    """
    批处理一个文件夹内所有的nfo文件
    :param root_dir: 文件夹路径
    :param restore: 恢复模式还是处理模式
    :param dry_run: 不实际更改文件，只把文件的变化写出来
    :return:
    """
    if not (Path(root_dir).exists() and Path(root_dir).is_dir()):
        _print(f'文件夹不存在，检查一下有没有输入错误哦： {root_dir}')
        return

    _no_modify_list = []
    _print(f'Hi~\n开始处理文件夹：{root_dir}'
           f'  处理模式：{"正常模式" if not restore else "恢复模式"}')
    for _nfo in Path(root_dir).rglob('*.nfo'):
        try:
            if not _nfo.is_file():
                continue

            _file_content = read_file(_nfo)
            _xml_type = judge_nfo_type(_file_content)
            if _xml_type not in Config.PROCESS_TYPE:
                continue

            print('')
            _print(f'处理第 {Config.NUM} 个文件：{_nfo.absolute()}')

            _processed_content = process_nfo(_file_content, _xml_type, restore)
            if _processed_content is None:
                _print(f'文件非电影或电视节目的nfo文件，将跳过：{_nfo.absolute()}')
            elif _processed_content != _file_content:
                _diff_html = Path(Config.DIFF_DIR) / f'[{Config.NUM}]{_nfo.parent.name}--{_nfo.name}.diff.html'
                diff_show(_file_content, _processed_content, _diff_html)
                _print(f'处理后的文件差异见：{_diff_html}')
                if not dry_run:
                    save_file(_nfo, _processed_content)
                    _print(f'已覆盖写入文件：{_nfo}')
                else:
                    _print("dry run模式，未写入文件")

            else:
                _no_modify_list.append(_nfo)

            Config.NUM += 1
        except Exception as _e:
            _print(f'ERROR 处理文件 {_nfo} 的时候出错了, 将继续下一个文件，错误信息： {_e}')

    if _no_modify_list:
        print('')
        _print(f'文件夹{root_dir} 中有 {len(_no_modify_list)} 个文件由于已经处理过或无法处理，将不会产生变化: ')
        for _index, _file in enumerate(_no_modify_list):
            _print(f'{_index}\t{_file}')


if __name__ == '__main__':
    arg_parse = argparse.ArgumentParser('Emby-Pinyin',
                                        description='Emby拼音首字母搜索和按拼音排序，通过修改nfo文件达到效果，仅会处理电影与电视剧的nfo文件，不处理季、集的文件，\n'
                                                    '程序将修改nfo文件中的originaltitle和sorttitle两个字段，并且会备份原有信息，\n'
                                                    '修改后可以实现用拼音首字母搜索、按照拼音首字母排序的效果。\n'
                                                    '通过传入--restore指令可以恢复程序对nfo文件做出的修改。\n'
                                                    '如果只想看一下程序将如何对你的文件进行处理，可传入--dry-run或者-n。\n'
                                                    '程序对你的文件做出的修改将以html格式保存在 ./diff 文件夹中，可通过--diff-out指定文件夹。\n'
                                                    '程序使用自动化xml生成程序，可能会将原文件中不规范的的 双引号 替换为 &quot; ，这不是程序错误哦。',
                                        formatter_class=argparse.RawDescriptionHelpFormatter)
    arg_parse.add_argument('-d', '--dir', dest='dirs', nargs='*', required=True,
                           help='指定要处理的文件夹，支持多个文件夹传入，注意用引号包裹含有空格的路径')
    arg_parse.add_argument('-t', '--type', dest='type', choices=['movie', 'tvshow', 'both'], default='both',
                           help='指定要处理的媒体类型，默认电影和电视节目都处理')
    arg_parse.add_argument('-r', '--restore', dest='restore', action='store_true', help='将已经修改的文件重置回到原状态')
    arg_parse.add_argument('-n', '--dry-run', dest='dry_run', action='store_true', help='不修改实际文件，只展示处理过程和修改的地方')
    arg_parse.add_argument('-s', '--select-pinyin', dest='select_pinyin', action='store_true', help='当出现多音字的时候，手动选择拼英')
    arg_parse.add_argument('-o', '--diff-out', dest='diff_dir', default='./diff', help='保存显示差异的文件夹，默认当前文件夹下的diff文件夹')
    arg_parse.add_argument('-l', '--log', dest='log_file', default='./emby_pinyin.log',
                           help='保存程序运行日志的文件路径，默认未当前文件夹下的emby_pinyin.log')
    arg_parse.add_argument('-v', '--version', dest='version', action='version', version=Config.VERSION, help='查看程序的版本号')
    args = arg_parse.parse_args()

    Config.SELECT_PINYIN = args.select_pinyin
    Config.DIFF_DIR = args.diff_dir
    Config.LOG_FILE = Path(args.log_file).parent / f'{Path(args.log_file).stem}.{datetime.now().strftime("%Y%m%d_%H%M")}{Path(args.log_file).suffix}'
    Config.PROCESS_TYPE = [args.type] if args.type != 'both' else Config.PROCESS_TYPE
    Config.init()

    try:
        for _dir in args.dirs:
            process_dir(_dir, args.restore, args.dry_run)
    except Exception as e:
        _print(f'ERROR 程序运行过程中出错了：{e}')
    finally:
        Config.exit()
