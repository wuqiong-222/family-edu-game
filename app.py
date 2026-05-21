import streamlit as st
import json
import random
import time
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="家庭教育实验", layout="wide")

# ==================== 配置 ====================
STYLE_NAMES = {"strict": "专制型", "gentle": "放任型", "balanced": "权威型"}
ACTION_CN = {"homework": "做作业", "rest": "休息", "distract": "开小差", "cant_solve": "题目不会"}

QUESTIONNAIRE = [
    ("孩子作业出错时，我会直接严厉批评，很少耐心讲解", "strict"),
    ("辅导作业时，我要求孩子必须完全听从我的安排，不允许反驳", "strict"),
    ("孩子作业拖延或开小差时，我会用强硬方式督促其改正", "strict"),
    ("我对作业质量要求极高，达不到标准就严厉指责", "strict"),
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
    "我能顺利代入孩子视角感受状态",
    "游戏场景和现实家庭辅导贴合",
    "体会到孩子内心真实感受",
    "教养态度直接影响孩子情绪",
    "帮助我重新审视教育方式",
    "意识到不当教育的负面影响",
    "理解共情式教育的合理性",
    "有效完成换位思考反思",
    "愿意调整沟通方式",
    "对亲子教育具备参考价值"
]

DIALOGUE_PAIRS = {
    "strict": {
        "homework": [("抓紧认真写，不许磨蹭", "知道啦，我尽量做好"), ("字迹工整点，马虎就要重写", "我慢慢调整书写")],
        "rest": [("作业没完成不能随便休息", "我已经写很久有点累了"), ("写完任务再谈休息", "好吧那我再坚持一会")],
        "distract": [("专心做题，不要分心贪玩", "一不小心走神了"), ("立刻收回心思专注学习", "我马上集中注意力")],
        "cant_solve": [("基础题都不会，上课没用心", "知识点有点没弄懂"), ("静下心仔细梳理思路", "我再重新审题试试")],
        "conflict": [("态度端正一点，认真对待学习", "我会调整状态好好完成")]
    },
    "gentle": {
        "homework": [("慢慢写就行，不用太过紧张", "好的，我稳步完成"), ("尽力就好，不用强求高标准", "那我按自己节奏写")],
        "rest": [("累了就歇一会，不用勉强自己", "放松下再继续做题"), ("想休息多久都可以自己安排", "短暂休息就回来学习")],
        "distract": [("分心也没关系，之后补上就好", "接下来我专心做题"), ("偶尔放松无妨，后续抓紧进度", "我把控好学习节奏")],
        "cant_solve": [("不会就先搁置，之后再处理", "先跳过做其他题目"), ("不用焦虑，慢慢来思考就行", "我多琢磨一下题目")],
        "conflict": [("不用有压力，放平心态就好", "我舒缓情绪继续学习")]
    },
    "balanced": {
        "homework": [("合理把控速度，保证书写质量", "我兼顾速度和工整度"), ("认真完成每一题，养成好习惯", "用心做好当下习题")],
        "rest": [("完成阶段性任务，可以短时放松", "休整过后继续努力"), ("约定休息时长，到点回归学习", "记住时间准时回来")],
        "distract": [("察觉分心及时拉回注意力哦", "意识到了立刻专注"), ("劳逸结合，尽量减少走神情况", "后续专心投入学习")],
        "cant_solve": [("遇到难题正常，我们一起分析", "麻烦帮我梳理下思路"), ("先自主思考，不懂再来询问", "我先尝试独立解题")],
        "conflict": [("出现情绪波动，调整后继续推进", "平复心情接着完成任务")]
    }
}

DELTA = {
    "homework": {"focus": 5, "mood": -3, "progress": 10, "patience": {"strict": 2, "gentle": 3, "balanced": 2}},
    "rest": {"focus": -3, "mood": 8, "progress": 0, "patience": {"strict": -5, "gentle": 0, "balanced": -2}},
    "distract": {"focus": -8, "mood": 5, "progress": 0, "patience": {"strict": -10, "gentle": -5, "balanced": -8}},
    "cant_solve": {"focus": -6, "mood": -8, "progress": 0, "patience": {"strict": -6, "gentle": -2, "balanced": -4}},
}

