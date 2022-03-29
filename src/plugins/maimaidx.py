from collections import defaultdict

from nonebot import on_command, on_regex,logger
from nonebot.typing import T_State
from nonebot.adapters import Event, Bot
from nonebot.adapters.cqhttp import Message
from PIL import Image
import os
import  requests,json

from src.libraries.tool import hash
from src.libraries.maimaidx_music import *
from src.libraries.image import *
from src.libraries.maimai_best_40 import generate
from src.libraries.maimai_best_50 import generate50
from src.libraries.enet_b50 import enetgenerate50
from src.libraries.enet import *
import re
import pymysql


def song_txt(music: Music):
    return Message([
        {
            "type": "text",
            "data": {
                "text": f"{music.id}. {music.title}\n"
            }
        },
        {
            "type": "image",
            "data": {
                "file": f"https://www.diving-fish.com/covers/{music.id}.jpg"
            }
        },
        {
            "type": "text",
            "data": {
                "text": f"\n{'/'.join(music.level)}"
            }
        }
    ])


def inner_level_q(ds1, ds2=None):
    result_set = []
    diff_label = ['Bas', 'Adv', 'Exp', 'Mst', 'ReM']
    if ds2 is not None:
        music_data = total_list.filter(ds=(ds1, ds2))
    else:
        music_data = total_list.filter(ds=ds1)
    for music in sorted(music_data, key = lambda i: int(i['id'])):
        for i in music.diff:
            result_set.append((music['id'], music['title'], music['ds'][i], diff_label[i], music['level'][i]))
    return result_set


inner_level = on_command('inner_level ', aliases={'定数查歌 '})


@inner_level.handle()
async def _(bot: Bot, event: Event, state: T_State):
    argv = str(event.get_message()).strip().split(" ")
    if len(argv) > 2 or len(argv) == 0:
        await inner_level.finish("命令格式为\n定数查歌 <定数>\n定数查歌 <定数下限> <定数上限>")
        return
    if len(argv) == 1:
        result_set = inner_level_q(float(argv[0]))
    else:
        result_set = inner_level_q(float(argv[0]), float(argv[1]))
    if len(result_set) > 50:
        await inner_level.finish(f"结果过多（{len(result_set)} 条），请缩小搜索范围。")
        return
    s = ""
    for elem in result_set:
        s += f"{elem[0]}. {elem[1]} {elem[3]} {elem[4]}({elem[2]})\n"
    await inner_level.finish(s.strip())


spec_rand = on_regex(r"^随个(?:dx|sd|标准)?[绿黄红紫白]?[0-9]+\+?")


@spec_rand.handle()
async def _(bot: Bot, event: Event, state: T_State):
    level_labels = ['绿', '黄', '红', '紫', '白']
    regex = "随个((?:dx|sd|标准))?([绿黄红紫白]?)([0-9]+\+?)"
    res = re.match(regex, str(event.get_message()).lower())
    try:
        if res.groups()[0] == "dx":
            tp = ["DX"]
        elif res.groups()[0] == "sd" or res.groups()[0] == "标准":
            tp = ["SD"]
        else:
            tp = ["SD", "DX"]
        level = res.groups()[2]
        if res.groups()[1] == "":
            music_data = total_list.filter(level=level, type=tp)
        else:
            music_data = total_list.filter(level=level, diff=['绿黄红紫白'.index(res.groups()[1])], type=tp)
        if len(music_data) == 0:
            rand_result = "没有这样的乐曲哦。"
        else:
            rand_result = song_txt(music_data.random())
        await spec_rand.send(rand_result)
    except Exception as e:
        print(e)
        await spec_rand.finish("随机命令错误，请检查语法")


mr = on_regex(r".*maimai.*什么")


@mr.handle()
async def _(bot: Bot, event: Event, state: T_State):
    await mr.finish(song_txt(total_list.random()))


search_music = on_regex(r"^查歌.+")


@search_music.handle()
async def _(bot: Bot, event: Event, state: T_State):
    regex = "查歌(.+)"
    name = re.match(regex, str(event.get_message())).groups()[0].strip()
    if name == "":
        return
    res = total_list.filter(title_search=name)
    if len(res) == 0:
        await search_music.send("没有找到这样的乐曲。")
    elif len(res) < 50:
        search_result = ""
        for music in sorted(res, key = lambda i: int(i['id'])):
            search_result += f"{music['id']}. {music['title']}\n"
        await search_music.finish(Message([
            {"type": "text",
                "data": {
                    "text": search_result.strip()
                }}]))
    else:
        await search_music.send(f"结果过多（{len(res)} 条），请缩小查询范围。")


