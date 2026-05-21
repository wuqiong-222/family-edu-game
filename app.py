import streamlit as st
import json
import random
from datetime import datetime
import pandas as pd

# 页面全局美化配置
st.set_page_config(page_title="家庭教育视角互换实验", layout="wide", page_icon="👨‍👩‍👧")

# 全局样式注入
st.markdown("""
<style>
.main {background-color: #f8f9fa;}
.stChatMessage {border-radius: 12px; padding: 8px; margin: 6px 0;}
.stMetric {background: #ffffff; border-radius: 10px; padding:10px; box-shadow: 0 2px 6px #eee;}
div.stButton > button:first-child {border-radius:8px; font-weight:500;}
.stRadio > div {gap:10px;}
hr {margin:15px 0;}
</style>
""", unsafe_allow_html=True)

# ==================== 基础常量配置 ====================
STYLE_NAMES = {"strict": "专制型", "gentle": "放任型", "balanced": "权威型"}
STYLE_DESC = {
    "strict": "专制型：高要求低包容，习惯批评约束",
    "gentle": "放任型：低要求高包容，较少干预引导",
    "balanced": "权威型：有度要求包容，理性沟通引导"
}

ACTION_CN = {
    "homework": "做作业",
    "rest": "休息",
    "distract": "开小差",
    "cant_solve": "题目不会"
}

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
    "本次模拟中，我能顺利代入孩子视角感受状态",
    "游戏互动场景和现实家庭辅导情况贴合",
    "体验同款教养方式，体会到孩子内心感受",
    "明显察觉教养态度影响孩子情绪与学习状态",
    "体验帮助我重新审视自身日常教育沟通方式",
    "意识到不当教育行为会产生负面亲子影响",
    "理解有边界共情式教育的优势与合理性",
    "本次体验有效完成家庭教育换位思考反思",
    "体验后愿意调整自身教养沟通方式",
    "沉浸式模拟对亲子共情教育具备参考价值"
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

# ==================== 数据存储类 ====================
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
        if self.focus < 30:
            conflict.append("专注冲突")
        if self.mood < 20:
            conflict.append("情绪冲突")
        if self.patience < 20:
            conflict.append("亲子冲突")
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

        record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": ACTION_CN[act_key],
            "focus": self.focus,
            "mood": self.mood,
            "progress": self.progress,
            "patience": self.patience,
            "conflict": self.cur_conflict,
            "parent_words": p_talk,
            "child_words": c_talk
        }
        self.game_records.append(record)

# 初始化会话
if "user_data" not in st.session_state:
    st.session_state.user_data = GameData()
if "page_flag" not in st.session_state:
    st.session_state.page_flag = "input_id"

user = st.session_state.user_data
page = st.session_state.page_flag

# ==================== 页面1 输入编号 ====================
if page == "input_id":
    st.title("👨‍👩‍👧 家庭教育视角互换实验")
    st.divider()
    pid = st.text_input("请填写你的实验编号", placeholder="示例：P05")
    st.divider()
    if st.button("进入教养风格测评问卷", disabled=not pid, use_container_width=True):
        user.participant_id = pid
        st.session_state.page_flag = "pre_ques"
        st.rerun()

# ==================== 页面2 前置问卷 ====================
elif page == "pre_ques":
    st.subheader("📝 家长教养风格测评问卷")
    st.info("请根据自身实际情况选择对应符合程度")
    ans_list = []
    for idx, (que, _) in enumerate(QUESTIONNAIRE):
        opt = st.radio(f"{idx+1}. {que}", [1,2,3,4], horizontal=True,
                       format_func=lambda x:["完全不符合","不太符合","比较符合","完全符合"][x-1])
        ans_list.append(opt)
    st.divider()
    if st.button("提交问卷，开启模拟体验", use_container_width=True, type="primary"):
        score_dict = {"strict":0,"balanced":0,"gentle":0}
        for a, (_, dim) in zip(ans_list, QUESTIONNAIRE):
            score_dict[dim] += a
        sort_res = sorted(score_dict.items(), key=lambda x:x[1], reverse=True)
        if sort_res[1][1] >= sort_res[0][1]-1:
            final_style = "balanced"
        else:
            final_style = sort_res[0][0]
        user.parent_style = final_style
        user.real_style = STYLE_NAMES[final_style]
        user.pre_questionnaire = ans_list
        user.reset_game()
        st.success(f"测评完成，你的教养风格判定为：{user.real_style}")
        st.session_state.page_flag = "game_run"
        st.rerun()

