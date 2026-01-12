# strategy_growth.py
import pandas as pd
import numpy as np

def analyze_growth_stage(df, logger=None):

    # 確保有足夠資料計算
    if len(df) < 12: return None

    #3M_Avg = 近 3 月平均 YoY
    #6M_Avg = 近 6 月平均 YoY
    #6M_Std = 近 6 月標準差
    #trend = 趨勢診斷
    #trend_score = 趨勢分
    #burst = 爆發力診斷
    #burst_score = 爆發分
    #struct = 體質診斷
    #struct_score = 體質分
    #state_diag = 狀態診斷
    #gold = 投資含金量
    #stable_score = 穩定分
    #total_score = 成長總分
    #action = 成長總分建議
    #next_growth = 推估下一年度成長率
    
    
    # 近 3 月 & 6 月平均 YoY
    df['3M_Avg'] = df['Mon_YoY'].rolling(3).mean().round(3)
    df['6M_Avg'] = df['Mon_YoY'].rolling(6).mean().round(3)
    # 近 6 月標準差
    df['6M_Std'] = df['Mon_YoY'].rolling(6).std().round(3)
    
    # 取最新一筆資料來診斷
    row = df.iloc[-1].copy()

    mon_1 = df.iloc[-1]['Mon_YoY']
    mon_2 = df.iloc[-2]['Mon_YoY']
    mon_growth = round(((mon_1 - mon_2) / abs(mon_2)) * 100, 2)


    if logger: logger(f"======== 開始分析 ({row['stock_id']}) 成長資料 ========")

    if logger: logger(f" ({row['stock_id']}) 取得最新資料月份為: {row['date'].strftime('%Y 年 %m 月')}")
    if logger: logger(f" ({row['stock_id']}) 近3月平均YoY計算完成: {round(row['3M_Avg'] * 100, 1)} %")
    if logger: logger(f" ({row['stock_id']}) 近6月平均YoY計算完成: {round(row['6M_Avg'] * 100, 1)} %")
    if logger: logger(f" ({row['stock_id']}) 近6月標準差計算完成: {round(row['6M_Std'] * 100, 1)} %")

    # 趨勢診斷
    trend = row['Mon_YoY'] - row['6M_Avg']  # 趨勢診斷
    if trend >= 0.5: trend_txt = "100 (⚠️ 爆發過熱｜需注意是否為低基期效應)"
    elif trend >= 0.1: trend_txt = "100 (🚀 極強成長｜營收動能強勁，位居前段班)"
    elif trend >= 0.05 or row['Mon_YoY']  >= 0.2: trend_txt = "80 (安全成長📈 穩健成長｜成長趨勢明確，安全邊際佳)"
    elif trend >= 0: trend_txt = "60 (⚖️ 持穩表現｜營收持平，無顯著衰退)"
    elif trend >= -0.05: trend_txt = "40 (📉 動能放緩｜成長力道減弱，需留意)"
    else: trend_txt = "20 (❌ 高度危險｜營收顯著衰退，建議避開)"

    # 趨勢分
    if trend >= 0.1: trend_score = 100
    elif row['Mon_YoY'] >= 0.2 or trend >= 0.05: trend_score = 80
    elif trend >= 0: trend_score = 60
    elif trend >= -0.05: trend_score = 40
    else: trend_score = 20


    if logger: logger(f" ({row['stock_id']}) 趨勢值計算完成: {round(trend * 100, 1)} %")
    if logger: logger(f" ({row['stock_id']}) 趨勢值診斷為: {trend_txt}")


    #爆發力診斷
    burst = row['3M_Avg'] - row['6M_Avg']
    threshold = row['6M_Std'] / 2 if not np.isnan(row['6M_Std']) else 0
    if burst >= 0.05 and burst > threshold: burst_txt = "100 (🔥 極速噴發｜短線動能極強，注意乖離過大)"
    elif burst >= 0.02 and burst > threshold: burst_txt = "80 (🚀 加速升溫｜動能加溫中，趨勢向上)"
    elif row['Mon_YoY'] >= 0.15 or burst >= -0.02: burst_txt = "60 (⚖️ 動能平穩｜長短線趨勢一致)"
    elif burst >= -0.05: burst_txt = "40 (📉 動能降溫｜短線不如中線，成長趨緩)"
    else: burst_txt = "20 (⚠️ 顯著失速｜短線動能急凍，甚至轉弱)"

 
    #爆發分
    if burst >= 0.05: burst_score = 100
    elif burst >= 0.02: burst_score = 80
    elif row['3M_Avg'] >= 0.15 or burst >= -0.02: burst_score = 60
    elif burst >= -0.05: burst_score = 40
    else: burst_score = 20


    if logger: logger(f" ({row['stock_id']}) 爆發值計算完成: {round(burst * 100, 1)} %")
    if logger: logger(f" ({row['stock_id']}) 爆發值診斷為: {burst_txt}")

    #體質診斷
    struct = row['6M_Avg'] - row['Cum_YoY']   # 體質轉型
    if struct <-0.03 and row['Mon_YoY']>=0.2: struct_txt = "🛡️ 強勢回檔 (基期因素)"
    elif struct >= 0.08: struct_txt = "100 (💎 結構性爆發｜業績結構顯著跳升)"
    elif struct >= 0.03: struct_txt = "80 (✅ 體質優化｜近期表現優於全年平均)"
    elif struct >= -0.03: struct_txt = "60 (🔄 常態表現｜符合年度趨勢)"
    else: struct_txt = "40 (🚩 成長瓶頸｜近期表現低於全年平均)"

    #體質分
    if struct >= 0.08: struct_score = 100
    elif struct >= 0.03: struct_score = 80
    elif row['Mon_YoY'] >= 0.2 or struct >= -0.03: struct_score = 60
    else: struct_score = 40


    if logger: logger(f" ({row['stock_id']}) 體質值計算完成: {round(struct * 100, 1)} %")
    if logger: logger(f" ({row['stock_id']}) 體質值診斷為: {struct_txt}")

    #狀態診斷
    if trend < 0 and row['Mon_YoY'] >= 0.2: state_diag = "🔄 趨勢收斂 (高成長持續)"
    elif trend > 0.25 and trend > (burst * 2): state_diag = "🚩 短線過熱 (防追高)"
    elif trend > burst and burst > struct and struct < 0: state_diag = "🔥 低檔轉強 (轉機初期)"
    elif trend > burst and burst > struct and struct > 0: state_diag = "🚀 全面加速 (主升段)"
    elif trend < burst and trend < 0: state_diag = "⚠️ 動能見頂 (警訊)"
    else: state_diag = "🔄 盤整調整中"

 

    if logger: logger(f" ({row['stock_id']}) 狀態診斷為: {state_diag} %")

    #投資含金量 & 穩定分 (S8)
    risk_base = max(row['6M_Std'], 0.03) 
    gold_ratio = trend / risk_base
    
    if gold_ratio > 1.5: gold_txt = "100 (👑 皇冠級標的)"
    elif gold_ratio > 1: gold_txt = "80 (💎 完美標的)"
    elif gold_ratio > 0.5: gold_txt = "60 (📈 標準成長)"
    elif gold_ratio > 0: gold_txt = "40 🎢 (虛浮成長)"
    elif row['Mon_YoY'] >= 0.2: gold_txt = "60 🛡️ (強勢整理 (高成長))"
    else: gold_txt = "40 ❌ (動能渙散)",

  

    #穩定分
    if gold_ratio >= 1.5: stable_score = 100
    elif gold_ratio >= 1: stable_score = 80
    elif row['Mon_YoY']>= 0.2 or gold_ratio >= 0.5: stable_score = 60
    else: stable_score = 40

    if logger: logger(f" ({row['stock_id']}) 投資含金量診斷為: {gold_txt}")
    
    # === 總分計算 ===
    # J15 = (J11*0.35) + (J12*0.25) + (J13*0.2) + (J14*0.2)
    total_score = (trend_score * 0.35) + (burst_score * 0.25) + (struct_score * 0.20) + (stable_score * 0.20)

    if logger: logger(f" ({row['stock_id']}) 趨勢分 (S1): {trend_score}")
    if logger: logger(f" ({row['stock_id']}) 爆發分 (S2): {burst_score}")
    if logger: logger(f" ({row['stock_id']}) 體質分 (S3): {struct_score}")
    if logger: logger(f" ({row['stock_id']}) 穩定分 (S8): {stable_score}")

    if logger: logger(f" ({row['stock_id']}) 成長總分為: {total_score}")

    # === 成長總分建議 ===
    if total_score >= 90: action = "🚀 強力主升段｜全速前進，獲利噴發期"
    elif total_score >= 80: action = "💎 精選成長股｜機構法人偏好，積極佈局"
    elif total_score >= 70: action = "🔥 轉機確立區｜趨勢向上，分批佈局良機"
    elif total_score >= 50: action = "🔄 盤整蓄勢區｜動能平穩，耐心等待突破"
    elif total_score >= 30: action = "⚠️ 弱勢警告區｜動能失速，建議減少持股"
    else: action = "❌ 危險衰退區｜動能潰散，嚴守空手紀律"

    if logger: logger(f" ({row['stock_id']}) 成長動能總評: {action}")


    #推估下一年度成長率
    next_growth = ((row['Cum_YoY'] * 0.4) + (row['3M_Avg'] * 0.4) + (trend * 0.2))*1.1

    if logger: logger(f" ({row['stock_id']}) 推估下一年度成長率: {round(next_growth * 100, 2)}")
    if logger: logger(f"======== 結束分析 ({row['stock_id']}) 成長資料 ========")

    # 回傳結果字典
    return {
        "最新單月營收年增": mon_1,
        "營收年增成長": mon_growth,
        "日期": row['date'].strftime('%Y-%m'),
        "近三月平均YoY": row['3M_Avg'],
        "近六月平均YoY": row['6M_Avg'],
        "近六月標準差": row['6M_Std'],
        "趨勢值": trend,
        "趨勢txt": trend_txt,
        "趨勢分": trend_score,
        "爆發值": burst,
        "爆發力txt": burst_txt,
        "爆發分": burst_score,
        "體質值": struct,
        "體質txt": struct_txt,
        "體質分": struct_score,
        "狀態診斷": state_diag,
        "投資含金量": gold_txt,
        "穩定分": stable_score,
        "成長總分": total_score,
        "成長總分建議": action,
        "推估下一年度成長率": next_growth,
    }