query_chart = on_regex(r"^([绿黄红紫白]?)id([0-9]+)")


@query_chart.handle()
async def _(bot: Bot, event: Event, state: T_State):
    regex = "([绿黄红紫白]?)id([0-9]+)"
    groups = re.match(regex, str(event.get_message())).groups()
    level_labels = ['绿', '黄', '红', '紫', '白']
    if groups[0] != "":
        try:
            level_index = level_labels.index(groups[0])
            level_name = ['Basic', 'Advanced', 'Expert', 'Master', 'Re: MASTER']
            name = groups[1]
            music = total_list.by_id(name)
            chart = music['charts'][level_index]
            ds = music['ds'][level_index]
            level = music['level'][level_index]
            file = f"https://www.diving-fish.com/covers/{music['id']}.jpg"
            if len(chart['notes']) == 4:
                msg = f'''{level_name[level_index]} {level}({ds})
TAP: {chart['notes'][0]}
HOLD: {chart['notes'][1]}
SLIDE: {chart['notes'][2]}
BREAK: {chart['notes'][3]}
谱师: {chart['charter']}'''
            else:
                msg = f'''{level_name[level_index]} {level}({ds})
TAP: {chart['notes'][0]}
HOLD: {chart['notes'][1]}
SLIDE: {chart['notes'][2]}
TOUCH: {chart['notes'][3]}
BREAK: {chart['notes'][4]}
谱师: {chart['charter']}'''
            await query_chart.send(Message([
                {
                    "type": "text",
                    "data": {
                        "text": f"{music['id']}. {music['title']}\n"
                    }
                },
                {
                    "type": "image",
                    "data": {
                        "file": f"{file}"
                    }
                },
                {
                    "type": "text",
                    "data": {
                        "text": msg
                    }
                }
            ]))
        except Exception:
            await query_chart.send("未找到该谱面")
    else:
        name = groups[1]
        music = total_list.by_id(name)
        try:
            file = f"https://www.diving-fish.com/covers/{music['id']}.jpg"
            await query_chart.send(Message([
                {
                    "type": "text",
                    "data": {
                        "text": f"{music['id']}. {music['title']}\n"
                    }
                },
                {
                    "type": "image",
                    "data": {
                        "file": f"{file}"
                    }
                },
                {
                    "type": "text",
                    "data": {
                        "text": f"艺术家: {music['basic_info']['artist']}\n分类: {music['basic_info']['genre']}\nBPM: {music['basic_info']['bpm']}\n版本: {music['basic_info']['from']}\n难度: {'/'.join(music['level'])}"
                    }
                }
            ]))
        except Exception:
            await query_chart.send("未找到该乐曲")


wm_list = ['拼机', '推分', '越级', '下埋', '夜勤', '练底力', '练手法', '打旧框', '干饭', '抓绝赞', '收歌']


jrwm = on_command('今日舞萌', aliases={'今日mai'})


@jrwm.handle()
async def _(bot: Bot, event: Event, state: T_State):
    qq = int(event.get_user_id())
    h = hash(qq)
    rp = h % 100
    wm_value = []
    for i in range(11):
        wm_value.append(h & 3)
        h >>= 2
    s = f"今日人品值：{rp}\n"
    for i in range(11):
        if wm_value[i] == 3:
            s += f'宜 {wm_list[i]}\n'
        elif wm_value[i] == 0:
            s += f'忌 {wm_list[i]}\n'
    s += "烧鹅提醒您：打机时不要大力拍打或滑动哦\n今日推荐歌曲："
    music = total_list[h % len(total_list)]
    await jrwm.finish(Message([
        {"type": "text", "data": {"text": s}}
    ] + song_txt(music)))


music_aliases = defaultdict(list)
f = open('src/static/aliases.csv', 'r', encoding='utf-8')
tmp = f.readlines()
f.close()
for t in tmp:
    arr = t.strip().split('\t')
    for i in range(len(arr)):
        if arr[i] != "":
            music_aliases[arr[i].lower()].append(arr[0])


find_song = on_regex(r".+是什么歌")