# ==================== 数据类 ====================
class GameData:
    def __init__(self):
        self.participant_id = ""
        self.real_style = ""
        self.parent_style = "balanced"
        self.focus = 60
        self.mood = 70
        self.progress = 0
        self.patience = 80
        self.pre_questionnaire = []
        self.after_questionnaire = []
        self.game_records = []
        self.cur_parent_talk = ""
        self.cur_child_talk = ""
        self.cur_conflict = ""

    def reset_game(self):
        self.focus = 60
        self.mood = 70
        self.progress = 0
        self.patience = 80
        self.game_records.clear()
        self.cur_parent_talk = ""
        self.cur_child_talk = ""
        self.cur_conflict = ""

    def get_conflict_status(self):
        conflict = []
        if self.focus < 30: conflict.append("专注冲突")
        if self.mood < 20: conflict.append("情绪冲突")
        if self.patience < 20: conflict.append("亲子冲突")
        return "、".join(conflict) if conflict else ""

    def action_update(self, act_key):
        d = DELTA[act_key]
        self.focus = max(0, min(100, self.focus + d["focus"]))
        self.mood = max(0, min(100, self.mood + d["mood"]))
        self.patience = max(0, min(100, self.patience + d["patience"][self.parent_style]))
        self.progress = max(0, min(100, self.progress + d["progress"]))
        self.cur_conflict = self.get_conflict_status()
        talk_lib = DIALOGUE_PAIRS[self.parent_style]
        if self.cur_conflict:
            p_talk, c_talk = random.choice(talk_lib["conflict"])
        else:
            p_talk, c_talk = random.choice(talk_lib[act_key])
        self.cur_parent_talk = p_talk
        self.cur_child_talk = c_talk
        self.game_records.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": ACTION_CN[act_key],
            "focus": self.focus, "mood": self.mood,
            "progress": self.progress, "patience": self.patience,
            "conflict": self.cur_conflict,
            "parent_words": p_talk, "child_words": c_talk
        })

# ==================== 初始化 ====================
if "user_data" not in st.session_state:
    st.session_state.user_data = GameData()
if "page_flag" not in st.session_state:
    st.session_state.page_flag = "input_id"
if "animate_playing" not in st.session_state:
    st.session_state.animate_playing = False

user = st.session_state.user_data
page = st.session_state.page_flag

# ==================== 页面1：编号 ====================
if page == "input_id":
    st.title("家庭教育视角互换实验")
    pid = st.text_input("实验编号", placeholder="如：P01")
    if st.button("进入问卷") and pid:
        user.participant_id = pid
        st.session_state.page_flag = "pre_ques"
        st.rerun()

# ==================== 页面2：前置问卷 ====================
elif page == "pre_ques":
    st.subheader("教养风格测评问卷")
    ans = []
    for i, (q, _) in enumerate(QUESTIONNAIRE):
        r = st.radio(f"{i+1}. {q}", [1,2,3,4], horizontal=True, format_func=lambda x:["完全不符合","不太符合","比较符合","完全符合"][x-1])
        ans.append(r)
    if st.button("提交并开始模拟", use_container_width=True):
        s = {"strict":0,"balanced":0,"gentle":0}
        for a, (_, t) in zip(ans, QUESTIONNAIRE): s[t]+=a
        best = sorted(s.items(), key=lambda x:x[1], reverse=True)[0][0]
        if s["balanced"] >= s[best]-1: best="balanced"
        user.parent_style = best
        user.real_style = STYLE_NAMES[best]
        user.pre_questionnaire = ans
        user.reset_game()
        st.success(f"你的风格：{user.real_style}")
        st.session_state.page_flag = "game_run"
        st.rerun()

