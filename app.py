import streamlit as st
import json
import random
import requests
from datetime import datetime
import pandas as pd
import sqlite3

# 页面配置
st.set_page_config(page_title="家庭教育视角互换实验", layout="wide", page_icon="👨‍👩‍👧")

# 移动端适配CSS
st.markdown("""
<style>
.main {background-color: #f8f9fa; padding: 1rem;}
.stButton>button {width: 100%; border-radius: 8px; padding: 0.5rem;}
@media (max-width: 768px) {
    .block-container {padding: 1rem;}
}
</style>
""", unsafe_allow_html=True)

# 数据库初始化
conn = sqlite3.connect('family_edu_data.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS submissions
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              experiment_id TEXT,
              real_style TEXT,
              pre_questionnaire TEXT,
              game_records TEXT,
              post_questionnaire TEXT,
              timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

def save_submission(experiment_id, real_style, pre_data, game_data, post_data):
    c.execute("INSERT INTO submissions (experiment_id, real_style, pre_questionnaire, game_records, post_questionnaire) VALUES (?, ?, ?, ?, ?)",
              (experiment_id, real_style, json.dumps(pre_data), json.dumps(game_data), json.dumps(post_data)))
    conn.commit()

# AI配置
USE_LLM = True
LLM_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
LLM_API_KEY = "YOUR_API_KEY" # 这里如果不用可以删掉

# 游戏常量
STYLE_NAMES = {"strict": "专制型", "gentle": "放任型", "balanced": "权威型"}
ACTION_CN = {"homework": "做作业", "rest": "休息", "distract": "开小差", "cant_solve": "题目不会"}

# 问卷题目
PRE_QUESTIONS = [
    ("孩子作业出错时，我会直接严厉批评，很少耐心讲解", "strict"),
    ("辅导作业时，我要求孩子必须完全听从我的安排，不允许反驳", "strict"),
    ("孩子作业拖延或开小差时，我会用强硬方式督促其改正", "strict"),
    ("我对孩子作业质量要求极高，达不到标准就严厉指责", "strict"),
    ("我更注重纠错而非鼓励，认为批评才能进步", "strict"),
    ("孩子作业做得好我会及时表扬，不好时也会先指出再引导", "balanced"),
    ("我会和孩子约定规则，违反了会指出，做到了会表扬", "balanced"),
    ("孩子遇到难题我会先鼓励独立思考，再讲解", "balanced"),
    ("我会先肯定孩子的优点，再指出改进方向", "balanced"),
    ("失误我会先分析原因，再给建议", "balanced"),
    ("孩子开小差我只会简单提醒，不强制", "gentle"),
    ("我只陪伴孩子写作业，不强制进度和质量", "gentle"),
    ("孩子不会的题我不批评，也不强制求助", "gentle"),
    ("孩子长期拖延我也不强制，只口头提醒", "gentle"),
    ("习惯不好我只口头说，不纠正", "gentle")
]

POST_QUESTIONS = [
    "本次模拟中，我能顺利代入孩子视角感受状态",
    "游戏互动场景和现实家庭辅导情况贴合",
    "体验同款教养方式，体会到孩子的内心感受",
    "明显察觉教养态度影响孩子情绪与学习状态",
    "体验帮助我重新审视自身日常教育沟通方式",
    "意识到不当教育行为会产生负面亲子影响",
    "理解有边界共情式教育的优势与合理性",
    "本次体验有效完成家庭教育换位思考反思",
    "体验后愿意调整自身教养沟通方式",
    "沉浸式模拟对亲子共情教育具备参考价值"
]

# 会话状态初始化
if "page" not in st.session_state:
    st.session_state.page = "pre"
if "user_data" not in st.session_state:
    st.session_state.user_data = {}

# 侧边栏：普通用户页面选择
with st.sidebar:
    st.title("📋 功能导航")
    page_mode = st.radio("选择功能", ["参与实验", "数据管理"])

# 1. 参与实验流程
if page_mode == "参与实验":
    if st.session_state.page == "pre":
        st.title("👨‍👩‍👧 家庭教育视角互换实验")
        experiment_id = st.text_input("填写你的实验编号", placeholder="示例：P05")
        if not experiment_id:
            st.warning("请先填写实验编号再开始")
        else:
            st.session_state.user_data["experiment_id"] = experiment_id
            st.subheader("📝 前置教养方式问卷")
            pre_answers = []
            for i, (q, _) in enumerate(PRE_QUESTIONS, 1):
                score = st.radio(f"Q{i}: {q}", [1,2,3,4], format_func=lambda x: ["非常不同意", "不同意", "一般", "同意"][x-1])
                pre_answers.append(score)
            if st.button("提交问卷，开始模拟", use_container_width=True):
                # 计算教养风格
                strict_score = sum(pre_answers[:5])
                balanced_score = sum(pre_answers[5:10])
                gentle_score = sum(pre_answers[10:])
                max_score = max(strict_score, balanced_score, gentle_score)
                if max_score == strict_score:
                    style = "strict"
                elif max_score == balanced_score:
                    style = "balanced"
                else:
                    style = "gentle"
                st.session_state.user_data["pre_answers"] = pre_answers
                st.session_state.user_data["style"] = style
                st.success(f"问卷提交成功！你的教养方式倾向于：{STYLE_NAMES[style]}")
                st.session_state.page = "game"
                st.rerun()

    elif st.session_state.page == "game":
        st.title("🎮 家庭教育视角互换模拟")
        style = st.session_state.user_data["style"]
        st.info(f"当前模拟你的教养方式：{STYLE_NAMES[style]}")
        if "game_records" not in st.session_state.user_data:
            st.session_state.user_data["game_records"] = []
        # 游戏模拟逻辑（简化版）
        if st.button("进行下一步模拟", use_container_width=True):
            actions = ["homework", "rest", "distract", "cant_solve"]
            action = random.choice(actions)
            feedback = ""
            if style == "strict":
                feedback = random.choice(["严厉批评", "强制继续", "指责不用心"])
            elif style == "balanced":
                feedback = random.choice(["先安抚再引导", "一起分析原因", "鼓励后给建议"])
            else:
                feedback = random.choice(["温柔提醒", "陪伴但不干预", "让孩子自己决定"])
            record = {
                "action": ACTION_CN[action],
                "feedback": feedback,
                "time": datetime.now().strftime("%H:%M:%S")
            }
            st.session_state.user_data["game_records"].append(record)
            st.subheader("本次互动")
            st.write(f"孩子行为：{record['action']}")
            st.write(f"你的反馈：{record['feedback']}")
            st.subheader("互动记录")
            st.table(pd.DataFrame(st.session_state.user_data["game_records"]))
        if st.button("结束模拟，填写后置问卷", use_container_width=True, type="primary"):
            st.session_state.page = "post"
            st.rerun()

    elif st.session_state.page == "post":
        st.title("📝 后置体验问卷")
        post_answers = []
        for i, q in enumerate(POST_QUESTIONS, 1):
            score = st.radio(f"Q{i}: {q}", [1,2,3,4,5], format_func=lambda x: ["非常不同意", "不同意", "一般", "同意", "非常同意"][x-1])
            post_answers.append(score)
        if st.button("提交并导出数据", use_container_width=True, type="primary"):
            # 保存到数据库
            save_submission(
                experiment_id=st.session_state.user_data["experiment_id"],
                real_style=STYLE_NAMES[st.session_state.user_data["style"]],
                pre_data=st.session_state.user_data["pre_answers"],
                game_data=st.session_state.user_data["game_records"],
                post_data=post_answers
            )
            st.success("✅ 数据提交完成！管理员可在后台查看")
            # 导出文件
            all_data = {
                "experiment_id": st.session_state.user_data["experiment_id"],
                "style": st.session_state.user_data["style"],
                "pre_answers": st.session_state.user_data["pre_answers"],
                "game_records": st.session_state.user_data["game_records"],
                "post_answers": post_answers
            }
            st.download_button("📥 下载数据文件", json.dumps(all_data, ensure_ascii=False, indent=2),
                               file_name=f"{st.session_state.user_data['experiment_id']}_data.json",
                               mime="application/json")

# 2. 数据管理页面（管理员专用）
elif page_mode == "数据管理":
    st.title("📊 所有提交数据")
    # 从数据库读取数据
    df = pd.read_sql("SELECT * FROM submissions", conn)
    st.dataframe(df[["id", "experiment_id", "real_style", "timestamp"]], use_container_width=True)
    # 查看单条详情
    if len(df) > 0:
        selected_id = st.selectbox("选择提交ID查看详情", df["id"].tolist())
        if selected_id:
            row = df[df["id"] == selected_id].iloc[0]
            st.subheader(f"提交详情 - ID: {selected_id}")
            st.write(f"实验编号：{row['experiment_id']}")
            st.write(f"教养风格：{row['real_style']}")
            st.write(f"提交时间：{row['timestamp']}")
            if st.button("查看完整数据", use_container_width=True):
                st.json({
                    "前置问卷答案": json.loads(row["pre_questionnaire"]),
                    "游戏互动记录": json.loads(row["game_records"]),
                    "后置问卷答案": json.loads(row["post_questionnaire"])
                })
    else:
        st.info("暂无提交数据")

# 关闭数据库连接
conn.close()