@find_song.handle()
async def _(bot: Bot, event: Event, state: T_State):
    regex = "(.+)是什么歌"
    name = re.match(regex, str(event.get_message())).groups()[0].strip().lower()
    if name not in music_aliases:
        await find_song.finish("未找到此歌曲\n舞萌 DX 歌曲别名收集计划：https://docs.qq.com/sheet/DQ0pvUHh6b1hjcGpl")
        return
    result_set = music_aliases[name]
    if len(result_set) == 1:
        music = total_list.by_title(result_set[0])
        await find_song.finish(Message([{"type": "text", "data": {"text": "您要找的是不是"}}] + song_txt(music)))
    else:
        s = '\n'.join(result_set)
        await find_song.finish(f"您要找的可能是以下歌曲中的其中一首：\n{ s }")


query_score = on_command('分数线')


@query_score.handle()
async def _(bot: Bot, event: Event, state: T_State):
    r = "([绿黄红紫白])(id)?([0-9]+)"
    argv = str(event.get_message()).strip().split(" ")
    if len(argv) == 1 and argv[0] == '帮助':
        s = '''此功能为查找某首歌分数线设计。
命令格式：分数线 <难度+歌曲id> <分数线>
例如：分数线 紫799 100
命令将返回分数线允许的 TAP GREAT 容错以及 BREAK 50落等价的 TAP GREAT 数。
以下为 TAP GREAT 的对应表：
GREAT/GOOD/MISS
TAP\t1/2.5/5
HOLD\t2/5/10
SLIDE\t3/7.5/15
TOUCH\t1/2.5/5
BREAK\t5/12.5/25(外加200落)'''
        await query_score.send(Message([{
            "type": "image",
            "data": {
                "file": f"base64://{str(image_to_base64(text_to_image(s)), encoding='utf-8')}"
            }
        }]))
    elif len(argv) == 2:
        try:
            grp = re.match(r, argv[0]).groups()
            level_labels = ['绿', '黄', '红', '紫', '白']
            level_labels2 = ['Basic', 'Advanced', 'Expert', 'Master', 'Re:MASTER']
            level_index = level_labels.index(grp[0])
            chart_id = grp[2]
            line = float(argv[1])
            music = total_list.by_id(chart_id)
            chart: Dict[Any] = music['charts'][level_index]
            tap = int(chart['notes'][0])
            slide = int(chart['notes'][2])
            hold = int(chart['notes'][1])
            touch = int(chart['notes'][3]) if len(chart['notes']) == 5 else 0
            brk = int(chart['notes'][-1])
            total_score = 500 * tap + slide * 1500 + hold * 1000 + touch * 500 + brk * 2500
            break_bonus = 0.01 / brk
            break_50_reduce = total_score * break_bonus / 4
            reduce = 101 - line
            if reduce <= 0 or reduce >= 101:
                raise ValueError
            await query_chart.send(f'''{music['title']} {level_labels2[level_index]}
分数线 {line}% 允许的最多 TAP GREAT 数量为 {(total_score * reduce / 10000):.2f}(每个-{10000 / total_score:.4f}%),
BREAK 50落(一共{brk}个)等价于 {(break_50_reduce / 100):.3f} 个 TAP GREAT(-{break_50_reduce / total_score * 100:.4f}%)''')
        except Exception:
            await query_chart.send("格式错误，输入“分数线 帮助”以查看帮助信息")


best_40_pic = on_command('b40')


@best_40_pic.handle()
async def _(bot: Bot, event: Event, state: T_State):
    username = str(event.get_message()).strip()
    if username == "":
        payload = {'qq': str(event.get_user_id())}
    else:
        payload = {'username': username}
    img, success = await generate(payload)
    if success == 400:
        await best_40_pic.send("未找到此玩家，请确保此玩家的用户名和查分器中的用户名相同。")
    elif success == 403:
        await best_40_pic.send("该用户禁止了其他人获取数据。")
    else:
        await best_40_pic.send(Message([
            {
                "type": "image",
                "data": {
                    "file": f"base64://{str(image_to_base64(img), encoding='utf-8')}"
                }
            }
        ]))

best_50_pic = on_command('b50')


@best_50_pic.handle()
async def _(bot: Bot, event: Event, state: T_State):
    username = str(event.get_message()).strip()
    if username == "":
        payload = {'qq': str(event.get_user_id()),'b50':True}
    else:
        payload = {'username': username,'b50':  True}
    img, success = await generate50(payload)
    print(img,success)
    if success == 400:
        await best_50_pic.send("未找到此玩家，请确保此玩家的用户名和查分器中的用户名相同。")
    elif success == 403:
        await best_50_pic.send("该用户禁止了其他人获取数据。")
    else:
        await best_50_pic.send(Message([
            {
                "type": "image",
                "data": {
                    "file": f"base64://{str(image_to_base64(img), encoding='utf-8')}"
                }
            }
        ]))

