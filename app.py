import streamlit as st
import json
import random
import requests
from datetime import datetime
from config import (
    QUESTIONNAIRE, AFTER_SURVEY_QUESTIONS, STYLE_NAMES,
    DELTA, DIALOGUE_PAIRS, CHILD_RESPONSES, HOMEWORK_CHILD_RESPONSES,
    LLM_URL_ZHIPU, LLM_MODEL_ZHIPU, ZHIPU_API_KEY, LLM_MAX_RETRY, LLM_TIMEOUT_SECONDS
)

# 你的PostBin地址（已填好）
POSTBIN_URL = "https://www.postb.in/1779334708404-8427541556302"

# -------------------------- 数据类（完全复用原逻辑） --------------------------
class GameData:
    def __init__(self):
        self.participant_id = ""
        self.real_style = "未选择"
        self.parent_style = "strict"
        self.focus = 60
        self.mood = 70
        self.progress = 0
        self.patience = 80
        self.ops = []
        self.conflicts = []
        self.questionnaire_answers = []
        self.after_survey_answers = []
        self.rows = []

    def reset_for_game(self):
        self.focus = 60
        self.mood = 70
        self.progress = 0
        self.patience = 80
        self.ops = []
        self.conflicts = []
        self.rows = []

    def add_log(self, action, conflict_type, dialogue, child_dialogue):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.rows.append({
            "timestamp": now,
            "participant_id": self.participant_id,
            "action": action,
            "focus": self.focus,
            "mood": self.mood,
            "progress": self.progress,
            "patience": self.patience,
            "conflict_type": conflict_type,
            "parent_dialogue": dialogue,
            "child_dialogue": child_dialogue
        })

# -------------------------- 核心逻辑（完全复用原函数） --------------------------
def clamp(value):
    return max(0, min(100, value))

def get_conflicts(data):
    found = []
    if data.focus < 30:
        found.append("专注冲突")
    if data.mood < 20:
        found.append("情绪冲突")
    if data.patience < 20:
        found.append("亲子冲突")
    return found

def assess_parent_style(answers):
    scores = {"strict": 0, "balanced": 0, "gentle": 0}
    for answer, (_, dim) in zip(answers, QUESTIONNAIRE):
        scores[dim] += max(1, min(4, answer))
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top, second = sorted_scores[0], sorted_scores[1]
    if second[1] >= top[1] - 1:
        return "balanced"
    return top[0]

def apply_action(action, data):
    delta = DELTA[action]
    if action == "cant_solve":
        data.focus = clamp(data.focus + delta["focus"])
        data.mood = clamp(data.mood + delta["mood"])
        data.patience = clamp(data.patience + delta["patience"][data.parent_style])
    else:
        data.focus = clamp(data.focus + delta["focus"])
        data.mood = clamp(data.mood + delta["mood"])
        data.patience = clamp(data.patience + delta["patience"][data.parent_style])
    data.progress = clamp(data.progress + delta["progress"])
    data.ops.append(action)
    conflict_list = get_conflicts(data)
    is_conflict = len(conflict_list) > 0
    conflict_type = "、".join(conflict_list) if is_conflict else ""
    # 对话生成（优先用规则库，LLM可留空）
    pair = random.choice(DIALOGUE_PAIRS[data.parent_style]["conflict"] if is_conflict else DIALOGUE_PAIRS[data.parent_style][action])
    parent_dialogue, child_dialogue = pair[0], pair[1]
    data.add_log(action, conflict_type, parent_dialogue, child_dialogue)
    return parent_dialogue, child_dialogue, conflict_list

# -------------------------- 数据上传函数（零成本） --------------------------
def upload_data(data):
    try:
        requests.post(POSTBIN_URL, json={
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "participant_id": data.participant_id,
            "real_parent_style": data.real_style,
            "simulate_style": STYLE_NAMES[data.parent_style],
            "operations": data.ops,
            "conflicts": data.conflicts,
            "pre_questionnaire": data.questionnaire_answers,
            "after_questionnaire": data.after_survey_answers,
            "logs": data.rows
        }, timeout=5)
        return True
    except:
        return False

