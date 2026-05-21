import streamlit as st
import json
import random
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO, StringIO
from PIL import Image

# 配置页面
st.set_page_config(page_title="家庭教育实验", layout="wide")

# ====================== 全局配置 ======================
STYLE_NAMES = {"strict": "专制型", "gentle": "放任型", "balanced": "权威型"}

QUESTIONNAIRE = [
    ("孩子作业出错时，我会直接严厉批评，很少耐心讲解", "strict"),
    ("辅导作业时，我要求孩子必须完全听从我的安排，不允许反驳", "strict"),
    ("孩子作业拖延或开小差时，我会用强硬方式督促其改正", "strict"),
    ("我对孩子作业质量要求极高，达不到标准就严厉指责", "strict"),
    ("我更注重纠错而非鼓励，认为批评才能进步", "strict"),
    ("孩子作业做得好及时表扬，不好先指出再引导", "balanced"),
    ("我会和孩子约定规则，违反指出，遵守表扬", "balanced"),
    ("孩子遇难题先鼓励独立思考，再讲解", "balanced"),
    ("先肯定优点，再指出改进", "balanced"),
    ("失误先分析原因，再给建议", "balanced"),
    ("孩子开小差仅简单提醒，不强制", "gentle"),
    ("仅陪伴，无进度质量要求", "gentle"),
    ("孩子不会不批评不强制，自愿求助", "gentle"),
    ("长期拖延也不强制，仅提醒", "gentle"),
    ("习惯不合理仅口头提醒", "gentle"),
]

AFTER_SURVEY_QUESTIONS = [
    "我能顺利代入孩子视角",
    "游戏场景与现实贴合",
    "我能感受到孩子真实感受",
    "教养方式直接影响孩子状态",
    "体验让我重新审视教育方式",
    "我意识到强硬教育的负面影响",
    "我理解权威式教育的优势",
    "本次体验帮助我换位思考",
    "我愿意调整沟通方式",
    "对共情教育有实际价值",
]

DELTA = {
    "homework": {"focus": 5, "mood": -3, "progress": 10, "patience": {"strict": 2, "gentle": 3, "balanced": 2}},
    "rest": {"focus": -3, "mood": 8, "progress": 0, "patience": {"strict": -5, "gentle": 0, "balanced": -2}},
    "distract": {"focus": -8, "mood": 5, "progress": 0, "patience": {"strict": -10, "gentle": -5, "balanced": -8}},
    "cant_solve": {"focus": -6, "mood": -8, "progress": 0, "patience": {"strict": -6, "gentle": -2, "balanced": -4}},
}

# ====================== 数据类 ======================
class GameData:
    def __init__(self):
        self.participant_id = ""
        self.parent_style = "strict"
        self.real_style = ""
        self.focus = 60
        self.mood = 70
        self.progress = 0
        self.patience = 80
        self.logs = []
        self.qs = []
        self.after = []

    def reset(self):
        self.focus = 60
        self.mood = 70
        self.progress = 0
        self.patience = 80
        self.logs = []

    def act(self, action):
        d = DELTA[action]
        self.focus = max(0, min(100, self.focus + d["focus"]))
        self.mood = max(0, min(100, self.mood + d["mood"]))
        self.patience = max(0, min(100, self.patience + d["patience"][self.parent_style]))
        self.progress = max(0, min(100, self.progress + d["progress"]))
        self.logs.append({
            "t": datetime.now().strftime("%H:%M:%S"),
            "act": action,
            "focus": self.focus,
            "mood": self.mood,
            "progress": self.progress,
            "patience": self.patience
        })

# 初始化
if "data" not in st.session_state:
    st.session_state.data = GameData()
if "page" not in st.session_state:
    st.session_state.page = 0

data = st.session_state.data

# ====================== 页面1：输入ID ======================
if st.session_state.page == 0:
    st.title("📝 实验开始")
    pid = st.text_input("实验编号")
    if st.button("下一步") and pid:
        data.participant_id = pid
        st.session_state.page = 1
        st.rerun()

# ====================== 页面2：问卷 ======================
elif st.session_state.page == 1:
    st.title("家长教养风格问卷")
    ans = []
    for q, _ in QUESTIONNAIRE:
        v = st.radio(q, [1,2,3,4], horizontal=True, key=q)
        ans.append(v)
    if st.button("提交"):
        s = {"strict":0,"balanced":0,"gentle":0}
        for a, (_, d) in zip(ans, QUESTIONNAIRE):
            s[d] += a
        best = max(s, key=s.get)
        data.parent_style = best
        data.real_style = STYLE_NAMES[best]
        data.qs = ans
        data.reset()
        st.session_state.page = 2
        st.rerun()

# ====================== 页面3：游戏 ======================
elif st.session_state.page == 2:
    st.title(f"🎮 辅导模拟（{data.real_style}）")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("专注", data.focus); c1.progress(data.focus/100)
    c2.metric("情绪", data.mood); c2.progress(data.mood/100)
    c3.metric("进度", data.progress); c3.progress(data.progress/100)
    c4.metric("耐心", data.patience); c4.progress(data.patience/100)

    act = st.radio("孩子行为", ["做作业","休息","开小差","题目不会"], horizontal=1)
    m = {"做作业":"homework","休息":"rest","开小差":"distract","题目不会":"cant_solve"}
    if st.button("执行"):
        data.act(m[act])
        if data.progress >= 100:
            st.success("✅ 作业完成！生成反思报告")
            st.session_state.page = 3
            st.rerun()

# ====================== 页面4：反思报告（你要的核心！）======================
elif st.session_state.page == 3:
    st.title("📊 个人反思报告")

    # 图表
    df = pd.DataFrame(data.logs)
    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(df.index, df.focus, label="专注", color="#4B89DC")
    ax.plot(df.index, df.mood, label="情绪", color="#F66D9F")
    ax.plot(df.index, df.progress, label="进度", color="#38C172")
    ax.plot(df.index, df.patience, label="耐心", color="#777")
    ax.legend()
    ax.set_ylim(0,100)
    st.pyplot(fig)

    # 统计
    st.subheader("📌 模拟概况")
    acts = [x["act"] for x in data.logs]
    c = dict(pd.Series(acts).value_counts())
    st.write(f"总操作：{len(acts)} 次")
    st.write(f"行为统计：{c}")

    # 反思文字
    st.subheader("💡 反思与建议")
    st.markdown(f"""
    **你的类型：{data.real_style}**
    - 你在模拟中体验了孩子的真实学习状态
    - 专注/情绪/耐心的波动直接反映教育方式影响
    - 强制型易导致情绪下降、耐心不足
    - 放任型易导致进度缓慢、规则意识弱
    - 权威型（温和+边界）最利于长期学习习惯
    """)

    st.success("✅ 报告生成完成！")

    # 下载
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    st.download_button("💾 下载反思报告图片", buf, "反思报告.png", "image/png")

    # 数据下载
    out = {
        "id": data.participant_id,
        "style": data.real_style,
        "logs": data.logs,
        "qs": data.qs
    }
    js = json.dumps(out, ensure_ascii=0, indent=2)
    st.download_button("📥 下载完整实验数据", js, f"数据_{data.participant_id}.json")

    if st.button("完成体验"):
        st.session_state.page = 4
        st.rerun()

elif st.session_state.page == 4:
    st.title("✅ 实验结束")
    st.success("所有数据已下载保存，感谢参与！")
