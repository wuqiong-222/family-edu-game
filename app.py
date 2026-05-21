import streamlit as st
import json
import random
import requests
from datetime import datetime
import pandas as pd
import sqlite3

st.set_page_config(
    page_title="家庭教育视角互换实验",
    layout="wide",
    page_icon="👨‍👩‍👧",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
header,
div[data-testid="stHeader"],
div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
#MainMenu {
    display: none !important;
    height: 0 !important;
    visibility: hidden !important;
}
.appview-container .main .block-container,
div[data-testid="stMainBlockContainer"] {
    padding-top: 0rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}
div[data-testid="stSidebar"] {
    padding-top: 0rem !important;
}
h1, h2, h3 {
    white-space: nowrap !important;
    overflow: visible !important;
    margin-top: 0 !important;
    padding-top: 0 !important;
}
@media (max-width: 768px) {
    h1 { font-size: 20px !important; }
    h2 { font-size: 18px !important; }
    h3 { font-size: 16px !important; }
    .stRadio > div {
        flex-direction: column !important;
        gap: 8px !important;
    }
}
</style>
""", unsafe_allow_html=True)

conn = sqlite3.connect('family_edu_data.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS submissions
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              experiment_id TEXT,
              real_style TEXT,
              pre_questionnaire TEXT,
              game_records TEXT,
              after_questionnaire TEXT,
              timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

def save_submission(data):
    c.execute("INSERT INTO submissions (experiment_id, real_style, pre_questionnaire, game_records, after_questionnaire) VALUES (?, ?, ?, ?, ?)",
              (data["基础信息"]["实验编号"],
               data["基础信息"]["判定教养风格"],
               json.dumps(data["前置问卷作答"]),
               json.dumps(data["游戏全程操作数据"]),
               json.dumps(data["后置问卷作答"])))
    conn.commit()

USE_LLM = True
LLM_PROVIDER = "zhipu"
LLM_URL_ZHIPU = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
LLM_MODEL_ZHIPU = "glm-4-flash"
ZHIPU_API_KEY = "9b3679a915614c8c8e342390bbe798fa.9CkuesKtmmNyhTtF"
LLM_TIMEOUT_SECONDS = 10
LLM_MAX_RETRY = 2

STYLE_NAMES = {"strict": "专制型", "gentle": "放任型", "balanced": "权威型"}
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
        "homework": [("抓紧认真写，不许磨蹭", "知道啦，我尽量做好")],
        "rest": [("作业没完成不能随便休息", "我已经写很久有点累了")],
        "distract": [("专心做题，不要分心贪玩", "一不小心走神了")],
        "cant_solve": [("基础题都不会，上课没用心", "知识点有点没弄懂")],
        "conflict": [("态度端正一点，认真对待学习", "我会调整状态好好完成")]
    },
    "gentle": {
        "homework": [("慢慢写就行，不用太过紧张", "好的，我稳步完成")],
        "rest": [("累了就歇一会，不用勉强自己", "放松下再继续做题")],
        "distract": [("分心也没关系，之后补上就好", "接下来我专心做题")],
        "cant_solve": [("不会就先搁置，之后再处理", "先跳过做其他题目")],
        "conflict": [("不用有压力，放平心态就好", "我舒缓情绪继续学习")]
    },
    "balanced": {
        "homework": [("合理把控速度，保证书写质量", "我兼顾速度和工整度")],
        "rest": [("完成阶段性任务，可以短时放松", "休整过后继续努力")],
        "distract": [("察觉分心及时拉回注意力哦", "意识到了立刻专注")],
        "cant_solve": [("遇到难题正常，我们一起分析", "麻烦帮我梳理下思路")],
        "conflict": [("出现情绪波动，调整后继续推进", "平复心情接着完成任务")]
    }
}

DELTA = {
    "homework": {"focus": 5, "mood": -3, "progress": 10, "patience": {"strict": 2, "gentle": 3, "balanced": 2}},
    "rest": {"focus": -3, "mood": 8, "progress": 0, "patience": {"strict": -5, "gentle": 0, "balanced": -2}},
    "distract": {"focus": -8, "mood": 5, "progress": 0, "patience": {"strict": -10, "gentle": -5, "balanced": -8}},
    "cant_solve": {"focus": -6, "mood": -8, "progress": 0, "patience": {"strict": -6, "gentle": -2, "balanced": -4}},
}

def ai_generate_dialogue(style, action, is_conflict):
    style_text = STYLE_NAMES[style]
    action_text = ACTION_CN[action]
    conflict_text = "出现冲突" if is_conflict else "正常沟通"
    prompt = f"""你是{style_text}家长，孩子正在{action_text}，当前{conflict_text}。请生成一句家长一句孩子。"""
    headers = {"Authorization": f"Bearer {ZHIPU_API_KEY}", "Content-Type": "application/json"}
    data = {"model": LLM_MODEL_ZHIPU, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
    for _ in range(LLM_MAX_RETRY):
        try:
            res = requests.post(LLM_URL_ZHIPU, headers=headers, json=data, timeout=LLM_TIMEOUT_SECONDS)
            if res.status_code == 200:
                return json.loads(res.json()["choices"][0]["message"]["content"].strip())
        except:
            continue
    return None

def get_local_dialogue(style, action, is_conflict):
    lib = DIALOGUE_PAIRS[style]
    key = "conflict" if is_conflict else action
    p, c = random.choice(lib[key])
    return {"parent": p, "child": c}

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
        conflict_flag = bool(self.cur_conflict)
        dialog = ai_generate_dialogue(self.parent_style, act_key, conflict_flag) if USE_LLM else None
        if not dialog: dialog = get_local_dialogue(self.parent_style, act_key, conflict_flag)
        self.cur_parent_talk = dialog["parent"]
        self.cur_child_talk = dialog["child"]
        record = {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "action": ACTION_CN[act_key],
                  "focus": self.focus, "mood": self.mood, "progress": self.progress, "patience": self.patience,
                  "conflict": self.cur_conflict, "parent_words": dialog["parent"], "child_words": dialog["child"]}
        self.game_records.append(record)

if "user_data" not in st.session_state:
    st.session_state.user_data = GameData()
if "page_flag" not in st.session_state:
    st.session_state.page_flag = "input_id"
if "admin_login" not in st.session_state:
    st.session_state.admin_login = False

user = st.session_state.user_data
page = st.session_state.page_flag

with st.sidebar:
    st.title("系统菜单")
    menu_choice = st.radio("功能选择", ["参与实验", "数据管理"])
    if menu_choice == "数据管理":
        if not st.session_state.admin_login:
            pwd = st.text_input("管理员密码", type="password")
            if st.button("登录验证"):
                if pwd == "123456":
                    st.session_state.admin_login = True
                    st.rerun()
                else:
                    st.error("密码错误")
        else:
            st.success("已登录管理员")
            if st.button("退出登录"):
                st.session_state.admin_login = False
                st.rerun()

if menu_choice == "数据管理":
    if st.session_state.admin_login:
        st.title("📊 实验数据管理后台")
        df = pd.read_sql("SELECT id, experiment_id, real_style, timestamp FROM submissions", conn)
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            sel_id = st.selectbox("选择ID查看详情", df["id"].tolist())
            row = df[df["id"] == sel_id].iloc[0]
            st.subheader(f"提交详情 ID：{sel_id}")
            st.write(f"实验编号：{row['experiment_id']}")
            st.write(f"教养风格：{row['real_style']}")
            st.write(f"提交时间：{row['timestamp']}")
            if st.button("查看完整数据"):
                full = pd.read_sql(f"SELECT * FROM submissions WHERE id={sel_id}", conn).iloc[0]
                st.json({"前置问卷": json.loads(full["pre_questionnaire"]),
                         "游戏记录": json.loads(full["game_records"]),
                         "后置问卷": json.loads(full["after_questionnaire"])})
        all_data = pd.read_sql("SELECT * FROM submissions", conn)
        st.download_button("导出全部CSV", all_data.to_csv(index=False, encoding="utf-8-sig"), "全部实验数据.csv")
    else:
        st.info("请输入密码登录后方可查看数据")

else:
    if page == "input_id":
        st.title("👨‍👩‍👧 家庭教育视角互换实验")
        pid = st.text_input("填写实验编号", placeholder="示例：P05")
        if st.button("进入测评问卷", disabled=not pid, use_container_width=True):
            user.participant_id = pid
            st.session_state.page_flag = "pre_ques"
            st.rerun()

    elif page == "pre_ques":
        st.subheader("📝 教养风格测评问卷")
        ans_list = []
        for idx, (que, _) in enumerate(QUESTIONNAIRE):
            opt = st.radio(f"{idx+1}. {que}", [1,2,3,4], horizontal=True,
                           format_func=lambda x:["完全不符合","不太符合","比较符合","完全符合"][x-1])
            ans_list.append(opt)
        if st.button("提交开启模拟", use_container_width=True, type="primary"):
            score = {"strict":0,"balanced":0,"gentle":0}
            for a, (_, dim) in zip(ans_list, QUESTIONNAIRE):
                score[dim] += a
            final_style = max(score, key=score.get)
            user.parent_style = final_style
            user.real_style = STYLE_NAMES[final_style]
            user.pre_questionnaire = ans_list
            user.reset_game()
            st.success("测评完成，即将进入模拟场景")
            st.session_state.page_flag = "game_run"
            st.rerun()

    elif page == "game_run":
        st.subheader("📚 作业辅导模拟")
        st.divider()
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
        st.markdown("### 💬 亲子对话")
        if user.cur_conflict:
            st.error(f"⚠️ 冲突：{user.cur_conflict}")
        if user.cur_parent_talk:
            st.chat_message("家长", avatar="👩").write(user.cur_parent_talk)
            st.chat_message("孩子", avatar="🧒").write(user.cur_child_talk)

        st.divider()
        st.markdown("### 🎮 互动操作")
        act_select = st.radio("选择孩子行为", ["做作业","休息","开小差","题目不会"], horizontal=True)
        act_map = {"做作业":"homework","休息":"rest","开小差":"distract","题目不会":"cant_solve"}
        if st.button("执行互动", type="primary", use_container_width=True):
            user.action_update(act_map[act_select])
            st.rerun()

        st.divider()
        if user.progress >= 100:
            st.balloons()
            st.success("🎉 辅导任务完成")
            if st.button("查看反思报告", use_container_width=True):
                st.session_state.page_flag = "reflection"
                st.rerun()
        else:
            st.info(f"当前进度：{user.progress}%，继续互动完成任务")

    elif page == "reflection":
        st.title("📊 体验反思报告")
        style_name = user.real_style
        total_steps = len(user.game_records)
        conflict_list = [r["conflict"] for r in user.game_records if r["conflict"]]
        conflict_count = len(conflict_list)
        min_focus = min([60] + [x['focus'] for x in user.game_records])
        min_mood = min([70] + [x['mood'] for x in user.game_records])

        st.markdown(f"""