enetbest_50_pic = on_command('鹅网b50')


@enetbest_50_pic.handle()
async def _(bot: Bot, event: Event, state: T_State):
    qq = str(event.get_user_id())
    aime = aimesearch(qq)
    userid = searchId(aime)
    img, success = enetgenerate50(userid)
    logger.info(img)
    logger.info(success)
    await enetbest_50_pic.send(Message([
        {
            "type": "image",
            "data": {
                "file": f"base64://{str(image_to_base64(img), encoding='utf-8')}"
            }
        }
    ]))


tql = on_regex(r".*CQ:image,file.*")


@tql.handle()
async def _(bot: Bot, event: Event, state: T_State):
    qq = str(event.get_user_id())
    if qq == '652099302' :
        await tql.finish('tql')
        


tql2 = on_command('tql', aliases={'太强了', '无敌', '飞升'})

@tql2.handle()
async def _(bot: Bot, event: Event, state: T_State):
    qq = str(event.get_user_id())
    if qq == '652099302':
        await tql2.finish('那还得是您比较强')

jj = on_command('jjw', aliases={'教教', '教我', '浇浇', 'jiaojiao', 'jj','jw','这不教我','zbjw'})

@jj.handle()
async def _(bot: Bot, event: Event, state: T_State):
    qq = str(event.get_user_id())
    if qq == '652099302':
        await jj.finish('先教我先教我')

mr = on_command('卖弱', aliases={'脉弱', '麦若', 'mairuo', '买若', '卖若','脉络'})

@mr.handle()
async def _(bot: Bot, event: Event, state: T_State):
    qq = str(event.get_user_id())
    if qq == '652099302':
        await mr.finish('卖弱还是你比较在行')

nin = on_command('您', aliases={'您们', 'nin', })

@nin.handle()
async def _(bot: Bot, event: Event, state: T_State):
    qq = str(event.get_user_id())
    if qq == '652099302':
        await nin.finish('还得是您')



dragonpic = on_command('龙图')

@dragonpic.handle()
async def _(bot: Bot, event: Event, state: T_State):
    alls = readdir()
    simple = (random.sample(alls, 1))
    strsimple = ','.join(simple)
    await dragonpic.send(Message([
            {
                "type": "image",
                "data": {
                    "file": f"file:///home/pi/mai-bot/src/static/dragonpic/{strsimple}"
                }
            }
        ]))

def readdir():
    allfiles = os.listdir("/home/pi/mai-bot/src/static/dragonpic")
    # print(allfiles)
    return allfiles


title = on_command('maimai牌子')
@title.handle()

async def _(bot: Bot, event: Event, state: T_State):
    await dragonpic.send(Message([
            {
                "type": "image",
                "data": {
                    "file": "file:///home/pi/mai-bot/src/static/mai/title.png"
                }
            }
        ]))

fuxin = on_command('/缚心', aliases={'/fuxin', '/负心'})

@fuxin.handle()
async def _(bot: Bot, event: Event, state: T_State):
    alls1 = readdirfuxin()
    simple1 = (random.sample(alls1, 1))
    strsimple1 = ','.join(simple1)
    await fuxin.send(Message([
            {
                "type": "image",
                "data": {
                    "file": f"file:///home/pi/mai-bot/src/static/fuxin/{strsimple1}"
                }
            }
        ]))

def readdirfuxin():
    allfiles1 = os.listdir("/home/pi/mai-bot/src/static/fuxin")
    # print(allfiles)
    return allfiles1

paopao = on_command('/泡泡', aliases={'/paopao', '/炮炮', '/跑跑', '/狍狍'})

@paopao.handle()
async def _(bot: Bot, event: Event, state: T_State):
    alls2 = readdirpaopao()
    simple2 = (random.sample(alls2, 1))
    strsimple2 = ','.join(simple2)
    await paopao.send(Message([
            {
                "type": "image",
                "data": {
                    "file": f"file:///home/pi/mai-bot/src/static/paopao/{strsimple2}"
                }
            }
        ]))

def readdirpaopao():
    allfiles2 = os.listdir("/home/pi/mai-bot/src/static/paopao")
    # print(allfiles)
    return allfiles2


wkl = on_command('乌克兰', aliases={'俄罗斯', '俄罗斯乌克兰', '乌克兰与俄罗斯', '基辅', '毛子', '普京大帝', '普京'})