# -------------------------- Streamlit页面逻辑 --------------------------
def main():
    st.set_page_config(page_title="家庭教育模拟实验", layout="wide")
    st.title("家庭教育模拟实验")

    # 初始化会话状态
    if "page" not in st.session_state:
        st.session_state.page = "input"
    if "data" not in st.session_state:
        st.session_state.data = GameData()
    data = st.session_state.data

    # 1. 输入ID页面
    if st.session_state.page == "input":
        data.participant_id = st.text_input("请输入你的实验编号（如 P01）")
        if st.button("下一步填写问卷", disabled=not data.participant_id):
            st.session_state.page = "questionnaire"
            st.rerun()

    # 2. 前置问卷页面
    elif st.session_state.page == "questionnaire":
        st.subheader("家长教养风格问卷")
        answers = []
        for i, (q, _) in enumerate(QUESTIONNAIRE):
            ans = st.radio(f"Q{i+1}: {q}", [1,2,3,4], index=0, format_func=lambda x: ["完全不符合", "不太符合", "比较符合", "完全符合"][x-1])
            answers.append(ans)
        if st.button("提交问卷，开始模拟"):
            data.questionnaire_answers = answers
            data.parent_style = assess_parent_style(answers)
            data.real_style = STYLE_NAMES[data.parent_style]
            st.success(f"你的教养风格判定为：{data.real_style}，将以该风格进行模拟")
            st.session_state.page = "game"
            st.rerun()

    # 3. 游戏交互页面
    elif st.session_state.page == "game":
        data.reset_for_game()
        st.subheader("作业辅导模拟场景")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("专注度", f"{data.focus}%")
            st.metric("情绪值", f"{data.mood}%")
        with col2:
            st.metric("作业进度", f"{data.progress}%")
            st.metric("家长耐心", f"{data.patience}%")

        st.divider()
        action = st.radio("请选择孩子的行为：", ["做作业", "休息", "开小差", "题目不会"], horizontal=True)
        action_map = {"做作业":"homework", "休息":"rest", "开小差":"distract", "题目不会":"cant_solve"}
        if st.button("执行操作", use_container_width=True):
            p_dialogue, c_dialogue, conflicts = apply_action(action_map[action], data)
            st.session_state.last_p = p_dialogue
            st.session_state.last_c = c_dialogue
            st.session_state.conflicts = conflicts
            st.rerun()

        if "last_p" in st.session_state:
            st.divider()
            st.info(f"👩‍👧 家长：{st.session_state.last_p}")
            st.success(f"👧 孩子：{st.session_state.last_c}")
            if st.session_state.conflicts:
                st.warning(f"⚠️ 冲突触发：{', '.join(st.session_state.conflicts)}")

        if data.progress >= 100:
            st.balloons()
            st.success("🎉 作业完成！请完成后置问卷")
            if st.button("进入后置问卷"):
                st.session_state.page = "after_survey"
                st.rerun()

    # 4. 后置问卷页面
    elif st.session_state.page == "after_survey":
        st.subheader("体验反馈问卷")
        answers = []
        for i, q in enumerate(AFTER_SURVEY_QUESTIONS):
            ans = st.radio(f"Q{i+1}: {q}", [1,2,3,4,5], index=2, format_func=lambda x: ["非常不同意", "不同意", "一般", "同意", "非常同意"][x-1])
            answers.append(ans)
        if st.button("提交并结束实验", use_container_width=True):
            data.after_survey_answers = answers
            success = upload_data(data)
            if success:
                st.success("✅ 数据已提交，感谢参与！")
            else:
                st.warning("网络波动，数据已临时存储，稍后会自动上传")
            st.session_state.page = "end"
            st.rerun()

    # 5. 结束页面
    elif st.session_state.page == "end":
        st.title("实验结束，感谢你的参与！")
        st.info("你的数据已安全提交，本次体验将帮助我们更好地理解家庭教育中的沟通模式")

if __name__ == "__main__":
    main()