### 一、你的教养方式判定
本次模拟你的教养方式：**{style_name}**

### 二、本次模拟关键数据
- 总互动次数：**{total_steps} 次**
- 亲子冲突次数：**{conflict_count} 次**
- 孩子最低专注度：**{min_focus}%**
- 孩子最低情绪值：**{min_mood}%**

### 三、基于家庭作业互动研究的解读
根据《Homework Wars》对78个中国家庭的实证研究：
家长辅导作业时会出现显著情绪变化：愉悦度下降、唤醒度上升、控制感降低。
研究发现7类高频冲突：知识冲突、学习方法冲突、专注冲突、沟通冲突、规则冲突、时间管理冲突、期望冲突。

### 四、教养模式分析
- **专制型**：高控制、低支持，冲突频繁
- **放任型**：高支持、低控制，效率偏低
- **权威型**：高支持+高结构，状态最稳定、冲突最少、长期效果最优

### 五、关键结论
即使正向行为（表扬、鼓励）若带有控制色彩，也会提升冲突概率。
真正有效的育儿是：**共情回应 + 清晰规则 + 温和坚定**。

### 六、科学育儿建议
1. 理解孩子认知难度，减少知识冲突
2. 不用批评、指责、贴标签
3. 减少攀比与过高期望
4. 多使用具体表扬、鼓励、引导提问
5. 温和而坚定，建立权威型教养
""")

        st.divider()
        st.subheader("🔁 体验权威型家长模式")
        st.info("点击下方按钮，直接体验【权威型家长】，无需重新测评！")
        if st.button("立即体验权威型家长", use_container_width=True, type="primary"):
            user.parent_style = "balanced"
            user.real_style = "权威型"
            user.reset_game()
            st.session_state.page_flag = "game_run"
            st.rerun()

        if st.button("填写后置问卷", use_container_width=True):
            st.session_state.page_flag = "after_survey"
            st.rerun()

    elif page == "after_survey":
        st.title("📋 后置调查问卷")
        answers = []
        for idx, que in enumerate(AFTER_SURVEY_QUESTIONS):
            ans = st.radio(f"Q{idx+1}: {que}", [1,2,3,4,5], horizontal=True,
                           format_func=lambda x: ["非常不同意", "不同意", "一般", "同意", "非常同意"][x-1])
            answers.append(ans)
        if st.button("提交并导出数据", use_container_width=True, type="primary"):
            all_final_data = {
                "基础信息":{"实验编号":user.participant_id,"判定教养风格":user.real_style},
                "前置问卷作答":user.pre_questionnaire,
                "游戏全程操作数据":user.game_records,
                "后置问卷作答":answers
            }
            save_submission(all_final_data)
            st.success("✅ 数据提交完成！")
            st.download_button("💾 下载数据文件", json.dumps(all_final_data, ensure_ascii=False, indent=3),
                               f"全套数据_{user.participant_id}.json", "application/json", use_container_width=True)

conn.close()
