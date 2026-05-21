import streamlit as st
import json
import random
import pandas as pd
from datetime import datetime
from io import BytesIO

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
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "action": action,
            "focus": self.focus,
            "mood": self.mood,
            "progress": self.progress,
            "patience": self.patience
        })

# 初始化会话状态
if "data" not in st.session_state:
    st.session_state.data = GameData()
if "page" not in st.session_state:
    st.session_state.page = 0

data = st.session_state.data

# ====================== 页面1：输入ID ======================
if st.session_state.page == 0:
    st.title("📝 家庭教育模拟实验")
    pid = st.text_input("请输入你的实验编号（如 P01）")
    if st.button("下一步，填写问卷", disabled=not pid):
        data.participant_id = pid
        st.session_state.page = 1
        st.rerun()

# ====================== 页面2：前置问卷 ======================
elif st.session_state.page == 1:
    st.title("📋 家长教养风格问卷")
    st.info("请根据你的真实情况选择，我们将据此判定你的教养风格")
    answers = []
    for q, _ in QUESTIONNAIRE:
        ans = st.radio(f"Q: {q}", [1,2,3,4], horizontal=True, format_func=lambda x: ["完全不符合", "不太符合", "比较符合", "完全符合"][x-1])
        answers.append(ans)
    if st.button("提交问卷，开始模拟", use_container_width=True):
        scores = {"strict": 0, "balanced": 0, "gentle": 0}
        for ans, (_, dim) in zip(answers, QUESTIONNAIRE):
            scores[dim] += ans
        # 判定风格
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if sorted_scores[1][1] >= sorted_scores[0][1] - 1:
            best_style = "balanced"
        else:
            best_style = sorted_scores[0][0]
        data.parent_style = best_style
        data.real_style = STYLE_NAMES[best_style]
        data.qs = answers
        data.reset()
        st.success(f"✅ 你的教养风格判定为：{data.real_style}，将以此风格进行模拟")
        st.session_state.page = 2
        st.rerun()

# ====================== 页面3：游戏交互 ======================
elif st.session_state.page == 2:
    st.title(f"🎮 作业辅导模拟场景（{data.real_style}）")

    # 状态卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🧠 专注度", f"{data.focus}%")
        st.progress(data.focus / 100)
    with col2:
        st.metric("😊 情绪值", f"{data.mood}%")
        st.progress(data.mood / 100)
    with col3:
        st.metric("📚 作业进度", f"{data.progress}%")
        st.progress(data.progress / 100)
    with col4:
        st.metric("⏳ 家长耐心", f"{data.patience}%")
        st.progress(data.patience / 100)

    st.divider()
    action = st.radio("请选择孩子的行为：", ["做作业", "休息", "开小差", "题目不会"], horizontal=True)
    action_map = {"做作业": "homework", "休息": "rest", "开小差": "distract", "题目不会": "cant_solve"}
    if st.button("执行操作", use_container_width=True, type="primary"):
        data.act(action_map[action])
        if data.progress >= 100:
            st.balloons()
            st.success("🎉 作业完成！请查看你的反思报告")
            st.session_state.page = 3
            st.rerun()

# ====================== 页面4：反思报告（核心！）======================
elif st.session_state.page == 3:
    st.title("📊 个人反思报告")
    st.info(f"被试编号：{data.participant_id} | 模拟风格：{data.real_style}")

    # 1. 状态变化趋势（用Streamlit原生图表，无需matplotlib）
    st.subheader("📈 状态变化趋势")
    if data.logs:
        df = pd.DataFrame(data.logs)
        df["step"] = range(len(df))
        st.line_chart(df, x="step", y=["focus", "mood", "progress", "patience"], color=["#4B89DC", "#F66D9F", "#38C172", "#777"])

    # 2. 行为统计
    st.subheader("📌 模拟行为统计")
    if data.logs:
        action_counts = pd.Series([x["action"] for x in data.logs]).value_counts()
        st.bar_chart(action_counts)

    # 3. 反思总结
    st.subheader("💡 反思与建议")
    conflict_list = []
    if data.focus < 30: conflict_list.append("专注冲突")
    if data.mood < 20: conflict_list.append("情绪冲突")
    if data.patience < 20: conflict_list.append("亲子冲突")

    st.markdown(f"""
    **你的教养风格：{data.real_style}**
    - 本次模拟中，你从孩子视角体验了作业辅导的全过程，共完成 {len(data.logs)} 次操作
    - 专注度最低：{min([60] + [x["focus"] for x in data.logs])}%，情绪值最低：{min([70] + [x["mood"] for x in data.logs])}%
    - 触发冲突：{', '.join(conflict_list) if conflict_list else "无冲突"}

    **核心反思点：**
    1.  专制型风格：易导致孩子情绪下降、耐心不足，长期可能引发抵触心理
    2.  放任型风格：易导致作业进度缓慢、规则意识薄弱，缺乏学习动力
    3.  权威型风格：温和+边界的引导方式，更利于孩子建立稳定的学习习惯与情绪管理

    **行动建议：**
    - 下次辅导前，先和孩子约定明确的规则与目标
    - 当孩子出现抵触情绪时，先暂停批评，共情其状态再引导
    - 用“描述事实+表达感受+提出需求”的沟通方式，代替命令式语言
    """)

    # 4. 数据下载
    st.divider()
    st.subheader("💾 数据导出")
    full_data = {
        "participant_id": data.participant_id,
        "real_style": data.real_style,
        "simulate_style": data.parent_style,
        "pre_questionnaire": data.qs,
        "logs": data.logs
    }
    json_str = json.dumps(full_data, ensure_ascii=False, indent=2)
    st.download_button("下载完整实验数据", json_str, f"实验数据_{data.participant_id}.json", mime="application/json", use_container_width=True)

    if st.button("进入后置体验问卷", use_container_width=True):
        st.session_state.page = 4
        st.rerun()

# ====================== 页面5：后置问卷 ======================
elif st.session_state.page == 4:
    st.title("📋 后置体验问卷")
    st.info("请结合本次模拟体验，回答以下问题，帮助我们改进实验")
    answers = []
    for q in AFTER_SURVEY_QUESTIONS:
        ans = st.radio(f"Q: {q}", [1,2,3,4,5], horizontal=True, format_func=lambda x: ["非常不同意", "不同意", "一般", "同意", "非常同意"][x-1])
        answers.append(ans)
    if st.button("提交问卷，结束实验", use_container_width=True, type="primary"):
        data.after = answers
        st.success("✅ 问卷提交成功，感谢你的参与！")
        st.balloons()
        st.session_state.page = 5
        st.rerun()

# ====================== 页面6：结束页面 ======================
elif st.session_state.page == 5:
    st.title("🎊 实验结束，感谢你的参与！")
    st.info("你的数据已安全保存，本次体验将帮助我们更好地理解家庭教育中的沟通模式")
    st.markdown("你可以下载之前生成的反思报告和数据文件，用于后续分析。")