@wkl.handle()
async def _(bot: Bot, event: Event, state: T_State):
    alls3 = readdirwkl()
    simple3 = (random.sample(alls3, 1))
    strsimple3 = ','.join(simple3)
    await wkl.send(Message([
            {
                "type": "image",
                "data": {
                    "file": f"file:///home/pi/mai-bot/src/static/wkl/{strsimple3}"
                }
            }
        ]))

def readdirwkl():
    allfiles3 = os.listdir("/home/pi/mai-bot/src/static/wkl")
    # print(allfiles)
    return allfiles3


cet4 = on_command('四六级')

@cet4.handle()
async def _(bot: Bot, event: Event, state: T_State):
        await cet4.finish('爸💎妈💎不💎在💎家💎\n一💎个💎人💎寂💎寞💎\n打开四六级官网📱\n来一次尽情享受❤️\nv我查分🉐\n给我从未有过的体验💕\n🔥四🔥六🔥级🔥查🔥分🔥\n❤️❤️💎星期四💎❤️❤️\n❤️💎❤️lets get❤️\n crazy！\n未止\nhttp://cet.neea.edu.cn/cet/')


hll = on_command('货拉拉拉不拉拉布拉多')

@hll.handle()
async def _(bot: Bot, event: Event, state: T_State):
        await hll.finish('货拉拉拉不拉拉布拉多取决于货拉拉上拉的拉布拉多拉得多不多')


def gupiao(code:str):
    url = 'http://hq.sinajs.cn/list=' + code
    req = requests.get(url,headers={"Referer":"https://finance.sina.com.cn/"})
    result = req.text
    arr1 = result.split('=')
    arr2 = arr1[1].split('"')
    arr3 = arr2[1].split(",")
    logger.info(arr3)
    return arr3

gupiao2 = on_regex(r"^股票.+")

@gupiao2.handle()
async def _(bot: Bot, event: Event, state: T_State):
    regex = "股票(.+)"
    code1 = re.match(regex, str(event.get_message())).groups()[0].strip()
    logger.info(code1)
    if code1 == "":
        return
    res = gupiao(code1)
    # await gupiao2.finish(res)
    if len(res) == 0:
        await gupiao2.send("没有找到这个股票")
    else:
        await gupiao2.send(f"股票名字：{res[0]}\n今日开盘：{res[1]}\n昨日收盘：{res[2]}\n当前价格：{res[3]}\n今日最高价：{res[4]}\n今日最低价：{res[5]}\n当前日期：{res[30]}\n刷新时间：{res[31]}\n烧鹅提醒您：\n投资有风险\n入市需谨慎\n又在摸鱼炒股啊，我替老板求求你上会儿班吧")

dnm = on_command('广州市市歌')

@dnm.handle()
async def _(bot: Bot, event: Event, state: T_State):
    await dnm.send(Message([
            {
                "type": "record",
                "data": {
                    "file": f"file:///home/pi/mai-bot/src/static/record/dnm.mp3"
                }
            }
        ]))

# kop = on_command('/kop链接')

# @kop.handle()
# async def _(bot: Bot, event: Event, state: T_State):
#     await kop.finish("万众期待的SEGA系街机音游比赛——KING of Performai 3rd即将在今天2/27 11:00(北京时间) 正式开幕! 注意是北京时间哦！\n油管官方观看：http://t.cn/A66zt9xm\n也有国内部分的朋友提供友情转播+非官方解说：\n\n虎牙直播平台：http://t.cn/A66zt9xE 三机种全程直播解说\n主播：@GameG游戏基\n嘉宾：@小豆亚麻 @内田玛雅\n\nbilibili: http://t.cn/A66zt9xn maimai侧直播解说\n主播：@桜語不詳_SAKURAGO")

# enet = on_regex(r"^鹅网信息.+")
enet = on_command("鹅网信息")

@enet.handle()
async def _(bot: Bot, event: Event, state: T_State):
    # regex = "鹅网信息(.+)"
    # aime = re.match(regex, str(event.get_message())).groups()[0].strip()
    qq = str(event.get_user_id())
    aime = aimesearch(qq)
    logger.info(aime)
    if aime == "":
        return
    userid = searchId(aime)
    if userid == 'null':
        await enet.send("没有找到这个玩家")
    else:
        info = searchMaiInfo(userid)
        await enet.send(f"玩家名字：{info['userName']}\n最近游戏时间：{info['lastPlayDate']}\n玩家Rating：{info['playerRating']}")

