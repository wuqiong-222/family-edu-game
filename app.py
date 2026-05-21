import streamlit as st
import json
import random
import requests
from datetime import datetime
import pandas as pd

# 页面配置
st.set_page_config(page_title="家庭教育实验", layout="wide")

# 常量
STYLE_NAMES = {"strict": "专制型", "gentle": "放任型", "balanced": "权威型"}
ACTION_CN = {"homework": "做作业", "rest": "休息", "distract": "开小差", "cant_solve": "题目不会"}

# 前置问卷
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

# 后置问卷
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

# 对话兜底
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

# 状态规则
DELTA = {
    "homework": {"focus": 5, "mood": -3, "progress": 10, "patience": {"strict": 2, "gentle": 3, "balanced": 2}},
    "rest": {"focus": -3, "mood": 8, "progress": 0, "patience": {"strict": -5, "gentle": 0, "balanced": -2}},
    "distract": {"focus": -8, "mood": 5, "progress": 0, "patience": {"strict": -10, "gentle": -5, "balanced": -8}},
    "cant_solve": {"focus": -6, "mood": -8, "progress": 0, "patience": {"strict": -6, "gentle": -2, "balanced": -4}},
}

# AI配置
USE_LLM = True
LLM_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
LLM_MODEL = "glm-4-flash"
API_KEY = "9b3679a915614c8c8e342390bbe798fa.9CkuesKtmmNyhTtF"

# AI对话生成
def generate_ai_dialog(style, action, is_conflict):
    style_desc = {"strict":"专制型家长，严格强势","gentle":"放任型家长，宽松包容","balanced":"权威型家长，理性引导"}
    action_desc = {"homework":"孩子正在写作业","rest":"孩子想要休息","distract":"孩子写作业开小差","cant_solve":"孩子遇到不会做的题目"}
    scene = "冲突状态" if is_conflict else "正常辅导"
    prompt = f"""你是{style_desc[style]}，场景：{action_desc[action]}，当前：{scene}。输出简短对话，各一句。只返回JSON：{{"parent":"","child":"","source":"ai"}}"""
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}]}
    try:
        resp = requests.post(LLM_URL, json=data, timeout=10)
        return eval(resp.json()["choices"][0]["message"]["content"])
    except:
        return None

# 游戏数据类
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
        self.dialog_source = ""

    def reset_game(self):
        self.focus = 60
        self.mood = 70
        self.progress = 0
        self.patience = 80
        self.game_records.clear()
        self.cur_parent_talk = ""
        self.cur_child_talk = ""
        self.cur_conflict = ""
        self.dialog_source = ""

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

        # 优先AI，失败兜底
        dialog = generate_ai_dialog(self.parent_style, act_key, bool(self.cur_conflict)) if USE_LLM else None
        if dialog is None:
            key = "conflict" if self.cur_conflict else act_key
            p, c = random.choice(DIALOGUE_PAIRS[self.parent_style][key])
            dialog = {"parent": p, "child": c, "source": "规则兜底"}

        self.cur_parent_talk = dialog["parent"]
        self.cur_child_talk = dialog["child"]
        self.dialog_source = dialog["source"]

        self.game_records.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": ACTION_CN[act_key],
            "focus": self.focus, "mood": self.mood,
            "progress": self.progress, "patience": self.patience,
            "conflict": self.cur_conflict,
            "parent_words": self.cur_parent_talk,
            "child_words": self.cur_child_talk,
            "dialog_source": self.dialog_source
        })

