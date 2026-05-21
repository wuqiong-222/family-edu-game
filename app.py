import streamlit as st
import json
import random
import requests
from datetime import datetime
import pandas as pd
import sqlite3

# -------------------------- 页面配置 --------------------------
st.set_page_config(page_title="家庭教育视角互换实验", layout="wide", page_icon="👨‍👩‍👧")

# 移动端适配
st.markdown("""
<style>
.block-container {padding:0.5rem; max-width:100%}
.stRadio>div {gap:6px}
.stButton button {border-radius:6px}
hr {margin:6px 0}
</style>
""", unsafe_allow_html=True)

# -------------------------- 本地数据库（存在你电脑） --------------------------
def get_db():
    db = sqlite3.connect("data.db", check_same_thread=False)
    db.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pid TEXT, style TEXT,
        pre TEXT, game TEXT, after TEXT, time TEXT
    )""")
    db.commit()
    return db

db = get_db()

# 保存数据
def save_data(pid, style, pre, game, after):
    try:
        db.execute("INSERT INTO results (pid, style, pre, game, after, time) VALUES (?,?,?,?,?,?)",
                   [pid, style, json.dumps(pre), json.dumps(game), json.dumps(after), datetime.now().strftime("%Y-%m-%d %H:%M")])
        db.commit()
        return True
    except Exception as e:
        st.error(f"数据保存失败: {e}")
        return False

# 管理员查看所有数据（你本地打开就能看）
def admin_page():
    st.title("📊 全部提交数据（本地查看）")
    df = pd.read_sql("SELECT * FROM results", db)
    if df.empty:
        st.info("暂无数据")
        return
    st.dataframe(df[["id","pid","style","time"]], use_container_width=True)
    st.subheader("查看详情")
    sid = st.selectbox("选择ID", df["id"].tolist())
    if sid:
        row = df[df.id==sid].iloc[0]
        st.json({
            "实验编号":row["pid"],
            "教养风格":row["style"],
            "前置问卷":json.loads(row["pre"]),
            "游戏记录":json.loads(row["game"]),
            "后置问卷":json.loads(row["after"])
        })

# -------------------------- AI 配置（智谱） --------------------------
ZHIPU_KEY = "9b3679a915614c8c8e342390bbe798fa.9CkuesKtmmNyhTtF"
ZHIPU_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

def ai_reply(style, act, is_conflict):
    try:
        r = requests.post(ZHIPU_URL, headers={"Authorization":f"Bearer {ZHIPU_KEY}"}, json={
            "model":"glm-4-flash",
            "messages":[{"role":"user","content":f"""
