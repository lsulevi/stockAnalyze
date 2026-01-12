import pandas as pd
import numpy as np

def analyze_valuation_stage(df_val, current_price, us_bond,eps,df_annual, logger=None):
    """
    計算估值相關指標：
    使用縮尾處理 (Winsorization) 來優化歷史本益比區間的準確性，並推算目標價位。
    """
    if df_val.empty: 
        if logger: logger("    [Valuation] ❌ 數據不足，無法進行估價")
        return {}
    
    price_val = 0.0
    if isinstance(current_price, dict):
        price_val = float(current_price.get('close', 0))
    else:
        price_val = float(current_price or 0)

    # 1. 數據初步清洗：排除虧損狀態 (PE <= 0)
    pe_series = df_val[df_val['PER'] > 0]['PER'].copy()
    
    if pe_series.empty:
        if logger: logger("    [Valuation] ⚠️ 無有效正本益比數據，無法計算區間")
        return {}

    # 2. 執行縮尾處理 (Winsorization)
    upper_limit = pe_series.quantile(0.95)
    valid_pe = pe_series.clip(upper=upper_limit)
    
    # 3. 計算統計指標
    pe_max = round(valid_pe.max(), 2)
    pe_min = round(valid_pe.min(), 2)
    pe_avg = round(valid_pe.mean(), 2)
    pe_std = valid_pe.std() 

    # 4. 取得目前數據與推算淨值
    latest_row = df_val.iloc[-1]
    current_pe = round(latest_row['PER'], 2)
    current_pb = latest_row['PBR']
    
    # 反推淨值 (NAV = Price / PBR)
    nav = round(price_val / current_pb, 2) if current_pb > 0 else 0
    
    # 5. 計算評價位階門檻 (使用標準差通道)
    cheap_pe = pe_avg - pe_std
    expensive_pe = pe_avg + pe_std

    valuation_eps = eps
    
    # 6. 【新增】目標價計算邏輯
    # 根據當前股價與當前 PE 反推目前的 TTM EPS
    # 公式：EPS = Price / PE
    derived_eps = price_val / current_pe if current_pe > 0 else 0
    print(valuation_eps)

    # 便宜價 = (平均 PE - 1倍標準差) * EPS
    target_cheap = round(cheap_pe * valuation_eps, 2)
    # 合理價 = 平均 PE * EPS
    target_fair = round(pe_avg * valuation_eps, 2)
    # 昂貴價 = (平均 PE + 1倍標準差) * EPS
    target_expensive = round(expensive_pe * valuation_eps, 2)

    #伯彥估值法
    latest_roe = df_annual['ROE'].iloc[-1]
    max_sustainable_roe = 0.25
    latest_roe = min(latest_roe, max_sustainable_roe)
    us_bond = us_bond / 100
    intrinsic_value = round(nav * (1+ (latest_roe - us_bond))** 10, 2)
    
    if price_val <= target_cheap and price_val < intrinsic_value: price_txt = "💎 絕對低估｜雙重安全邊際 (PE低檔 + 低於內在價值)"
    elif price_val <= target_cheap: price_txt = "📉 歷史低檔｜股價位於本益比下緣，需確認基本面"
    elif price_val <= target_fair and price_val < intrinsic_value: price_txt = "✅ 蓄勢待發｜價格合理且低於長期價值，適合佈局"
    elif price_val <= target_fair: price_txt = "⚖️ 合理區間｜價格反映基本面，隨獲利穩健成長"
    elif price_val <= target_expensive and price_val < intrinsic_value: price_txt = "📈 價值重估｜市場熱度升溫，唯尚未超越長期內在價值"
    elif price_val <= target_expensive: price_txt = "⚠️ 溢價交易｜股價已高於合理區間，需高成長支撐"
    else: price_txt = "🔥 過熱警戒｜股價突破歷史上緣，風險報酬比極低"

    if logger:
        logger(f"    [Valuation] 已完成 95% 縮尾處理，排除極端值干擾")
        logger(f"    [Valuation] 便宜價推估: {target_cheap}, 合理價推估: {target_fair}, 昂貴價推估: {target_expensive}")

    print(pe_max)
    print(pe_min)
    print(pe_avg)

    return {
        "目前股價": price_val,
        "股票目前淨值": nav,
        "目前本益比": current_pe,
        "歷史最高PE": pe_max,
        "歷史最低PE": pe_min,
        "歷史平均PE": pe_avg,
        "便宜價": target_cheap,
        "合理價": target_fair,
        "昂貴價": target_expensive,
        "美債殖利率": us_bond,
        "目標價": intrinsic_value,
        "價值評估": price_txt
    }