# ==================== 页面3 游戏交互 对话上移布局 ====================
elif page == "game_run":
    st.subheader(f"📚 作业辅导模拟 | 当前教养风格：{user.real_style}")
    st.divider()
    # 状态面板
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("专注度", f"{user.focus}%")
    c1.progress(user.focus/100)
    c2.metric("情绪值", f"{user.mood}%")
    c2.progress(user.mood/100)
    c3.metric("作业进度", f"{user.progress}%")
    c3.progress(user.progress/100)
    c4.metric("耐心值", f"{user.patience}%")
    c4.progress(user.patience/100)

    st.divider()
    # ========== 亲子对话 放置在操作区域上方 ==========
    st.markdown("### 💬 实时亲子对话")
    if user.cur_conflict:
        st.error(f"⚠️ 现场冲突提示：{user.cur_conflict}")

    if user.cur_parent_talk:
        st.chat_message("家长", avatar="👩").write(user.cur_parent_talk)
        st.chat_message("孩子", avatar="🧒").write(user.cur_child_talk)

    st.divider()
    # 下方放置行为选择与操作按钮
    st.markdown("### 🎮 进行互动操作")
    act_select = st.radio("选择孩子当下行为状态", ["做作业","休息","开小差","题目不会"], horizontal=True)
    act_map = {"做作业":"homework","休息":"rest","开小差":"distract","题目不会":"cant_solve"}

    if st.button("执行本次互动操作", type="primary", use_container_width=True):
        user.action_update(act_map[act_select])
        st.rerun()

    st.divider()
    # 进度提示与解锁按钮
    if user.progress >= 100:
        st.balloons()
        st.success("🎉 本次作业辅导任务顺利完成！")
        if st.button("查看体验反思报告", use_container_width=True):
            st.session_state.page_flag = "reflection"
            st.rerun()
    else:
        st.info(f"当前作业完成进度：{user.progress}%，持续互动直至任务结束")

# ==================== 页面4 反思报告 ====================
elif page == "reflection":
    st.title("📊 模拟体验反思报告")
    st.info(f"实验编号：{user.participant_id} | 判定教养风格：{user.real_style}")
    st.divider()

    # 状态变化趋势
    if user.game_records:
        df = pd.DataFrame(user.game_records)
        st.subheader("📈 身心状态变化趋势")
        st.line_chart(df, y=["focus","mood","progress","patience"], use_container_width=True)

    # 基础统计
    st.subheader("📌 模拟数据基础统计")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总互动次数", len(user.game_records))
    with col2:
        st.metric("最低专注度", f"{min([60] + [x['focus'] for x in user.game_records])}%")
    with col3:
        st.metric("最低情绪值", f"{min([70] + [x['mood'] for x in user.game_records])}%")

    # 冲突统计
    st.subheader("⚠️ 亲子冲突发生统计")
    conflict_list = [r["conflict"] for r in user.game_records if r["conflict"]]
    if conflict_list:
        conflict_counts = pd.Series(conflict_list).value_counts()
        st.bar_chart(conflict_counts)
    else:
        st.write("本次模拟全程未产生亲子冲突")

    # 行为分布
    st.subheader("🎯 孩子行为频次分布")
    action_counts = pd.Series([r["action"] for r in user.game_records]).value_counts()
    st.bar_chart(action_counts)

    # 深度反思总结
    st.subheader("💡 体验感悟与反思总结")
    st.markdown(f"""
    本次以**{user.real_style}**模式完成辅导模拟，互动过程中状态波动直观体现了教养方式带来的影响：
    - **专制型**：易引发孩子情绪抵触，耐心消耗快，亲子冲突概率偏高
    - **放任型**：孩子情绪保持平稳，但作业推进效率偏低，规则约束力较弱
    - **权威型**：兼顾心态安抚与任务推进，整体冲突最少，教育效果更均衡

    **本次体验核心数据：**
    共触发 **{len(conflict_list)} 次冲突**，过程最低专注度 **{min([60] + [x['focus'] for x in user.game_records])}%**，最低情绪值 **{min([70] + [x['mood'] for x in user.game_records])}%**。
    换位思考后可清晰感知沟通方式对孩子学习心态的作用，后续可调整沟通语气与边界尺度，减少不必要矛盾。
    """)
    st.divider()
    if st.button("填写体验后置问卷", use_container_width=True):
        st.session_state.page_flag = "after_survey"
        st.rerun()

# ==================== 页面5 后置问卷 ====================
elif page == "after_survey":
    st.title("📋 体验后置调查问卷")
    st.info("结合本次沉浸式模拟体验，如实选择你的感受程度")
    st.divider()
    answers = []
    for idx, que in enumerate(AFTER_SURVEY_QUESTIONS):
        ans = st.radio(f"Q{idx+1}: {que}", [1,2,3,4,5], horizontal=True,
                       format_func=lambda x: ["非常不同意", "不同意", "一般", "同意", "非常同意"][x-1])
        answers.append(ans)

    # 整合全部数据
    all_final_data = {
        "基础信息":{
            "实验编号":user.participant_id,
            "判定教养风格":user.real_style
        },
        "前置问卷作答":user.pre_questionnaire,
        "游戏全程操作数据":user.game_records,
        "后置问卷作答":answers
    }
    st.divider()
    if st.button("提交问卷并导出全套实验数据", use_container_width=True, type="primary"):
        user.after_questionnaire = answers
        json_all = json.dumps(all_final_data, ensure_ascii=False, indent=3)
        st.success("✅ 所有数据提交完成，可下载保存实验档案")
        st.download_button("💾 下载JSON格式数据文件", json_all,
                           file_name=f"全套数据_{user.participant_id}.json",
                           mime="application/json", use_container_width=True)
