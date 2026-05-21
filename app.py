import streamlit as st
import json
import random
import pandas as pd
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt

# 页面基础配置
st.set_page_config(page_title="家庭教育视角互换实验系统", layout="wide", page_icon="👨‍👩‍👧")
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei"]
plt.rcParams["axes.unicode_minus"] = False

# 全局样式美化
st.markdown("""
<style>
.main {background-color: #f8f9fa; padding: 1rem;}
.stButton>button {border-radius: 6px; padding: 6px 12px;}
.block-container {max-width: 1200px; margin: 0 auto;}
</style>
""", unsafe_allow_html=True)

# 数据库初始化
def init_db():
    conn = sqlite3.connect('edu_experiment.db', check_same_thread=False)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS user_submit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exp_id TEXT NOT NULL,
        judge_style TEXT,
        pre_ans TEXT,
        game_log TEXT,
        post_ans TEXT,
        submit_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    return conn, cur

conn, cur = init_db()

# 常量定义
STYLE_DICT = {"strict":"专制型", "balanced":"权威型", "gentle":"放任型"}
BEHAVE_NAME = {"homework":"认真做题","rest":"休息放松","distract":"走神贪玩","cant_solve":"解题受阻"}

# 问卷题库
PRE_QUEST_LIST = [
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
    ("孩子开小差我只会简单提醒，不强制约束", "gentle"),
    ("我只陪伴孩子写作业，不强制进度和书写质量", "gentle"),
    ("孩子不会的题我不批评，也不主动督促求助", "gentle"),
    ("孩子长期拖延我也不严厉管束，仅口头提醒", "gentle"),
    ("学习习惯不佳仅随口提及，不会刻意纠正", "gentle")
]

POST_QUEST_LIST = [
    "本次模拟中，我能顺利代入孩子视角感受内心状态",
    "游戏互动场景和现实家庭辅导情况贴合度较高",
    "体验同款教养方式，真切体会到孩子的情绪感受",
    "明显察觉教养态度直接影响孩子情绪与学习状态",
    "体验帮助我重新审视自身日常教育沟通方式",
    "意识到不当教育行为会产生负面亲子相处影响",
    "理解有边界共情式教育的优势与实际合理性",
    "本次体验有效完成家庭教育换位思考自我反思",
    "体验后愿意主动调整自身教养沟通处事方式",
    "沉浸式模拟对亲子共情教育具备实际参考价值"
]

# 数据存储函数
def save_data(exp_id, style, pre_data, game_data, post_data):
    cur.execute('INSERT INTO user_submit (exp_id, judge_style, pre_ans, game_log, post_ans) VALUES (?,?,?,?,?)',
                (exp_id, style, json.dumps(pre_data), json.dumps(game_data), json.dumps(post_data)))
    conn.commit()

# 初始化会话状态
if "curr_page" not in st.session_state:
    st.session_state.curr_page = "pre_question"
if "user_info" not in st.session_state:
    st.session_state.user_info = {}

# 侧边导航栏
with st.sidebar:
    st.title("📑 系统导航")
    menu = st.radio("功能菜单", ["参与实验", "数据管理", "统计分析"])