# ==================== 页面3：游戏界面（带对话动画！）====================
elif page == "game_run":
    st.subheader(f"作业辅导模拟 | 风格：{user.real_style}")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("专注度", f"{user.focus}%"), c1.progress(user.focus/100)
    c2.metric("情绪值", f"{user.mood}%"), c2.progress(user.mood/100)
    c3.metric("进度", f"{user.progress}%"), c3.progress(user.progress/100)
    c4.metric("耐心", f"{user.patience}%"), c4.progress(user.patience/100)

    st.divider()
    st.markdown("## 💬 实时对话（带打字动画）")
    chat_area = st.empty()  # 动画区域

    # 冲突显示
    if user.cur_conflict:
        st.error(f"⚠️ 发生冲突：{user.cur_conflict}")

    # 操作区
    act = st.radio("孩子行为：", ["做作业","休息","开小差","题目不会"], horizontal=True)
    act_map = {"做作业":"homework","休息":"rest","开小差":"distract","题目不会":"cant_solve"}

    if st.button("▶️ 执行互动", type="primary", use_container_width=True):
        user.action_update(act_map[act])
        st.session_state.animate_playing = True
        st.rerun()

    # 打字动画（你要的效果）
    if st.session_state.animate_playing and user.cur_parent_talk:
        with chat_area.container():
            pcol, ccol = st.columns(2)
            with pcol:
                st.chat_message("parent").write("家长：")
                text = ""
                t = st.empty()
                for ch in user.cur_parent_talk:
                    text += ch
                    t.markdown(f"**{text}**")
                    time.sleep(0.04)
            with ccol:
                st.chat_message("child").write("孩子：")
                text2 = ""
                t2 = st.empty()
                time.sleep(0.2)
                for ch in user.cur_child_talk:
                    text2 += ch
                    t2.markdown(text2)
                    time.sleep(0.04)
        st.session_state.animate_playing = False

    # 完成判断
    if user.progress >= 100:
        st.balloons()
        st.success("✅ 作业完成！")
        if st.button("前往反思报告", use_container_width=True):
            st.session_state.page_flag = "reflection"
            st.rerun()
    else:
        st.caption(f"当前进度：{user.progress}%，需达到100%完成")

# ==================== 页面4：反思报告 ====================
elif page == "reflection":
    st.title("📊 深度反思报告")
    st.info(f"编号：{user.participant_id} | 风格：{user.real_style}")
    if user.game_records:
        df = pd.DataFrame(user.game_records)
        st.subheader("状态趋势")
        st.line_chart(df, y=["focus","mood","progress","patience"])
        col1,col2,col3 = st.columns(3)
        col1.metric("总操作", len(user.game_records))
        col2.metric("最低专注", f"{min([60]+[x['focus']for x in user.game_records])}%")
        col3.metric("最低情绪", f"{min([70]+[x['mood']for x in user.game_records])}%")
        st.subheader("冲突统计")
        clist = [r["conflict"]for r in user.game_records if r["conflict"]]
        if clist: st.bar_chart(pd.Series(clist).value_counts())
        else: st.write("无冲突")
    st.markdown(f"""
    ### 总结
    本次模拟采用 **{user.real_style}** 教育方式，全程共发生 **{len(clist)} 次冲突**。
    专制型易引发情绪对抗，放任型进度缓慢，权威型最稳定。
    """)
    if st.button("前往后置问卷", use_container_width=True):
        st.session_state.page_flag = "after_survey"
        st.rerun()

# ==================== 页面5：后置问卷 ====================
elif page == "after_survey":
    st.title("📋 体验反馈问卷")
    answers = []
    for i, q in enumerate(AFTER_SURVEY_QUESTIONS):
        r = st.radio(f"{i+1}. {q}", [1,2,3,4,5], horizontal=True, format_func=lambda x:["非常不同意","不同意","一般","同意","非常同意"][x-1])
        answers.append(r)
    if st.button("提交并生成数据", use_container_width=True, type="primary"):
        data = {
            "编号":user.participant_id,"风格":user.real_style,
            "前置问卷":user.pre_questionnaire,
            "游戏记录":user.game_records,
            "后置问卷":answers
        }
        js = json.dumps(data, ensure_ascii=False, indent=2)
        st.success("提交成功！")
        st.download_button("💾 下载全套数据", js, f"实验数据_{user.participant_id}.json", use_container_width=True)
