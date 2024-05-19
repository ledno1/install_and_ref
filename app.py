"""
访问 localhost:5000/hello时，会用mqtt客户端发布主题消息
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from queue import Queue

import paho.mqtt.client as mqtt
import requests
from flask import Flask, request

app = Flask(__name__)
print('[app] start work', file=sys.stdout)

proxy_status = True
host = "192.168.3.12"

proc_g = None
thread = None
# 定义二进制可执行文件的完整路径
binary_path = "/root/ajiasu"
sheng = sys.argv[1]
host = sys.argv[2]
topicsheng = sys.argv[3]
maxQueueSize = sys.argv[4]
print("启动参数", sys.argv)
proxies = {
    "http": "127.0.0.1:1080",
    "https": "127.0.0.1:1080",  # 如果代理服务器同时支持HTTPS，请确保这里也配置
}


# 启用代理进程
def start_proxy(args):
    if len(args) == 0:
        args = ["connect", "vvn-4749-6263"]
    print("启动代理进程", args)
    global proc_g
    # 使用 subprocess.run() 启动子进程
    try:
        proc_g = subprocess.Popen([binary_path, *args])
    except Exception as e:
        print("启动代理进程出错", e)
        return False
    return True


def start_proxy_by_pm2(t):
    args = ["pm2", "start", "/root/ajiasu", "--", "connect"]
    args.append(t)
    result = subprocess.run(args)
    if result.returncode == 0:
        return True
    else:
        return False


def stop_proxy_by_pm2():
    args = ["pm2", "delete", "ajiasu"]
    result = subprocess.run(args)
    if result.returncode == 0:
        return True
    else:
        return False


def curl_test():
    args = ["curl", "-x", "127.0.0.1:1080", "http://myexternalip.com/raw"]
    # 执行shell命令 并打印输出
    result = subprocess.run(args, stdout=subprocess.PIPE)
    if result.returncode == 0:
        return True
    else:
        return False


area_data = {
    '北京': ['北京市', '朝阳区', '海淀区', '通州区', '房山区', '丰台区', '昌平区', '大兴区', '顺义区', '西城区',
             '延庆县', '石景山区', '宣武区', '怀柔区', '崇文区', '密云县',
             '东城区', '门头沟区', '平谷区'],
    '广东': ['广东省', '东莞市', '广州市', '中山市', '深圳市', '惠州市', '江门市', '珠海市', '汕头市', '佛山市',
             '湛江市', '河源市', '肇庆市', '潮州市', '清远市', '韶关市', '揭阳市', '阳江市', '云浮市', '茂名市',
             '梅州市', '汕尾市'],
    '山东': ['山东省', '济南市', '青岛市', '临沂市', '济宁市', '菏泽市', '烟台市', '泰安市', '淄博市', '潍坊市',
             '日照市', '威海市', '滨州市', '东营市', '聊城市', '德州市', '莱芜市', '枣庄市'],
    '江苏': ['江苏省', '苏州市', '徐州市', '盐城市', '无锡市', '南京市', '南通市', '连云港市', '常州市', '扬州市',
             '镇江市', '淮安市', '泰州市', '宿迁市'],
    '河南': ['河南省', '郑州市', '南阳市', '新乡市', '安阳市', '洛阳市', '信阳市', '平顶山市', '周口市', '商丘市',
             '开封市', '焦作市', '驻马店市', '濮阳市', '三门峡市', '漯河市', '许昌市', '鹤壁市', '济源市'],
    '上海': ['上海市', '松江区', '宝山区', '金山区', '嘉定区', '南汇区', '青浦区', '浦东新区', '奉贤区', '闵行区',
             '徐汇区', '静安区', '黄浦区', '普陀区', '杨浦区', '虹口区', '闸北区', '长宁区', '崇明县', '卢湾区'],
    '河北': ['河北省', '石家庄市', '唐山市', '保定市', '邯郸市', '邢台市', '河北区', '沧州市', '秦皇岛市', '张家口市',
             '衡水市', '廊坊市', '承德市'],
    '浙江': ['浙江省', '温州市', '宁波市', '杭州市', '台州市', '嘉兴市', '金华市', '湖州市', '绍兴市', '舟山市',
             '丽水市', '衢州市'],
    '陕西': ['陕西省', '西安市', '咸阳市', '宝鸡市', '汉中市', '渭南市', '安康市', '榆林市', '商洛市', '延安市',
             '铜川市'],
    '湖南': ['湖南省', '长沙市', '邵阳市', '常德市', '衡阳市', '株洲市', '湘潭市', '永州市', '岳阳市', '怀化市',
             '郴州市', '娄底市', '益阳市', '张家界市', '湘西州'],
    '重庆': ['重庆市', '江北区', '渝北区', '沙坪坝区', '九龙坡区', '万州区', '永川市', '南岸区', '酉阳县', '北碚区',
             '涪陵区', '秀山县', '巴南区', '渝中区', '石柱县', '忠县', '合川市', '大渡口区', '开县', '长寿区', '荣昌县',
             '云阳县', '梁平县', '潼南县', '江津市', '彭水县', '璧山县', '綦江县',
             '大足县', '黔江区', '巫溪县', '巫山县', '垫江县', '丰都县', '武隆县', '万盛区', '铜梁县', '南川市',
             '奉节县', '双桥区', '城口县'],
    '福建': ['福建省', '漳州市', '泉州市', '厦门市', '福州市', '莆田市', '宁德市', '三明市', '南平市', '龙岩市'],
    '天津': ['天津市', '和平区', '北辰区', '河北区', '河西区', '西青区', '津南区', '东丽区', '武清区', '宝坻区',
             '红桥区', '大港区', '汉沽区', '静海县', '宁河县', '塘沽区', '蓟县', '南开区', '河东区'],
    '云南': ['云南省', '昆明市', '红河州', '大理州', '文山州', '德宏州', '曲靖市', '昭通市', '楚雄州', '保山市',
             '玉溪市', '丽江地区', '临沧地区', '思茅地区', '西双版纳州', '怒江州', '迪庆州'],
    '四川': ['四川省', '成都市', '绵阳市', '广元市', '达州市', '南充市', '德阳市', '广安市', '阿坝州', '巴中市',
             '遂宁市', '内江市', '凉山州', '攀枝花市', '乐山市', '自贡市', '泸州市', '雅安市', '宜宾市', '资阳市',
             '眉山市', '甘孜州'],
    '广西': ['广西壮族自治区', '贵港市', '玉林市', '北海市', '南宁市', '柳州市', '桂林市', '梧州市', '钦州市', '来宾市',
             '河池市', '百色市', '贺州市', '崇左市', '防城港市'],
    '安徽': ['安徽省', '芜湖市', '合肥市', '六安市', '宿州市', '阜阳市', '安庆市', '马鞍山市', '蚌埠市', '淮北市',
             '淮南市', '宣城市', '黄山市', '铜陵市', '亳州市', '池州市', '巢湖市', '滁州市'],
    '海南': ['海南省', '三亚市', '海口市', '琼海市', '文昌市', '东方市', '昌江县', '陵水县', '乐东县', '五指山市',
             '保亭县', '澄迈县', '万宁市', '儋州市', '临高县', '白沙县', '定安县', '琼中县', '屯昌县'],
    '江西': ['江西省', '南昌市', '赣州市', '上饶市', '吉安市', '九江市', '新余市', '抚州市', '宜春市', '景德镇市',
             '萍乡市', '鹰潭市'],
    '湖北': ['湖北省', '武汉市', '宜昌市', '襄樊市', '荆州市', '恩施州', '孝感市', '黄冈市', '十堰市', '咸宁市',
             '黄石市', '仙桃市', '随州市', '天门市', '荆门市', '潜江市', '鄂州市', '神农架林区'],
    '山西': ['山西省', '太原市', '大同市', '运城市', '长治市', '晋城市', '忻州市', '临汾市', '吕梁市', '晋中市',
             '阳泉市', '朔州市'],
    '辽宁': ['辽宁省', '大连市', '沈阳市', '丹东市', '辽阳市', '葫芦岛市', '锦州市', '朝阳市', '营口市', '鞍山市',
             '抚顺市', '阜新市', '本溪市', '盘锦市', '铁岭市'],
    '台湾': ['台湾省', '台北市', '高雄市', '台中市', '新竹市', '基隆市', '台南市', '嘉义市'],
    '黑龙江': ['黑龙江', '齐齐哈尔市', '哈尔滨市', '大庆市', '佳木斯市', '双鸭山市', '牡丹江市', '鸡西市', '黑河市',
               '绥化市', '鹤岗市', '伊春市', '大兴安岭地区', '七台河市'],
    '内蒙古': ['内蒙古自治区', '赤峰市', '包头市', '通辽市', '呼和浩特市', '乌海市', '鄂尔多斯市', '呼伦贝尔市',
               '兴安盟', '巴彦淖尔盟', '乌兰察布盟', '锡林郭勒盟', '阿拉善盟'],
    '香港': ["香港", "香港特别行政区"],
    '澳门': ['澳门', '澳门特别行政区'],
    '贵州': ['贵州省', '贵阳市', '黔东南州', '黔南州', '遵义市', '黔西南州', '毕节地区', '铜仁地区', '安顺市',
             '六盘水市'],
    '甘肃': ['甘肃省', '兰州市', '天水市', '庆阳市', '武威市', '酒泉市', '张掖市', '陇南地区', '白银市', '定西地区',
             '平凉市', '嘉峪关市', '临夏回族自治州', '金昌市', '甘南州'],
    '青海': ['青海省', '西宁市', '海西州', '海东地区', '海北州', '果洛州', '玉树州', '黄南藏族自治州'],
    '新疆': ['新疆', '新疆维吾尔自治区', '乌鲁木齐市', '伊犁州', '昌吉州', '石河子市', '哈密地区', '阿克苏地区',
             '巴音郭楞州', '喀什地区', '塔城地区', '克拉玛依市', '和田地区', '阿勒泰州', '吐鲁番地区', '阿拉尔市',
             '博尔塔拉州', '五家渠市',
             '克孜勒苏州', '图木舒克市'],
    '西藏': ['西藏区', '拉萨市', '山南地区', '林芝地区', '日喀则地区', '阿里地区', '昌都地区', '那曲地区'],
    '吉林': ['吉林省', '吉林市', '长春市', '白山市', '白城市', '延边州', '松原市', '辽源市', '通化市', '四平市'],
    '宁夏': ['宁夏回族自治区', '银川市', '吴忠市', '中卫市', '石嘴山市', '固原市']
}

sheng_list = []


def get_list():
    sheng_list.clear()
    # 根据启动的参数获取对应的省份的代理列表 执行命令获取代理列表
    list = subprocess.run([binary_path, "list"], stdout=subprocess.PIPE)
    # 根据获取列表中
    # print("获取列表", list)
    with open("list.txt", "w") as f:
        data = list.stdout.decode("utf-8")
        f.write(data)
    data_array = data.split("\n")
    for item in data_array:
        if item.startswith("vvn-"):
            # 开始判断
            # 正则 获取item item字符串类似 vvn-2076-264 ok         镇江 #1
            # ok xx # xx的 匹配内容 并打印出来
            t = item.split("ok")[1].split("#")[0].strip()
            # print(t)
            for k, v in area_data.items():
                for i in v:
                    if t in i:
                        if k == sheng:
                            sheng_list.append(item.split("ok")[0])


def start_and_test() -> bool:
    if len(sheng_list) == 0:
        get_list()
    if len(sheng_list) == 0:
        return False
    try:
        for i in sheng_list:
            time.sleep(3)
            if i.find("vvn-4316-4029") != -1:
                continue
            start_proxy_by_pm2(i)
            # 定义代理服务器信息
            proxies = {
                "http": "http://127.0.0.1:1080",
                "https": "http://127.0.0.1:1080",  # 如果代理服务器同时支持HTTPS，请确保这里也配置
            }
            try:
                # res = requests.get("http://myexternalip.com/raw", proxies=proxies, timeout=30)
                # if res.status_code == 200:
                #     return True
                # else:
                #     print("请求失败，状态码:", res.status_code)
                # if curl_test():
                return True
            except Exception as e:
                print(i, "start_and_test", e)
            time.sleep(3)
            stop_proxy_by_pm2()
    except Exception as e:
        print(e)
        return False
    return False


def register_self():
    try:
        # sheng + topicsheng + maxQueueSize  的字符串 + refresh 的MD5
        sign = hashlib.md5((sheng + topicsheng + maxQueueSize + "refresh").encode()).hexdigest()
        print(sign)
        requests.get("http://" + host + ":8000/api/refresh/register_refresh", timeout=10, data={
            "sheng": sheng,
            "topicsheng": topicsheng,
            "maxQueueSize": maxQueueSize,
            "sign": sign.upper()
        })
    except Exception as e:
        return str(e)


get_list()
stop_proxy_by_pm2()
proxy_status = start_and_test()
# 注册自身
register_self()


class CodeData:
    id: str
    url: str
    codeType: str

    def __init__(self):
        pass


def connect_mqtt() -> mqtt:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            subscribe(client, topicsheng)
            print("Connected to MQTT Broker!", file=sys.stdout)
        else:
            print("Failed to connect, return code %d\n", rc, file=sys.stdout)

    # 重连时
    client = mqtt.Client()
    client.username_pw_set("admin", "public")
    client.on_connect = on_connect
    client.connect(host, 1883, 60)
    client.max_queued_messages_set(int(maxQueueSize))
    return client


def subscribe(client: mqtt, topic):
    def on_message(client, userdata, msg):
        print(f"[mqtt] Received `{msg.payload.decode()}` from `{msg.topic}` topic", file=sys.stdout)
        print(type(msg.payload.decode()))
        d = json.loads(msg.payload.decode())
        data = CodeData()
        data.id = d['id']
        data.url = d['url']
        data.codeType = d['codeType']
        refresh_task(data)

    client.on_message = on_message
    client.subscribe("sheng/" + topic)
    print("[mqtt] subscribe ", "sheng/" + topic)


client = connect_mqtt()

client.loop_start()


@app.route("/hello")
def alarm():
    # client.publish("hello", "important msg")
    # print("[mqtt] send msg successfully", file=sys.stdout)
    return "Mqtt message published"


# 接口 重启爱加速
@app.route("/restart")
def restart():
    try:
        stop_proxy_by_pm2()
        start_and_test()
        return "ok"
    except Exception as e:
        print(e)
        return str(e)


# 重启自身
@app.route("/restart_self")
def restart_self():
    try:
        # 获取 query 参数 maxQueueSize
        m = request.args.get("max_queue_size")
        s = request.args.get("sheng")
        topics = request.args.get("topicsheng")
        print(m, s, topics)
        # pm2 restart ./app.py -- 重庆 192.168.3.12 chongqing 1
        # pm2 restart ./app.py -- 重庆 192.168.3.12 chongqing 1 && pm2 logs
        args = ["pm2", "restart", os.getcwd() + "/app.py", "--", s, host, topics, m]
        subprocess.run(args)
    except Exception as e:
        print("重启服务器出错", e)


# 接口 测试当前代理状态
@app.route("/test")
def test():
    try:
        res = requests.get("http://myexternalip.com/raw", proxies=proxies, timeout=10, data={})
        # print(res.text)
        if res.status_code == 200:
            return res.text
        else:
            return "no"
    except Exception as e:
        print(e)
        return str(e)


def refresh_task(data: CodeData):
    headers = {
        "Host": "wx.tenpay.com",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "iframe",
        "Referer": "https://pay.qq.com/",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "",
        "Connection": "Keep-Alive",
    }

    try:
        # 先请求服务器获取现在ip proxies=proxies,
        if host.startswith("192"):
            res_test = requests.get(f"http://{host}:8000/api/refresh/refresh_test", timeout=10, data={"sheng":sheng})
        else:
            res_test = requests.get(f"http://{host}:8000/api/refresh/refresh_test", proxies=proxies, timeout=10,
                                    data={"sheng":sheng})

        if res_test.status_code == 200:
            print(res_test.text)
            # 执行判断
            res_data = json.loads(res_test.text)
            if "code" in res_data and res_data["code"] == 0:
                resp_data = res_data["data"]
                if resp_data["msg"] == "ok":
                    print("执行刷新请求", data.url)
                    # url = base64.decodebytes(data.url.encode('utf-8')).decode()
                    res = requests.get(data.url, proxies=proxies, headers=headers, timeout=30, data={})
                    # print(res.text)
                    if res.status_code == 200:
                        if res.text.find("支付请求已失效，请重新发起支付") != -1:
                            print("支付请求已失效")
                            client.publish("refresh_result",
                                           json.dumps({"id": data.id, "out_time": True, "url": "", "error": "","ip":resp_data["ip"]}))
                        else:
                            # 进行正则匹配 `url="([^"]*)"`
                            url = re.findall("url=\"(.*?)\"", res.text)
                            base64_url = base64.b64encode(url[0].encode('utf-8')).decode()
                            print("base64_url:", base64_url)
                            client.publish("refresh_result",
                                           json.dumps(
                                               {"id": data.id, "out_time": False, "url": base64_url, "error": "","ip":resp_data["ip"]}))
                    else:
                        client.publish("refresh_result",
                                       json.dumps({"id": data.id, "out_time": False, "url": "", "error": res.text,"ip":resp_data["ip"]}))
                elif resp_data["msg"] == "no":
                    # 重新推送会系统队列 还是 重启代理
                    client.publish("refresh_result",
                                   json.dumps({"id": data.id, "out_time": False, "url": "",
                                               "error": "代理失效:" + res_test.text,"ip":resp_data["ip"]}))
                    stop_proxy_by_pm2()
                    start_and_test()
                else:
                    # 重新推送会系统队列 还是 重启代理
                    client.publish("refresh_result",
                                   json.dumps({"id": data.id, "out_time": False, "url": "",
                                               "error": "代理失效:" + res_test.text,"ip":resp_data["ip"]}))
            else:
                # 重新推送会系统队列 还是 重启代理
                client.publish("refresh_result",
                               json.dumps({"id": data.id, "out_time": False, "url": "", "error": "测试代理出错:"+res_test.text,"ip":""}))
        else:
            print(res_test.status_code,res_test.text)
            client.publish("refresh_result",
                           json.dumps({"id": data.id, "out_time": False, "url": "", "error":f"{res_test.status_code}:{res_test.text}","ip":""}))

    except Exception as e:
        print("refresh_task", e)
        client.publish("refresh_result",
                       json.dumps({"id": data.id, "out_time": False, "url": "", "error": str(e),"ip":""}))


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