# 1. 参与实验模块
if menu == "参与实验":
    if st.session_state.curr_page == "pre_question":
        st.header("👨‍👩‍👧 家庭教育前置测评问卷")
        exp_num = st.text_input("填写个人实验编号", placeholder="例：S001")
        if not exp_num:
            st.warning("请先填写实验编号方可作答")
        else:
            st.session_state.user_info["exp_id"] = exp_num
            pre_result = []
            for idx, (quest, _) in enumerate(PRE_QUEST_LIST, 1):
                score = st.radio(f"{idx}. {quest}", [1,2,3,4],
                                format_func=lambda x:["非常不同意","不同意","一般","同意"][x-1])
                pre_result.append(score)
            if st.button("提交问卷，进入模拟场景", type="primary", use_container_width=True):
                # 风格判定
                score_strict = sum(pre_result[:5])
                score_balance = sum(pre_result[5:10])
                score_gentle = sum(pre_result[10:])
                max_score = max(score_strict, score_balance, score_gentle)
                if max_score == score_strict:
                    final_style = "strict"
                elif max_score == score_balance:
                    final_style = "balanced"
                else:
                    final_style = "gentle"
                st.session_state.user_info["pre_score"] = pre_result
                st.session_state.user_info["user_style"] = final_style
                st.success(f"测评完成，判定教养风格：{STYLE_DICT[final_style]}")
                st.session_state.curr_page = "game_simulation"
                st.rerun()

    elif st.session_state.curr_page == "game_simulation":
        st.header("🎮 亲子教育视角互换模拟")
        user_style = st.session_state.user_info["user_style"]
        st.info(f"当前模拟教养模式：{STYLE_DICT[user_style]}")
        if "game_record" not in st.session_state.user_info:
            st.session_state.user_info["game_record"] = []

        if st.button("触发下一轮互动场景", use_container_width=True):
            act_type = random.choice(list(BEHAVE_NAME.keys()))
            if user_style == "strict":
                feed_back = random.choice(["严厉斥责","勒令专心","批评懈怠态度"])
            elif user_style == "balanced":
                feed_back = random.choice(["安抚情绪引导思考","共同梳理问题","肯定进步再提建议"])
            else:
                feed_back = random.choice(["轻声提醒","放任自主处理","温和劝慰"])
            log_item = {
                "行为": BEHAVE_NAME[act_type],
                "家长反馈": feed_back,
                "发生时间": datetime.now().strftime("%H:%M:%S")
            }
            st.session_state.user_info["game_record"].append(log_item)
            st.subheader("本轮互动详情")
            st.write(f"孩子行为：{log_item['行为']}")
            st.write(f"你的应对方式：{log_item['家长反馈']}")
            st.divider()
            st.subheader("全部互动记录")
            st.dataframe(st.session_state.user_info["game_record"], use_container_width=True)

        if st.button("结束模拟，填写后置问卷", type="primary", use_container_width=True):
            st.session_state.curr_page = "post_question"
            st.rerun()

    elif st.session_state.curr_page == "post_question":
        st.header("📝 体验后置反馈问卷")
        post_result = []
        for idx, quest in enumerate(POST_QUEST_LIST,1):
            score = st.radio(f"{idx}. {quest}", [1,2,3,4,5],
                            format_func=lambda x:["非常不同意","不同意","一般","同意","非常同意"][x-1])
            post_result.append(score)
        if st.button("提交全部实验数据", type="primary", use_container_width=True):
            save_data(
                exp_id=st.session_state.user_info["exp_id"],
                style=STYLE_DICT[st.session_state.user_info["user_style"]],
                pre_data=st.session_state.user_info["pre_score"],
                game_data=st.session_state.user_info["game_record"],
                post_data=post_result
            )
            st.success("✅ 实验数据已成功入库保存！")
            full_data = st.session_state.user_info
            full_data["post_score"] = post_result
            down_json = json.dumps(full_data, ensure_ascii=False, indent=2)
            st.download_button("💾 下载个人实验数据包", down_json,
                               file_name=f"{st.session_state.user_info['exp_id']}_实验数据.json",
                               mime="application/json")
            st.session_state.curr_page = "pre_question"
            st.session_state.user_info = {}

# 2. 数据管理模块
elif menu == "数据管理":
    st.header("📊 全体实验数据管理")
    all_df = pd.read_sql("SELECT id,exp_id,judge_style,submit_time FROM user_submit", conn)
    st.dataframe(all_df, use_container_width=True)

    if not all_df.empty:
        sel_id = st.selectbox("选择编号查看完整明细", all_df["id"].tolist())
        row_data = all_df[all_df["id"]==sel_id].iloc[0]
        st.subheader(f"编号{sel_id}实验详情")
        st.write(f"实验编号：{row_data['exp_id']}")
        st.write(f"判定风格：{row_data['judge_style']}")
        st.write(f"提交时间：{row_data['submit_time']}")

        if st.button("展开完整作答与操作记录"):
            pre_ans = json.loads(row_data["pre_ans"])
            game_log = json.loads(row_data["game_log"])
            post_ans = json.loads(row_data["post_ans"])
            st.json({"前置问卷得分":pre_ans,"游戏互动日志":game_log,"后置问卷得分":post_ans})

        # 批量导出全部数据
        csv_data = pd.read_sql("SELECT * FROM user_submit", conn)
        csv_buf = csv_data.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("📤 导出全部数据CSV文件", csv_buf, file_name="全体实验数据.csv", mime="text/csv")
    else:
        st.info("暂无用户提交的实验数据")

# 3. 统计分析模块
elif menu == "统计分析":
    st.header("📈 实验数据统计分析")
    stat_df = pd.read_sql("SELECT judge_style FROM user_submit", conn)
    if stat_df.empty:
        st.info("暂无数据，完成实验提交后即可生成统计图表")
    else:
        # 风格人数统计
        style_count = stat_df["judge_style"].value_counts()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("教养风格人数分布")
            fig1, ax1 = plt.subplots()
            ax1.pie(style_count.values, labels=style_count.index, autopct="%1.1f%%", startangle=90)
            st.pyplot(fig1)
        with col2:
            st.subheader("风格数量柱状统计")
            fig2, ax2 = plt.subplots()
            style_count.plot.bar(ax=ax2, color=["#ff9999","#66b3ff","#99ff99"])
            ax2.set_ylabel("人数")
            st.pyplot(fig2)

        # 基础统计数值
        st.subheader("基础统计汇总")
        total_num = len(stat_df)
        st.write(f"累计参与实验总人数：{total_num}人")
        for sty, cnt in style_count.items():
            st.write(f"{sty}：{cnt}人")

# 关闭数据库
conn.close()
