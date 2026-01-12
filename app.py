import streamlit as st
import pandas as pd
import time
import requests
import json 
from datetime import datetime
from data import StockData
from strategy_growth import analyze_growth_stage
from strategy_profit import analyze_profit_stage 
from strategy_shareholder import analyze_shareholder_return
from strategy_valuation import analyze_valuation_stage

st.set_page_config(
    page_title="台股基本面戰情室",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .metric-card {
        background-color: #f9f9f9;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    /* 自定義進度條顏色 */
    .stProgress > div > div > div > div {
        background-color: #2E86C1;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_stock_map():
    try:
        with open('stock_map.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

stock_map = load_stock_map()

@st.dialog("⚠️ 股票篩選警示")
def show_alert_dialog(stock_id, msg, is_fatal=False):
    st.write(f"**偵測到股票代號：{stock_id}**")
    if is_fatal:
        st.error(msg)
        st.caption("系統將自動跳過此標的，不進行分析。")
    else:
        st.warning(msg)
        st.caption("系統將繼續嘗試分析，但結果僅供參考。")


def call_gemini_api(stock_res, api_key):
    if not api_key:
        return "⚠️ 請先在側邊欄輸入 Gemini AI Token。"
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
    
    prompt = f"""
        ## 1. 核心總分看板 (Master Dashboard)
        # 對應 Excel: J46 (分數) & J46評語
        Total_Score: {stock_res['MasterScore']}
        Master_Evaluation: "{stock_res['最終總評']}"
        # 範例: "💎【實質獲利爆發】績優權值/成長股：營收與獲利雙引擎驅動..."

        Sub_Scores:
        - Growth_Score (成長分): {stock_res['成長總分']}
        - Profit_Score (獲利分): {stock_res['total_score']}
        - Return_Score (報酬分): {stock_res['股東報酬與獲利分']}

        ---
        ## 2. 營收動能細節 (Momentum Deep Dive)
        # 關鍵：這裡的評語已經包含了「高成長保護機制」的判斷
        Trend_Diagnosis (趨勢診斷 G18):
        - Value: {stock_res['趨勢值']}
        - Status: "{stock_res['趨勢txt']}"  # 範例: "💎 高檔盤整 (成長確立)"
        
        Short_Term_Momentum (短線動能 G19):
        - Value: {stock_res['爆發值']}%
        - Status: "{stock_res['爆發力txt']}"  # 範例: "⚖️ 高原調整 (動能仍強)"

        Momentum_Cycle (動能週期定位): "{stock_res['狀態診斷']}"
        # 範例: "🔄 趨勢收斂 (高成長持續)" 或 "🔥 低檔轉強"

        ---
        ## 3. 獲利結構細節 (Profit Quality Deep Dive)
        # 關鍵：這裡包含「創8季新高」與「矩陣定位」
        Quality_Matrix (成長品質矩陣): "{stock_res['four_q']}"
        # 範例: "💎 黃金擴張 (價量齊揚)" 或 "⚙️ 虛胖成長"

        Profit_Trend_Direction (利潤趨勢): "{stock_res['four_r']}"
        # 範例: "🔥 結構轉機 (反轉確立)"

        Improvement_Rate (利潤改善幅度): {stock_res['profit_improvement']}%

        ---
        ## 4. 股東回報細節 (Shareholder Return)
        # 關鍵：包含 EPS 轉虧為盈與 ROE 自我超越判斷
        ROE_Analysis:
        - Status: "{stock_res['獲利轉化效率偵測']}"


        ## 5. 估值與目標價模組 (Valuation & Price Targets)
        # 核心：AI 需根據目前股價相對於便宜/昂貴價的位置，判斷安全邊際
        Price_Data:
        Current_Price: {stock_res['目前股價']}
        Est_Next_Year_EPS: {stock_res['推估eps']}

        Valuation_Levels:
        Cheap_Price (便宜價 = (最低本益比) * 推估明年EPS): {stock_res['便宜價']}
        Fair_Price (合理價 = (平均本益比) * 推估明年EPS): {stock_res['合理價']}
        Expensive_Price (昂貴價 = (最高本益比) * 推估明年EPS): {stock_res['昂貴價']}
        Target_Price_Net_Value (淨值目標價 = 淨值 × (1 + (最新ROE - 美債10年殖利率)) ^ 10年): {stock_res['目標價']}

        # 預先計算的估值狀態
        Valuation_Status: "{stock_res['價值評估']}"

        ---
        ## [給 AI 的指令 Instruction]
        你是一位資深台股分析師，請根據【{stock_res['股票']}】上述數據撰寫【個股診斷報告】。    
        **分析邏輯準則：**
        1. **[總調定性]**：優先引用 `Master_Evaluation`。

        2. **[拆解動能]**：
        - 觀察 `Trend_Diagnosis` 與 `Short_Term_Momentum`。

        3. **[檢視獲利品質] (最重要)**：
        - 引用 `Quality_Matrix`。若是「虛胖成長」，語氣需嚴厲警示。

        4. **[操作建議] (Actionable Advice)**：
        - 根據 `Current_Price` 與 `Cheap/Fair/Expensive/Target_Price_Net_Value` 的距離，給出具體價位建議。

        請用專業、客觀但犀利的口吻輸出，字數控制在 500 字以內。
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "AI 無回應")
        else:
            return f"❌ API 錯誤: {response.status_code}"
    except Exception as e:
        return f"❌ 連線失敗: {str(e)}"

st.title("📊 股票多維度基本面分析系統")

if 'analysis_results' not in st.session_state:
    st.session_state['analysis_results'] = None
if 'process_logs' not in st.session_state:
    st.session_state['process_logs'] = []

def add_log(msg):
    """將訊息加入日誌列表"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state['process_logs'].append(f"[{timestamp}] {msg}")

def render_kpi_card(title, value, delta=None, prefix="", suffix=""):
    """自定義 KPI 卡片樣式"""
    st.metric(label=title, value=f"{prefix}{value}{suffix}", delta=delta)


with st.sidebar:
    st.title("🎛️ 戰情室控制台")
    
    with st.expander("🔑 金鑰設定", expanded=False):
        finmind_token = st.text_input("FinMind Token", type="password", help="請輸入您的 FinMind API Token 以獲取數據")
        gemini_token = st.text_input("Gemini AI Token", type="password", help="請輸入 Google Gemini API Key 以啟用 AI 分析")

    st.divider()
    stock_input = st.text_area("輸入股票代號 (用逗號隔開)", value="2317")

    st.divider()

    start_btn = st.button("🚀 開始分析", width='stretch')

    with st.popover("ℹ️ 使用說明"):
        st.write("1. 適合的產業為「獲利與營收高度正相關」")
        st.write("如電子代工與零組件、半導體產業、軟體與 SaaS 服務")
        st.write("2. 不適用：景氣循環股、金融、營建")
        st.write("⚠️ 注意：單次分析限制最多 5 檔股票。")

    st.divider()
    st.write("🎵 **戰情室 BGM**")
    audio_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
    st.audio(audio_url, start_time=0)

if start_btn:
    stock_list = [s.strip() for s in stock_input.split(',')]

    if len(stock_list) > 5:
        st.error(f"❌ 偵測到 {len(stock_list)} 檔股票。為維護系統穩定，單次分析上限為 5 檔，請減少數量後再重試。")
        st.stop()
    
    results = []
    st.session_state['process_logs'] = [] 

    data_loader = StockData(finmind_token)
    run_timestamp = int(time.time()) 
    
    add_log(f"🚀 啟動分析任務，目標個股：{stock_list}")

    with st.status("🧬 系統正在執行深度計算...", expanded=True) as status:
        for i, stock_id in enumerate(stock_list):
            st.write(f"#### 🔍 處理個股：{stock_id}")
            add_log(f"🔍 處理個股：{stock_id}")

            stock_whitelist_info = stock_map.get(stock_id)

            if stock_whitelist_info:
                # 代號存在於 JSON 中
                stock_name = stock_whitelist_info.get("name", "未知股票")
                industry = stock_whitelist_info.get("industry", "未知產業")
                recommend = stock_whitelist_info.get("recommend", True)
                note = stock_whitelist_info.get("note", "")
                
                if not recommend:
                    warn_msg = f"此股票屬於【{industry}】，非「獲利與營收高度正相關」產業，不適用本模型。\n({note})"
                    show_alert_dialog(stock_id, warn_msg, is_fatal=True)
                    
                    add_log(f"⚠️ {stock_id} 跳過：{warn_msg}")
                    st.warning(warn_msg)
                    st.divider()
                    continue 
            else:
                warn_msg = "此股票未列入台股前 150 大權值股清單，基本面數據可能較不完整或波動較大。"
                show_alert_dialog(stock_id, warn_msg, is_fatal=False)
                
                stock_info = data_loader.get_stock_info(stock_id)
                if isinstance(stock_info, dict):
                    stock_name = stock_info.get("name", "未知股票")
                    industry = stock_info.get("industry", "未知產業")
                else:
                    stock_name = str(stock_info)
                    industry = "未知產業"          

            try:
                add_log(f"📡 正在獲取 {stock_id} 原始數據...")
                stock_info = data_loader.get_stock_info(stock_id)

                if stock_info == "未知股票":
                    err_msg = f"⚠️ 查無股票代號 {stock_id}。"
                    st.warning(err_msg)
                    add_log(err_msg)
                    continue 

                if isinstance(stock_info, dict):
                    stock_name = stock_info.get("name", stock_id)
                    industry = stock_info.get("industry", "未知產業")
                else:
                    stock_name = stock_info
                    industry = "未知產業"


                df_rev = data_loader.get_revenue(stock_id)

                if df_rev.empty:
                    err_msg = f"⚠️  {stock_id}該股營收數據不足。"
                    st.warning(err_msg)
                    add_log(err_msg)
                    continue 

                df_rev = df_rev[df_rev['date'] <= datetime.now()]
                df_profit = data_loader.get_profitability(stock_id)
                time.sleep(0.2) 


                add_log(f"📈 執行策略 A：成長性診斷...")
                res_growth = analyze_growth_stage(df_rev, logger=add_log)
                if not isinstance(res_growth, dict): res_growth = {}

                add_log(f"💰 執行策略 B：獲利性診斷...")

                res_profit = analyze_profit_stage(df_profit, res_growth, logger=add_log)
                if not isinstance(res_profit, dict): res_profit = {}
        
                add_log(f"👑 執行策略 C：報酬能力診斷...")
                df_annual = data_loader.get_shareholder_return(stock_id)
                res_sh = analyze_shareholder_return(df_annual, res_growth, res_profit, logger=add_log)
                
                if not isinstance(res_sh, dict): res_sh = {}

                current_price = data_loader.get_latest_price(stock_id)
                ten_american = data_loader.get_us_bond_yield()
                df_val = data_loader.get_valuation_history(stock_id)
                res_val = analyze_valuation_stage(df_val, current_price, ten_american,res_sh['推估eps'],df_annual, logger=add_log)
                
                df_news = data_loader.get_stock_news(stock_id, days=90, logger=add_log)

                combined_res = {**res_growth, **res_profit, **res_sh, **res_val}
                combined_res['股票'] = f"{stock_name} ({stock_id})"
                combined_res['股票代號'] = stock_id
                combined_res['股票名稱'] = stock_name
                combined_res['產業別'] = industry
                combined_res['ui_key'] = f"{stock_id}_{run_timestamp}_{i}"
                combined_res['news']= df_news


                results.append(combined_res)
                add_log(f"✅ {stock_id} 分析完成，得分：{combined_res.get('成長總分', 'N/A')}")
                st.write(f"✅ {stock_id} 分析完成")
      
            except Exception as e:
                err_msg = f"❌ {stock_id} 分析失敗: {str(e)}"
                st.error(err_msg)
                add_log(err_msg)

        status.update(label="✨ 所有分析完畢！", state="complete", expanded=False)
        st.session_state['analysis_results'] = results
        add_log("🏁 任務結束。")

if st.session_state['analysis_results']:
    results = st.session_state['analysis_results']
    df_res = pd.DataFrame(results)
    

    # 計算公式：(目標價 / 目前股價 - 1) * 100
    df_res['保底潛在空間'] = ((df_res['目標價'] / df_res['目前股價'] - 1) * 100).map(lambda x: f"{x:+.1f}%")

    st.subheader("🏆 綜合評分排行榜")
    cols = ['股票','MasterScore', '目前股價', '目標價', '保底潛在空間','便宜價','合理價','昂貴價','最終總評']
    rename_map = {'MasterScore': '綜合評分','最終總評': '分析評語','目標價': '實力保底價'}
    existing_cols = [c for c in cols if c in df_res.columns]
    
    st.dataframe(
        df_res[existing_cols].rename(columns=rename_map).set_index('股票').sort_values('實力保底價', ascending=False), 
        use_container_width=True, height=250
    )

    st.download_button("📥 匯出分析報告", df_res.to_csv().encode('utf-8-sig'), "report.csv", "text/csv")
    st.divider()

    st.subheader("🔍 個股深度診斷")
    
    success_ids = [d.get('股票代號') for d in results]
    
    if success_ids:
        selected_id = st.selectbox(
            "請選擇要深入分析的股票：", 
            success_ids, 
            format_func=lambda x: f"{x} ({next((d['股票名稱'] for d in results if d.get('股票代號') == x), '未分析')})"
        )
        res = next((d for d in results if d.get('股票代號') == selected_id), None)
        
        if res:

            with st.container(border=False):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.title(res['股票'])
                    st.caption(f"產業別：{res['產業別']} | 資料日期：{datetime.now().strftime('%Y-%m-%d')}")

                with c2:
                    avg_score = int((res.get('MasterScore', 0)))
                    score_color = "green" if avg_score >= 80 else "orange"
                    st.markdown(f"""
                        <div style="border: 2px solid {score_color}; border-radius: 10px; padding: 10px; text-align: center;">
                            <h1 style="margin:0; color:{score_color};">{avg_score} 分</h1>
                            <small>綜合評分</small>
                        </div>
                    """, unsafe_allow_html=True)

                st.info(f"Master Score 最終總評：{res.get('最終總評', '無特定建議')}")

            col1, col2, col3, col4, col5 = st.columns(5)
            roe = round(res.get('最新ROE') * 100, 2)
            eps = round(res.get('最新EPS'), 2)
            gpm = round(res.get('latest_gpm') * 100, 2)
            opm = round(res.get('latest_opm') * 100, 2)
            gro = round(res.get('最新單月營收年增') * 100, 2)


            with col1:
                render_kpi_card("單月營收年增", gro,  f"{res.get('營收年增成長')} %", suffix="%")
            with col2:
                render_kpi_card("GPM (季度)", gpm, f"{res.get('gpm_growth')} %", suffix="%")
            with col3:
                render_kpi_card("OPM (季度)", opm, f"{res.get('opm_growth')} %", suffix="%")
            with col4:
                render_kpi_card("ROE (年度)", roe, f"{res.get('ROE成長')} %", suffix="%")
            with col5:
                render_kpi_card("EPS (年度)", eps, f"{res.get('EPS成長')} %")
            st.write("")


            tab_main, tab_profit, tab_val, tab_news, tab_ai = st.tabs([
                "🚀 成長動能", "🤝 獲利結構/股東報酬", "💰 估值與目標價", "📰 重大新聞", "🤖 AI 分析"
            ])

            with tab_main:
                st.subheader("營收動能模組")
                col1, col2 = st.columns(2)
                col1.metric("綜合動能訊號", f"{res.get('狀態診斷', 'N/A')}")
                col2.metric("穩定度評級", f"{res.get('投資含金量', 'N/A')}")

                st.markdown(f"""
                **分析亮點：**
                - 趨勢強度：**{res.get('趨勢txt', '計算中')}**。
                - 短線爆發力：**{res.get('爆發力txt', '計算中')}**。
                - 體質轉型指標：**{res.get('體質txt', '計算中')}**。

                """)
                st.info(f"💡 成長動能總評：{res.get('成長總分建議', '無特定建議')}")

            with tab_profit:
                st.subheader("獲利/報酬體質模組")
                col1, = st.columns(1)
                col2, = st.columns(1)

                col1.metric("成長品質矩陣", f"{res.get('four_q', 'N/A')}")
                col2.metric("利潤率趨勢導航", f"{res.get('four_r', 'N/A')}")

                st.markdown(f"""                 
                **分析亮點：** 
                - 獲利效率檢核：**{res.get('opm_gpm_trend', '計算中')}**。
                - 規模經濟效應：**{res.get('獲利轉化效率偵測', '計算中')}**。
                """)
                st.info(f"💡 獲利含金量總評：{res.get('action', '無特定建議')}")

            with tab_val:
                eps_next = round(res.get('推估eps'), 2)
                st.subheader(f"本益比估值法 (推估明年 EPS: {eps_next}) ex.市場的期待值")
                curr_p = res.get('目前股價', 0)

                def get_price_card_html(title, price, diff, theme):

                    bg, border, text, icon = theme
                    diff_sign = "+" if diff > 0 else ""
                    
                    return f"""
                    <div style="
                        background-color: {bg};
                        border: 1px solid {border};
                        border-radius: 12px;
                        padding: 20px;
                        text-align: center;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                        height: 100%;
                    ">
                        <div style="color: {text}; font-weight: bold; font-size: 1.1em; margin-bottom: 8px;">
                            {icon} {title}
                        </div>
                        <div style="color: #1f2937; font-size: 2em; font-weight: 800; margin: 0;">
                            ${price}
                        </div>
                        <div style="margin-top: 8px; font-size: 0.9em; color: #4b5563;">
                            距目前價：<span style="color: {text}; font-weight: 600;">{diff_sign}{diff}%</span>
                        </div>
                    </div>
                    """
                
                c_low, c_fair, c_high = st.columns(3)
                with c_low:
                    p_cheap = res.get('便宜價', 0)
                    diff = round(((curr_p - p_cheap) / p_cheap) * 100, 1) if p_cheap > 0 else 0

                    st.markdown(get_price_card_html(
                        "便宜價", p_cheap, diff, 
                        ("#F0FDF4", "#BBF7D0", "#166534", "💎")
                    ), unsafe_allow_html=True)

                with c_fair:
                    p_fair = res.get('合理價', 0)
                    diff_fair = round(((curr_p - p_fair) / p_fair) * 100, 1) if p_fair > 0 else 0

                    st.markdown(get_price_card_html(
                        "合理價", p_fair, diff_fair, 
                        ("#FFF7ED", "#FED7AA", "#9A3412", "⚖️")
                    ), unsafe_allow_html=True)

                with c_high:
                    p_exp = res.get('昂貴價', 0)
                    diff_exp = round(((curr_p - p_exp) / p_exp) * 100, 1) if p_exp > 0 else 0

                    st.markdown(get_price_card_html(
                        "昂貴價", p_exp, diff_exp, 
                        ("#FEF2F2", "#FECACA", "#991B1B", "⚠️")
                    ), unsafe_allow_html=True)

                st.write("")

                col_long, col_hist = st.columns(2)
                
                with col_long:
                    with st.container(border=True):
                        st.write("🔍 **長期內在價值推估 ex.公司的真實潛力價**")
                        iv = res.get('目標價', 0)
                        st.title(f"${iv}")
                        st.caption(f"模型：淨值 × (1 + (ROE - 美債 {res.get('美債殖利率')}%)) ^ 10年")
                        if iv > curr_p:
                            st.success(f"📈 內在價值高於目前股價，潛在空間：{round((iv/curr_p-1)*100, 1)}%")
                        else:
                            st.warning("📉 目前股價已透支長期內在價值。")

                with col_hist:
                    with st.container(border=True):
                        st.write(" **目前價位**")
                        iv = res.get('目前股價', 0)
                        st.title(f"${iv}")
                        st.caption(datetime.now().strftime('%Y-%m-%d'))
                        st.info(res.get('價值評估'))

            with tab_news:
                    st.subheader("📰 近期新聞")
                    news_df = res.get('news')
                    
                    if news_df is not None and not news_df.empty:

                        news_df = news_df.drop_duplicates(subset=['title']).head(10)
                        
                        for idx, row in news_df.iterrows():
                            with st.container(border=True):
                                c_date, c_content = st.columns([1, 4])

                                date_str = row['date'].strftime('%Y-%m-%d') if pd.notnull(row['date']) else "未知日期"
                                c_date.caption(f"{date_str} | {row.get('source', '')}")
                                

                                title = row.get('title', '無標題')
                                link = row.get('link', '#')
                                c_content.markdown(f"**[{title}]({link})**")
                                
                                if 'description' in row and pd.notnull(row['description']):
                                    desc = str(row['description'])[:100] + "..."
                                    c_content.caption(desc)
                    else:
                        st.info("📭 查無近期相關新聞。")

            with tab_ai:
                st.markdown("### 🤖 Gemini AI 深度投資解析")
                st.write("點擊下方按鈕，讓 AI 為您即時解讀財報與市場情緒。")
                
                if st.button("✨ 啟動 AI 診斷", type="primary", key=f"ai_{res['ui_key']}"):
                    if not gemini_token:
                        st.error("⚠️ 請先在側邊欄輸入 Gemini Token")
                    else:
                        with st.spinner("AI 正在思考中..."):
                            report = call_gemini_api(res, gemini_token)
                            st.markdown("---")
                            st.markdown(report)

            st.markdown("---")
            st.subheader("🛡️ 投資護城河與風險評估")
            with st.container(border=True):
                rc1, rc2, rc3 = st.columns(3)
                
                s_growth = res.get('成長總分', 0)
                s_profit = res.get('total_score', 0)
                s_return = res.get('股東報酬與獲利分', 0)

                with rc1:
                    st.write("**🚀 成長分**")
                    st.progress(min(max(s_growth, 0), 100) / 100)
                    st.caption(f"得分：{s_growth} / 100")
                with rc2:
                    st.write("**💰 獲利分**")
                    st.progress(min(max(s_profit, 0), 100) / 100)
                    st.caption(f"得分：{s_profit} / 100")
                with rc3:
                    st.write("**🤝 報酬分**")
                    st.progress(min(max(s_return, 0), 100) / 100)
                    st.caption(f"得分：{s_return} / 100")

    st.divider()
    with st.expander("⚙️ 系統分析流水線日誌", expanded=False):
        if st.session_state['process_logs']:
            st.code("\n".join(st.session_state['process_logs']), language="text")
            if st.button("🗑️ 清空日誌"):
                st.session_state['process_logs'] = []
                st.rerun()
else:
    st.info("💡 請在左側輸入代號並點擊「開始分析」以查看結果。")