你是{style}家长，孩子在{act}，{"冲突" if is_conflict else "正常"}。
返回JSON：{{"parent":"","child":""}}，简短自然。
"""}]}, timeout=15)
        return r.json()["choices"][0]["message"]["content"]
    except:
        return None

# -------------------------- 游戏逻辑 --------------------------
STYLE = {"strict":"专制型","gentle":"放任型","balanced":"权威型"}
ACT_CN = {"homework":"做作业","rest":"休息","distract":"开小差","cant_solve":"题目不会"}
PRE_QS = [
    ("严厉批评不讲解","strict"),("必须服从","strict"),("强硬督促","strict"),
    ("高标准严指责","strict"),("只纠错不鼓励","strict"),
    ("先表扬再引导","balanced"),("约定规则","balanced"),("先独立再讲解","balanced"),
    ("先肯定再改进","balanced"),("分析原因给建议","balanced"),
    ("简单提醒","gentle"),("无要求","gentle"),("不批评","gentle"),
    ("不强制","gentle"),("口头提醒","gentle")
]
AFTER_QS = [
    "能代入孩子视角","场景贴合现实","体会内心感受","影响情绪学习",
    "重新审视教育","意识到负面影响","理解共情教育","完成换位思考",
    "愿意调整方式","有参考价值"
]

DELTA = {
    "homework":{"f":5,"m":-3,"p":10,"pt":{"s":2,"g":3,"b":2}},
    "rest":{"f":-3,"m":8,"p":0,"pt":{"s":-5,"g":0,"b":-2}},
    "distract":{"f":-8,"m":5,"p":0,"pt":{"s":-10,"g":-5,"b":-8}},
    "cant_solve":{"f":-6,"m":-8,"p":0,"pt":{"s":-6,"g":-2,"b":-4}}
}

LOCAL_DIALOGUE = {
    "strict":{
        "homework":[("抓紧写","知道了")],
        "rest":[("没写完不能休息","我累了")],
        "distract":[("专心点","走神了")],
        "cant_solve":[("怎么不会","没听懂")],
        "conflict":[("认真点","我会的")]
    },
    "gentle":{
        "homework":[("慢慢写","好的")],
        "rest":[("休息一下","谢谢")],
        "distract":[("没关系","我专心了")],
        "cant_solve":[("先跳过","好")],
        "conflict":[("别紧张","好")]
    },
    "balanced":{
        "homework":[("认真写好","我会的")],
        "rest":[("休息一下","好")],
        "distract":[("专心一点","好")],
        "cant_solve":[("我们一起看","好")],
        "conflict":[("慢慢来","好")]
    }
}

# -------------------------- 初始化 --------------------------
if "data" not in st.session_state:
    st.session_state.data = {
        "pid":"","style":"","s_key":"balanced",
        "f":60,"m":70,"p":0,"pt":80,
        "pre":[],"game":[],"after":[],
        "page":0, "parent":"","child":"","conflict":""
    }
d = st.session_state.data

# -------------------------- 页面路由 --------------------------
# 你本地查看数据
if st.sidebar.button("📂 查看所有数据（本地）"):
    admin_page()
    st.stop()

# 0 输入编号
if d["page"]==0:
    st.title("👨‍👩‍👧 家庭教育实验")
    d["pid"] = st.text_input("实验编号")
    if st.button("开始") and d["pid"]:
        d["page"]=1
        st.rerun()

# 1 前置问卷
elif d["page"]==1:
    st.subheader("📝 测评问卷")
    ans = []
    for i,(q,_) in enumerate(PRE_QS):
        ans.append(st.radio(f"{i+1}.{q}",[1,2,3,4],horizontal=True,key=f"pre{i}"))
    if st.button("提交"):
        d["pre"]=ans
        s = {"strict":0,"balanced":0,"gentle":0}
        for a,(_,k) in zip(ans,PRE_QS): s[k]+=a
        d["s_key"] = max(s,key=s.get)
        d["style"] = STYLE[d["s_key"]]
        d["page"]=2
        st.rerun()

# 2 游戏
elif d["page"]==2:
    st.subheader(f"🎮 辅导模拟 | {d['style']}")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("专注",f"{d['f']}%"),c1.progress(d["f"]/100)
    c2.metric("情绪",f"{d['m']}%"),c2.progress(d["m"]/100)
    c3.metric("进度",f"{d['p']}%"),c3.progress(d["p"]/100)
    c4.metric("耐心",f"{d['pt']}%"),c4.progress(d["pt"]/100)

    if d["parent"]:
        st.chat_message("parent").write(d["parent"])
        st.chat_message("child").write(d["child"])
        if d["conflict"]: st.error(f"冲突：{d['conflict']}")

    act = st.radio("行为",["做作业","休息","开小差","题目不会"],horizontal=True)
    act_k = {"做作业":"homework","休息":"rest","开小差":"distract","题目不会":"cant_solve"}[act]
    if st.button("执行"):
        df,dm,dp,dpt = DELTA[act_k].values()
        dpt_val = dpt[d["s_key"][0]]
        d["f"] = max(0,min(100,d["f"]+df))
        d["m"] = max(0,min(100,d["m"]+dm))
        d["pt"] = max(0,min(100,d["pt"]+dpt_val))
        d["p"] = max(0,min(100,d["p"]+dp))
        conflict = []
        if d["f"]<30: conflict.append("专注")
        if d["m"]<20: conflict.append("情绪")
        if d["pt"]<20: conflict.append("耐心")
        d["conflict"] = "、".join(conflict)+"冲突" if conflict else ""
        res = ai_reply(d["style"], act, bool(conflict))
        try:
            res = json.loads(res)
        except:
            res = random.choice(LOCAL_DIALOGUE[d["s_key"]]["conflict" if conflict else act_k])
            res = {"parent":res[0],"child":res[1]}
        d["parent"] = res["parent"]
        d["child"] = res["child"]
        d["game"].append({
            "act":act,"focus":d["f"],"mood":d["m"],"progress":d["p"],
            "patience":d["pt"],"conflict":d["conflict"],
            "parent":d["parent"],"child":d["child"]
        })
        st.rerun()

    if d["p"]>=100:
        st.success("完成！")
        if st.button("下一步"):
            d["page"]=3
            st.rerun()

# 3 后置问卷
elif d["page"]==3:
    st.subheader("📋 体验问卷")
    after = []
    for i,q in enumerate(AFTER_QS):
        after.append(st.radio(f"{i+1}.{q}",[1,2,3,4,5],horizontal=True,key=f"after{i}"))
    if st.button("提交完成"):
        d["after"] = after
        # 保存数据并提示
        if save_data(d["pid"],d["style"],d["pre"],d["game"],d["after"]):
            st.success("提交成功！数据已保存到管理员本地")
            # 强制刷新，让文件生成
            st.rerun()
        else:
            st.error("数据提交失败，请重试")
