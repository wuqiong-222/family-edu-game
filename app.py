import streamlit as st
import json
import random
import requests
from datetime import datetime
import pandas as pd
import sqlite3
import os

# -------------------------- 强制生成数据库文件 --------------------------
DB_PATH = "data.db"
# 强制创建文件（即使是空的）
if not os.path.exists(DB_PATH):
    open(DB_PATH, "a").close()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pid TEXT, style TEXT,
        pre TEXT, game TEXT, after TEXT, time TEXT
    )""")
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def save_data(pid, style, pre, game, after):
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO results (pid, style, pre, game, after, time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            pid, style,
            json.dumps(pre),
            json.dumps(game),
            json.dumps(after),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])
        conn.commit()
        return True
    except Exception as e:
        st.error(f"保存失败: {e}")
        return False
    finally:
        conn.close()

# -------------------------- 管理员后台 --------------------------
def admin_dashboard():
    st.title("📊 管理员数据后台")
    conn = get_db()
    df = pd.read_sql("SELECT * FROM results", conn)
    conn.close()

    if df.empty:
        st.info("暂无提交数据")
        return

    st.subheader("所有提交记录")
    st.dataframe(df[["id", "pid", "style", "time"]], use_container_width=True)

    st.subheader("查看详情")
    selected_id = st.selectbox("选择记录ID", df["id"].tolist())
    if selected_id:
        row = df[df["id"] == selected_id].iloc[0]
        st.json({
            "实验编号": row["pid"],
            "教养风格": row["style"],
            "提交时间": row["time"],
            "前置问卷": json.loads(row["pre"]),
            "游戏记录": json.loads(row["game"]),
            "后置问卷": json.loads(row["after"])
        })

# -------------------------- 游戏主程序 --------------------------
def main_game():
    if "state" not in st.session_state:
        st.session_state.state = {
            "pid": "", "style": "", "s_key": "balanced",
            "focus": 60, "mood": 70, "progress": 0, "patience": 80,
            "pre": [], "game": [], "after": [],
            "page": 0, "parent_msg": "", "child_msg": "", "conflict": ""
        }
    s = st.session_state.state

    STYLE = {"strict": "专制型", "gentle": "放任型", "balanced": "权威型"}
    ACT_CN = {"homework": "做作业", "rest": "休息", "distract": "开小差", "cant_solve": "题目不会"}
    PRE_QS = [
        ("孩子作业出错时，我会直接严厉批评，很少耐心讲解", "strict"),
        ("辅导作业时，我要求孩子必须完全听从我的安排，不允许反驳", "strict"),
        ("孩子作业拖延或开小差时，我会用强硬方式督促其改正", "strict"),
        ("我对孩子作业质量要求极高，达不到标准就严厉指责", "strict"),
        ("我更注重纠错而非鼓励，认为批评才能进步", "strict"),
        ("孩子作业做得好我会及时表扬，做得不好会先指出再引导", "balanced"),
        ("我会和孩子约定规则，违反规则会指出，遵守规则会表扬", "balanced"),
        ("遇到难题我会先鼓励孩子独立思考，再帮他讲解", "balanced"),
        ("我会先肯定孩子的努力，再指出可以改进的地方", "balanced"),
        ("我会帮孩子分析原因，给他建议，而不是只批评", "balanced"),
        ("孩子开小差时我只会简单提醒，不会强制", "gentle"),
        ("我对孩子的作业进度没有严格要求，只陪伴不施压", "gentle"),
        ("孩子不会的题目我不会批评，会耐心讲解", "gentle"),
        ("孩子拖延我也不会强制，只会温和提醒", "gentle"),
        ("孩子习惯不好我只会口头提醒，不会严厉指责", "gentle")
    ]
    AFTER_QS = [
        "本次模拟中，我能顺利代入孩子视角感受状态",
        "游戏互动场景和现实家庭辅导情况贴合",
        "通过体验，我体会到了孩子的内心感受",
        "我明显察觉到教养态度会影响孩子的情绪与学习状态",
        "这次体验帮助我重新审视自身日常教育沟通方式",
        "我意识到不当的教育行为会产生负面的亲子影响",
        "我理解了有边界的共情式教育的优势与合理性",
        "本次体验有效帮助我完成家庭教育换位思考反思",
        "体验后我愿意调整自身的教养沟通方式",
        "沉浸式模拟对亲子共情教育具备参考价值"
    ]
    DELTA = {
        "homework": {"f": 5, "m": -3, "p": 10, "pt": {"s": 2, "g": 3, "b": 2}},
        "rest": {"f": -3, "m": 8, "p": 0, "pt": {"s": -5, "g": 0, "b": -2}},
        "distract": {"f": -8, "m": 5, "p": 0, "pt": {"s": -10, "g": -5, "b": -8}},
        "cant_solve": {"f": -6, "m": -8, "p": 0, "pt": {"s": -6, "g": -2, "b": -4}}
    }
    LOCAL_DIALOGUE = {
        "strict": {
            "homework": [("抓紧写，不许磨蹭！", "知道了...")],
            "rest": [("作业没写完不许休息！", "我真的很累了...")],
            "distract": [("专心点！发什么呆！", "我不小心走神了...")],
            "cant_solve": [("这都不会？上课听了吗？", "我没听懂老师讲的...")],
            "conflict": [("态度端正点！不想学就别学！", "我知道了...")]
        },
        "gentle": {
            "homework": [("慢慢写，别着急，有问题随时说", "谢谢妈妈/爸爸")],
            "rest": [("累了就休息一下吧，别太勉强", "好，我休息一下")],
            "distract": [("没关系，我们把注意力拉回来好不好？", "好的")],
            "cant_solve": [("没关系，我们一起看看这道题", "谢谢")],
            "conflict": [("别紧张，我们慢慢说", "好...")]
        },
        "balanced": {
            "homework": [("认真写，遇到困难可以先标记出来", "好的")],
            "rest": [("累了就休息十分钟，调整一下状态", "好，谢谢")],
            "distract": [("我们先把这题做完，再休息好不好？", "好")],
            "cant_solve": [("我们一起分析一下，看看哪里卡住了", "好的")],
            "conflict": [("别急，我们一起解决问题", "好...")]
        }
    }

    def ai_reply(style, act, is_conflict):
        ZHIPU_KEY = "9b3679a915614c8c8e342390bbe798fa.9CkuesKtmmNyhTtF"
        ZHIPU_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        try:
            resp = requests.post(
                ZHIPU_URL,
                headers={"Authorization": f"Bearer {ZHIPU_KEY}"},
                json={
                    "model": "glm-4-flash",
                    "messages": [{
                        "role": "user",
                        "content": f"""你是{style}的家长，孩子正在{act}，当前{"出现冲突" if is_conflict else "正常沟通"}。
