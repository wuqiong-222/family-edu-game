import streamlit as st
import json
import random
import requests
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="家庭教育模拟实验", layout="wide")

# 内存临时存储数据，网页内查看，无需本地文件
if "all_data" not in st.session_state:
    st.session_state.all_data = []

# 保存数据到会话内存
def save_data(pid, style, pre, game, after):
    new_item = {
        "pid":pid,
        "style":style,
        "pre":pre,
        "game":game,
        "after":after,
        "time":datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    st.session_state.all_data.append(new_item)
    return True

# 管理员后台页面
def admin_view():
    st.title("📊 全部提交数据")
    data_list = st.session_state.all_data
    if not data_list:
        st.info("暂无提交记录")
        return
    df_show = pd.DataFrame([{"编号":d["pid"],"风格":d["style"],"时间":d["time"]} for d in data_list])
    st.dataframe(df_show, use_container_width=True)
    
    idx = st.selectbox("选择记录查看详情", range(len(data_list)))
    detail = data_list[idx]
    st.json(detail)

# 游戏主体
def game_run():
    if "user_state" not in st.session_state:
        st.session_state.user_state = {
            "pid":"","style":"","s_key":"balanced",
            "focus":60,"mood":70,"progress":0,"patience":80,
            "pre":[], "game":[], "after":[],
            "page":0, "parent":"", "child":"", "conflict":""
        }
    s = st.session_state.user_state

    STYLE = {"strict":"专制型","gentle":"放任型","balanced":"权威型"}
    ACT_MAP = {"做作业":"homework","休息":"rest","开小差":"distract","题目不会":"cant_solve"}
    PRE_QS = [
        ("严厉批评不讲解","strict"),("必须服从安排","strict"),("强硬督促行为","strict"),
        ("高标准严厉指责","strict"),("只纠错少鼓励","strict"),
        ("先表扬再引导","balanced"),("共同约定规则","balanced"),("先独立再讲解","balanced"),
        ("先肯定再改进","balanced"),("分析问题给建议","balanced"),
        ("温和简单提醒","gentle"),("无强制进度要求","gentle"),
        ("出错不指责","gentle"),("拖延不强迫","gentle"),("问题仅口头提醒","gentle")
    ]
    AFTER_QS = [
        "可顺利代入孩子视角","场景贴合现实辅导","体会孩子内心感受",
        "教养方式影响情绪学习","重新审视自身教育方式","察觉不当教育负面影响",
        "共情教育具备优势","完成教育换位思考","愿意调整教养沟通模式","模拟具备参考意义"
    ]
    DELTA = {
        "homework":{"f":5,"m":-3,"p":10,"pt":{"s":2,"g":3,"b":2}},
        "rest":{"f":-3,"m":8,"p":0,"pt":{"s":-5,"g":0,"b":-2}},
        "distract":{"f":-8,"m":5,"p":0,"pt":{"s":-10,"g":-5,"b":-8}},
        "cant_solve":{"f":-6,"m":-8,"p":0,"pt":{"s":-6,"g":-2,"b":-4}}
    }
    LOCAL_TALK = {
        "strict":{"homework":[("抓紧认真写","知道了")],"rest":[("没写完不能休息","有点疲惫")],
        "distract":[("专心不要走神","不小心分心了")],"cant_solve":[("基础内容都不会","理解有点吃力")],
        "conflict":[("端正学习态度","我会认真做")},
        "gentle":{"homework":[("放平心态慢慢写","好的谢谢您")],"rest":[("累了就短暂休息","调整下状态")],
        "distract":[("没关系收回注意力","马上专心做题")],"cant_solve":[("先搁置后续研究","好的")],
        "conflict":[("不必紧张焦虑","慢慢调整")},
        "balanced":{"homework":[("踏实完成作业任务","我尽力做好")],"rest":[("短时休息调整状态","稍后继续学习")],
        "distract":[("收拢心思专注题目","立刻集中注意力")],"cant_solve":[("一同梳理解题思路","麻烦帮忙分析")],
        "conflict":[("冷静下来解决问题","平稳心态做题")}
    }

    def get_ai_msg(style,act,is_conf):
        KEY = "9b3679a915614c8c8e342390bbe798fa.9CkuesKtmmNyhTtF"
        URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        try:
            res = requests.post(URL,headers={"Authorization":f"Bearer {KEY}"},
            json={"model":"glm-4-flash","messages":[{"role":"user","content":
            f"{style}家长，孩子正在{act}，{'存在矛盾冲突'if is_conf else '正常相处'}，输出{{parent:'',child:''}}简短对话"}]},timeout=12)
            return json.loads(res.json()["choices"][0]["message"]["content"])
        except:
            return None

    # 页面切换逻辑
    if s["page"] == 0:
        st.title("家庭教育视角互换实验")
        s["pid"] = st.text_input("填写个人实验编号")
        if st.button("进入测评") and s["pid"]:
            s["page"] = 1
            st.rerun()

    elif s["page"] == 1:
        st.subheader("教养风格测评问卷")
        ans_list = []
        for idx,que in enumerate(PRE_QS):
            ans_list.append(st.radio(f"{idx+1}.{que[0]}",[1,2,3,4],horizontal=True,key=f"q{idx}"))
        if st.button("提交测评进入模拟"):
            s["pre"] = ans_list
            score = {"strict":0,"balanced":0,"gentle":0}
            for a,(k) in zip(ans_list,PRE_QS):
                score[k[1]] += a
            s["s_key"] = max(score,key=score.get)
            s["style"] = STYLE[s["s_key"]]
            s["page"] = 2
            st.rerun()

    elif s["page"] == 2:
        st.subheader(f"作业辅导模拟 | {s['style']}")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("专注度",f"{s['focus']}%"),c1.progress(s["focus"]/100)
        c2.metric("情绪值",f"{s['mood']}%"),c2.progress(s["mood"]/100)
        c3.metric("作业进度",f"{s['progress']}%"),c3.progress(s["progress"]/100)
        c4.metric("耐心值",f"{s['patience']}%"),c4.progress(s["patience"]/100)

        if s["parent"]:
            st.chat_message("家长").write(s["parent"])
            st.chat_message("孩子").write(s["child"])
            if s["conflict"]:st.error(f"冲突提示：{s['conflict']}")

        select_act = st.radio("选择行为",list(ACT_MAP.keys()),horizontal=True)
        act_k = ACT_MAP[select_act]
        if st.button("执行互动操作"):
            d = DELTA[act_k]
            s["focus"] = max(0,min(100,s["focus"]+d["f"]))
            s["mood"] = max(0,min(100,s["mood"]+d["m"]))
            s["patience"] = max(0,min(100,s["patience"]+d["pt"][s["s_key"][0]]))
            s["progress"] = max(0,min(100,s["progress"]+d["p"]))
            conflict = []
            if s["focus"]<30:conflict.append("专注不足")
            if s["mood"]<20:conflict.append("情绪不佳")
            if s["patience"]<20:conflict.append("耐心欠缺")
            s["conflict"] = "、".join(conflict) if conflict else ""
            msg = get_ai_msg(s["style"],select_act,bool(conflict))
            if not msg:
                msg = random.choice(LOCAL_TALK[s["s_key"]]["conflict" if conflict else act_k])
                msg = {"parent":msg[0],"child":msg[1]}
            s["parent"],s["child"] = msg["parent"],msg["child"]
            s["game"].append({"行为":select_act,"专注":s["focus"],"情绪":s["mood"],"进度":s["progress"],"对话":msg})
            st.rerun()
        if s["progress"]>=100 and st.button("前往体验问卷"):
            s["page"] = 3
            st.rerun()

    elif s["page"] == 3:
        st.subheader("体验反馈问卷")
        after_ans = []
        for idx,que in enumerate(AFTER_QS):
            after_ans.append(st.radio(f"Q{idx+1}.{que}",[1,2,3,4,5],horizontal=True,key=f"aq{idx}"))
        if st.button("提交完成本次实验"):
            s["after"] = after_ans
            save_data(s["pid"],s["style"],s["pre"],s["game"],s["after"])
            st.success("提交成功，数据已存入后台")
            st.stop()

# 侧边固定后台入口
with st.sidebar:
    if st.button("🔍 管理员查看全部数据"):
        admin_view()
    else:
        game_run()
