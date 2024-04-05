# emby_pinyin
简单实现emby按照拼音首字母排序、按照拼音首字母查询

## 主要功能介绍（详细功能用-h查看）
Emby拼音首字母搜索和按拼音排序，通过修改nfo文件达到效果，仅会处理电影与电视剧的nfo文件，不处理季、集的文件，程序将修改nfo文件中的originaltitle和sorttitle两个字段，并且会备份原有信息，修改后可以实现用拼音首字母搜索、按照拼音首字母排序的效果。  
通过传入--restore指令可以恢复程序对nfo文件做出的修改。如果只想看一下程序将如何对你的文件进行处理，可传入--dry-run或者-n。程序对你的文件做出的修改将以html格式保存在 ./diff 文件夹中，可通过--diff-out指定文件夹。  
程序使用自动化xml生成程序，可能会将原文件中不规范的的 双引号 替换为 &quot; ，这不是程序错误哦。  

## 使用实例
最简单的使用方式：  
`python emby_pinyin.py -n -d '文件夹'`  
其中-n参数是不实际修改文件，但是展示修改的过程和修改的内容，检查无误后，去掉-n参数，程序就可以真正工作了。

## 原理简介
在nfo文件中有3个字段title、originaltitle、sorttitle，这三个字段被emby程序读取并运用在搜索和排序过程中，其中title是对外显示的标题，并参与搜索，originaltitle不对外显示，但是参与搜素，sorttitle只用于排序，不用于展示和搜索，为了实现拼音首字母搜索和排序，将把拼音首字母添加到originaltitle、sorttitle两个字段中，originaltitle字段将被修改成'$orig_title #($pinyin)'的形式，例如：我本是高山 #(wbsgs)，sorttitle将被修改为'$pinyin #($title)'，例如：wbsgs #(我本是高山)，这样就同时实现了拼音首字母搜索和排序。  

## 欢迎交流~
欢迎交流~