请生成一句家长的话和一句孩子的回应，简短自然，符合真实对话。
只返回JSON格式，不要其他内容：{{"parent":"","child":""}}"""
                    }]
                },
                timeout=15
            )
            if resp.status_code == 200:
                return json.loads(resp.json()["choices"][0]["message"]["content"].strip())
        except:
            return None

    if s["page"] == 0:
        st.title("🏠 家庭教育模拟实验")
        st.info("请输入你的实验编号，开始体验孩子视角的作业辅导场景")
        s["pid"] = st.text_input("请输入你的实验编号（如 P01）")
        if st.button("下一步填写问卷", disabled=not s["pid"]):
            s["page"] = 1
            st.rerun()

    elif s["page"] == 1:
        st.subheader("📝 教养风格测评问卷")
        ans = []
        for i, (q, _) in enumerate(PRE_QS):
            ans.append(st.radio(f"{i+1}. {q}", [1,2,3,4], horizontal=True, key=f"pre_{i}"))
        if st.button("提交并进入模拟", use_container_width=True):
            s["pre"] = ans
            score = {"strict":0, "balanced":0, "gentle":0}
            for a, (_, k) in zip(ans, PRE_QS):
                score[k] += a
            s["s_key"] = max(score, key=score.get)
            s["style"] = STYLE[s["s_key"]]
            s["page"] = 2
            st.rerun()

    elif s["page"] == 2:
        st.subheader(f"🎮 作业辅导模拟 | 当前风格：{s['style']}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("专注度", f"{s['focus']}%")
        col1.progress(s["focus"]/100)
        col2.metric("情绪值", f"{s['mood']}%")
        col2.progress(s["mood"]/100)
        col3.metric("作业进度", f"{s['progress']}%")
        col3.progress(s["progress"]/100)
        col4.metric("耐心值", f"{s['patience']}%")
        col4.progress(s["patience"]/100)

        st.divider()
        st.markdown("### 💬 亲子对话")
        if s["parent_msg"]:
            st.chat_message("家长").write(s["parent_msg"])
            st.chat_message("孩子").write(s["child_msg"])
            if s["conflict"]:
                st.error(f"⚠️ 冲突提示：{s['conflict']}")

        st.divider()
        st.markdown("### 🎮 互动操作")
        act = st.radio("选择孩子行为", ["做作业", "休息", "开小差", "题目不会"], horizontal=True)
        act_key = {"做作业":"homework", "休息":"rest", "开小差":"distract", "题目不会":"cant_solve"}[act]

        if st.button("执行互动", use_container_width=True):
            delta = DELTA[act_key]
            s["focus"] = max(0, min(100, s["focus"] + delta["f"]))
            s["mood"] = max(0, min(100, s["mood"] + delta["m"]))
            s["patience"] = max(0, min(100, s["patience"] + delta["pt"][s["s_key"][0]]))
            s["progress"] = max(0, min(100, s["progress"] + delta["p"]))

            conflict = []
            if s["focus"] < 30: conflict.append("专注度过低")
            if s["mood"] < 20: conflict.append("情绪崩溃")
            if s["patience"] < 20: conflict.append("家长耐心耗尽")
            s["conflict"] = "、".join(conflict) if conflict else ""

            res = ai_reply(s["style"], act, bool(conflict))
            if not res:
                res = random.choice(LOCAL_DIALOGUE[s["s_key"]]["conflict" if conflict else act_key])
                res = {"parent": res[0], "child": res[1]}
            s["parent_msg"] = res["parent"]
            s["child_msg"] = res["child"]

            s["game"].append({
                "action": act,
                "focus": s["focus"],
                "mood": s["mood"],
                "progress": s["progress"],
                "patience": s["patience"],
                "conflict": s["conflict"],
                "parent_msg": s["parent_msg"],
                "child_msg": s["child_msg"],
                "time": datetime.now().strftime("%H:%M:%S")
            })
            st.rerun()

        if s["progress"] >= 100:
            st.success("🎉 作业完成！请填写体验问卷")
            if st.button("进入体验问卷", use_container_width=True):
                s["page"] = 3
                st.rerun()

    elif s["page"] == 3:
        st.subheader("📋 体验反馈问卷")
        after_ans = []
        for i, q in enumerate(AFTER_QS):
            after_ans.append(st.radio(f"Q{i+1}: {q}", [1,2,3,4,5], horizontal=True, key=f"after_{i}"))
        if st.button("提交并结束实验", use_container_width=True):
            s["after"] = after_ans
            if save_data(s["pid"], s["style"], s["pre"], s["game"], s["after"]):
                st.success("✅ 提交成功！感谢参与")
                st.balloons()
                st.info("数据已保存到 data.db，可通过工具查看")
                st.stop()
            else:
                st.error("提交失败，请重试")

def main():
    with st.sidebar:
        if st.button("🔐 管理员后台", use_container_width=True):
            st.session_state["admin_mode"] = True
            st.rerun()

    if st.session_state.get("admin_mode", False):
        admin_dashboard()
    else:
        main_game()

if __name__ == "__main__":
    main()
