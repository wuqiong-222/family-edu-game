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

# -------------------------- 核心工具函数 --------------------------
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

# -------------------------- AI对话生成函数 --------------------------
def generate_ai_dialogue(parent_style, action, conflict_list):
    """调用智谱AI生成符合教养风格的家长对话"""
    if not ZHIPU_API_KEY:
        return None
    
    # 构建提示词
    style_desc = {
        "strict": "专制型家长，高要求、低包容，喜欢直接批评、强调规则和服从，说话直接、严厉",
        "gentle": "放任型家长，低要求、高包容，注重陪伴、不强制、鼓励自主，说话温和、不强势",
        "balanced": "权威型家长，适中要求、适中包容，先肯定再指出问题、引导改进，说话理性、有边界"
    }
    action_desc = {
        "homework": "孩子正在写作业",
        "rest": "孩子想休息",
        "distract": "孩子写作业开小差",
        "cant_solve": "孩子遇到不会的题目"
    }
    conflict_desc = ""
    if conflict_list:
        conflict_desc = f"当前出现了{', '.join(conflict_list)}，家长情绪受到影响"
    
    prompt = f"""
    你是一个{style_desc[parent_style]}，现在{action_desc[action]}。{conflict_desc}
    请生成一句符合你身份的家长对话，不要太长，口语化，直接给出对话内容即可。
    """

    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": LLM_MODEL_ZHIPU,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 50
    }

    for _ in range(LLM_MAX_RETRY):
        try:
            response = requests.post(
                LLM_URL_ZHIPU,
                headers=headers,
                json=data,
                timeout=LLM_TIMEOUT_SECONDS
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
        except:
            continue
    return None

# -------------------------- 核心逻辑（带AI对话） --------------------------
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

    # 优先调用AI生成对话，失败则用规则库
    parent_dialogue = generate_ai_dialogue(data.parent_style, action, conflict_list)
    if not parent_dialogue:
        pair = random.choice(DIALOGUE_PAIRS[data.parent_style]["conflict"] if is_conflict else DIALOGUE_PAIRS[data.parent_style][action])
        parent_dialogue, child_dialogue = pair[0], pair[1]
    else:
        # AI生成了家长对话，随机匹配一个孩子回应
        child_dialogue = random.choice(CHILD_RESPONSES[data.parent_style][action])

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

# -------------------------- Streamlit页面逻辑（美化版） --------------------------
def main():
    st.set_page_config(page_title="家庭教育模拟实验", layout="wide", page_icon="👨‍👩‍👧")
    st.title("🏠 家庭教育模拟实验")

    # 初始化会话状态
    if "page" not in st.session_state:
        st.session_state.page = "input"
    if "data" not in st.session_state:
        st.session_state.data = GameData()
    data = st.session_state.data

    # 1. 输入ID页面
    if st.session_state.page == "input":
        st.markdown("### 欢迎参与本次家庭教育视角互换实验")
        st.info("请输入你的实验编号，开始体验孩子视角的作业辅导场景")
        data.participant_id = st.text_input("请输入你的实验编号（如 P01）")
        if st.button("下一步填写问卷", disabled=not data.participant_id, use_container_width=True):
            st.session_state.page = "questionnaire"
            st.rerun()

    # 2. 前置问卷页面
    elif st.session_state.page == "questionnaire":
        st.subheader("📝 家长教养风格问卷")
        st.markdown("请根据你的真实情况选择，我们将根据你的回答判定你的教养风格")
        answers = []
        for i, (q, _) in enumerate(QUESTIONNAIRE):
            ans = st.radio(f"Q{i+1}: {q}", [1,2,3,4], index=0, format_func=lambda x: ["完全不符合", "不太符合", "比较符合", "完全符合"][x-1])
            answers.append(ans)
        if st.button("提交问卷，开始模拟", use_container_width=True):
            data.questionnaire_answers = answers
            data.parent_style = assess_parent_style(answers)
            data.real_style = STYLE_NAMES[data.parent_style]
            st.success(f"✅ 你的教养风格判定为：{data.real_style}，将以该风格进行模拟")
            # 只在进入游戏时重置一次数据，解决进度不动问题
            data.reset_for_game()
            st.session_state.page = "game"
            st.rerun()

    # 3. 游戏交互页面（修复进度问题+美化界面）
    elif st.session_state.page == "game":
        st.subheader("🎮 作业辅导模拟场景")
        
        # 状态卡片
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🧠 专注度", f"{data.focus}%")
            st.progress(data.focus/100)
        with col2:
            st.metric("😊 情绪值", f"{data.mood}%")
            st.progress(data.mood/100)
        with col3:
            st.metric("📚 作业进度", f"{data.progress}%")
            st.progress(data.progress/100)
        with col4:
            st.metric("⏳ 家长耐心", f"{data.patience}%")
            st.progress(data.patience/100)

        st.divider()
        action = st.radio("请选择孩子的行为：", ["做作业", "休息", "开小差", "题目不会"], horizontal=True)
        action_map = {"做作业":"homework", "休息":"rest", "开小差":"distract", "题目不会":"cant_solve"}
        if st.button("执行操作", use_container_width=True, type="primary"):
            p_dialogue, c_dialogue, conflicts = apply_action(action_map[action], data)
            st.session_state.last_p = p_dialogue
            st.session_state.last_c = c_dialogue
            st.session_state.conflicts = conflicts
            st.rerun()

        if "last_p" in st.session_state:
            st.divider()
            # 对话气泡美化
            with st.chat_message("user", avatar="👩‍👧"):
                st.markdown(f"**家长：** {st.session_state.last_p}")
            with st.chat_message("assistant", avatar="👧"):
                st.markdown(f"**孩子：** {st.session_state.last_c}")
            if st.session_state.conflicts:
                st.warning(f"⚠️ 冲突触发：{', '.join(st.session_state.conflicts)}")

        if data.progress >= 100:
            st.balloons()
            st.success("🎉 作业完成！请完成后置问卷")
            if st.button("进入后置问卷", use_container_width=True):
                st.session_state.page = "after_survey"
                st.rerun()

    # 4. 后置问卷页面
    elif st.session_state.page == "after_survey":
        st.subheader("📝 体验反馈问卷")
        st.markdown("请根据你的体验感受选择，帮助我们改进实验")
        answers = []
        for i, q in enumerate(AFTER_SURVEY_QUESTIONS):
            ans = st.radio(f"Q{i+1}: {q}", [1,2,3,4,5], index=2, format_func=lambda x: ["非常不同意", "不同意", "一般", "同意", "非常同意"][x-1])
            answers.append(ans)
        if st.button("提交并结束实验", use_container_width=True, type="primary"):
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
        st.title("🎊 实验结束，感谢你的参与！")
        st.info("你的数据已安全提交，本次体验将帮助我们更好地理解家庭教育中的沟通模式")
        st.balloons()

if __name__ == "__main__":
    main()