# 页面主逻辑
def main():
    if "user_data" not in st.session_state:
        st.session_state.user_data = GameData()
    if "page" not in st.session_state:
        st.session_state.page = "input_id"

    user = st.session_state.user_data
    current_page = st.session_state.page

    if current_page == "input_id":
        st.title("家庭教育视角互换实验")
        pid = st.text_input("填写实验编号", placeholder="示例：P05")
        if st.button("进入教养问卷", disabled=not pid):
            user.participant_id = pid
            st.session_state.page = "pre_ques"
            st.rerun()

    elif current_page == "pre_ques":
        st.subheader("家长教养风格测评问卷")
        ans_list = []
        for idx, (que, _) in enumerate(QUESTIONNAIRE):
            opt = st.radio(f"{idx+1}. {que}", [1,2,3,4], horizontal=True,
                           format_func=lambda x: ["完全不符合","不太符合","比较符合","完全符合"][x-1])
            ans_list.append(opt)
        if st.button("提交问卷，开启模拟", use_container_width=True):
            score_dict = {"strict":0,"balanced":0,"gentle":0}
            for a, (_, dim) in zip(ans_list, QUESTIONNAIRE):
                score_dict[dim] += a
            sort_res = sorted(score_dict.items(), key=lambda x:x[1], reverse=True)
            final_style = sort_res[0][0] if sort_res[1][1] < sort_res[0][1]-1 else "balanced"
            user.parent_style = final_style
            user.real_style = STYLE_NAMES[final_style]
            user.pre_questionnaire = ans_list
            user.reset_game()
            st.success(f"判定完成，你的教养风格：{user.real_style}")
            st.session_state.page = "game_run"
            st.rerun()

    elif current_page == "game_run":
        st.subheader(f"作业辅导模拟 | 风格：{user.real_style}")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("专注度", f"{user.focus}%"), c1.progress(user.focus/100)
        c2.metric("情绪值", f"{user.mood}%"), c2.progress(user.mood/100)
        c3.metric("作业进度", f"{user.progress}%"), c3.progress(user.progress/100)
        c4.metric("耐心值", f"{user.patience}%"), c4.progress(user.patience/100)

        st.divider()
        st.markdown("## 💬 对话区")

        if user.cur_parent_talk:
            st.markdown(f"👨‍👩 **家长**（{user.dialog_source}）")
            st.success(user.cur_parent_talk)
            st.markdown("👦 **孩子**")
            st.info(user.cur_child_talk)

        if user.cur_conflict:
            st.error(f"⚠️ 冲突发生：{user.cur_conflict}")

        act = st.radio("孩子行为", ["做作业","休息","开小差","题目不会"], horizontal=True)
        act_map = {"做作业":"homework","休息":"rest","开小差":"distract","题目不会":"cant_solve"}
        if st.button("执行互动", type="primary", use_container_width=True):
            user.action_update(act_map[act])
            st.rerun()

        if user.progress >= 100:
            st.success("✅ 作业完成！")
            if st.button("前往反思报告", use_container_width=True):
                st.session_state.page = "reflection"
                st.rerun()

    elif current_page == "reflection":
        st.title("📊 反思报告")
        st.info(f"编号：{user.participant_id} | 风格：{user.real_style}")
        if user.game_records:
            df = pd.DataFrame(user.game_records)
            st.subheader("状态趋势")
            st.line_chart(df, y=["focus","mood","progress","patience"])
            st.subheader("对话来源统计")
            st.dataframe(df["dialog_source"].value_counts())
        if st.button("前往后置问卷", use_container_width=True):
            st.session_state.page = "after_survey"
            st.rerun()

    elif current_page == "after_survey":
        st.title("📋 后置问卷")
        answers = []
        for i, q in enumerate(AFTER_SURVEY_QUESTIONS):
            r = st.radio(f"{i+1}. {q}", [1,2,3,4,5], horizontal=True,
                         format_func=lambda x:["非常不同意","不同意","一般","同意","非常同意"][x-1])
            answers.append(r)
        if st.button("提交并下载数据", type="primary", use_container_width=True):
            data = {
                "编号":user.participant_id,"风格":user.real_style,
                "前置问卷":user.pre_questionnaire,
                "记录":user.game_records,
                "后置问卷":answers
            }
            js = json.dumps(data, ensure_ascii=False, indent=2)
            st.success("提交成功！")
            st.download_button("下载数据", js, f"数据_{user.participant_id}.json", use_container_width=True)

if __name__ == "__main__":
    main()