def searchId(aime:str):
    url = 'http://youraquaurl/api/sega/aime/getByAccessCode'
    data1 = {'accessCode':aime}
    datajs = json.dumps(data1)
    logger.info(datajs)
    req = requests.post(url,data=datajs,headers={"Content-Type":"application/json"},verify = False)
    result = req.text
    if result == 'null':
        return "null"
    else:    
        req1 = json.loads(result)
        extid = req1['extId']
        logger.info(extid)
        return extid

def searchMaiInfo(Userid:str):
    url = 'http://youraquaurl/Maimai2Servlet/Maimai2Servlet/GetUserPreviewApi'
    data1 = {'userId':Userid, 'segaIdAuthKey': ""}
    datajs = json.dumps(data1)
    logger.info(datajs)
    req = requests.post(url,data=datajs,headers={"Content-Type":"application/json"},verify = False)
    result = req.text
    req1 = json.loads(result)
    logger.info(req1)
    return req1


enetcard = on_regex(r"^鹅网绑卡.+")

@enetcard.handle()
async def _(bot: Bot, event: Event, state: T_State):
    regex = "鹅网绑卡(.+)"
    aime = re.match(regex, str(event.get_message())).groups()[0].strip()
    qq = str(event.get_user_id())
    logger.info(aime)
    if aime == "":
        await enetcard.send("没有输入卡号绑你妈呢")
        return
    else:
        aimeblind(qq,aime)
        await enetcard.send(f"已绑定\nQQ：{qq}\nAime卡号：{aime}")
    # if aime == "":
    #     return
    # userid = searchId(aime)
    # if userid == 'null':
    #     await enet.send("没有找到这个玩家")
    # else:
    #     info = searchMaiInfo(userid)
    #     await enet.send(f"玩家名字：{info['userName']}\n最近游戏时间：{info['lastPlayDate']}\n玩家Rating：{info['playerRating']}")

def aimeblind(qq:str,aime:str):
    conn=pymysql.connect(host='localhost',user='root',password='pw')
    conn.select_db('aime_card')
    cur=conn.cursor()#获取游标
    insert=cur.execute(f"insert into aime (qq,aime) values('{qq}','{aime}')")
    print('添加语句受影响的行数：',insert)
    cur.close()
    conn.commit()
    conn.close()
    print('sql执行成功')    

def aimesearch(qq):
    conn = pymysql.connect(host='localhost',user = "root",password = "pw",db = "aime_card")
    cursor=conn.cursor()
    cursor.execute(f"select aime from aime where qq = '{qq}';")
    while 1:
        res=cursor.fetchone()
        if res is None:
            #表示已经取完结果集
            break
        print (res)
        out = res[0]
    cursor.close()
    conn.commit()
    conn.close()
    return out

enetsearchPhoto = on_command("鹅网图片查询")

@enetsearchPhoto.handle()
async def _(bot: Bot, event: Event, state: T_State):
    qq = str(event.get_user_id())
    aime = aimesearch(qq)
    logger.info(aime)
    if aime == "":
        return
    userid = searchId(aime)
    if userid == 'null':
        await enetsearchPhoto.send("没有找到这个玩家")
    else:
        info = searchMaiInfo(userid)
        photolist = allphoto(userid)
        print(userid)
        print('============')
        print(photolist)
        if len(photolist) != 0:
            result = handlePlist(photolist)
            await enetsearchPhoto.send(f"玩家名字：{info['userName']}\n图片时间列表：\n{result}")
        else:
            await enetsearchPhoto.send(f"玩家名字：{info['userName']}\n你还没有上传过图片，还不赶紧去机厅打mai")    


def handlePlist(plist):
    out = ''
    for i in range(0, len(plist)):
        out = f"{out}{i+1}、{plist[i]}\n"
    return out

enetdownPhoto = on_regex(r"^鹅网图片下载.+")

@enetdownPhoto.handle()
async def _(bot: Bot, event: Event, state: T_State):
    regex = "鹅网图片下载(.+)"
    phtime = re.match(regex, str(event.get_message())).groups()[0].strip()
    qq = str(event.get_user_id())
    aime = aimesearch(qq)
    # logger.info(aime)
    if aime == "":
        return
    userid = searchId(aime)
    if userid == 'null':
        await enetdownPhoto.send("没有找到这个玩家")
    else:
        photoname = downloadPhoto(userid=userid,photo=phtime)
        await enetdownPhoto.send(Message([
            {
                "type": "image",
                "data": {
                    "file": f"file:///home/pi/mai-bot/src/static/{photoname}"
                }
            }
        ]))