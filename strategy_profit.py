import pandas as pd
import numpy as np

@staticmethod
def calculate_slope(series):
    """
    計算數值序列的斜率 (Linear Regression Slope)
    用於判斷 8 季以來的趨勢力道
    """
    if len(series) < 2:
        return 0.0
    y = series.values
    x = np.arange(len(y))
    try:
        slope, _ = np.polyfit(x, y, 1)
        return round(float(slope), 4)
    except:
        return 0.0

def analyze_profit_stage(df_profit, res_growth, logger=None):
    """
    輸入由 data.py 抓回來的近八季資料，計算關鍵獲利指標
    """
    if df_profit.empty or len(df_profit) < 4:
        return {"status": "資料不足 (需至少 4 季以上)"}

    df = df_profit.sort_values('date')
    
    # 1. 取得最新一季數據
    latest_opm = df['OPM'].iloc[-1]
    opm_2 = df['OPM'].iloc[-2]

    latest_gpm = df['GPM'].iloc[-1]
    gpm_2 = df['GPM'].iloc[-2]

    opm_growth = round(((latest_opm - opm_2) / abs(opm_2)) * 100, 2)
    gpm_growth = round(((latest_gpm - gpm_2) / abs(gpm_2)) * 100, 2)

    # 2. 計算近 4 季平均值
    avg_4q_gpm = df['GPM'].tail(4).mean()
    avg_4q_opm = df['OPM'].tail(4).mean()

    row = df.iloc[-1].copy()

    if logger: logger(f"======== 開始分析 ({row['stock_id']}) 獲利資料 ========")


    if logger: logger(f" ({row['stock_id']}) 近4季平均毛利率計算完成: {round(avg_4q_gpm * 100, 1)} %")
    if logger: logger(f" ({row['stock_id']}) 近4季平均營業利益率計算完成: {round(avg_4q_opm * 100, 1)} %")

    # 3. 計算 8 季趨勢斜率 (Slope)
    # 如果資料不足 8 季，則有多少算多少
    
    slope_gpm_8q = calculate_slope(df['GPM'])
    slope_opm_8q = calculate_slope(df['OPM'])

    if logger: logger(f" ({row['stock_id']}) 毛利率趨勢(斜率,8季)計算完成: {slope_gpm_8q} ")
    if logger: logger(f" ({row['stock_id']}) 營業利益率趨勢(斜率,8季)計算完成: {slope_opm_8q} ")

    # 4. 利潤改善幅度 = 最新營業利益率 - 近4季平均營業利益率
    profit_improvement = latest_opm - avg_4q_opm

    if logger: logger(f" ({row['stock_id']}) 利潤改善幅度計算完成: {round(profit_improvement, 4)} ")

    #毛利、營業利益走勢
    if latest_gpm > df['GPM'].iloc[-2] and latest_opm > df['OPM'].iloc[-2]: opm_gpm_trend = "🔥 質變確立｜毛利營益雙升，價量齊揚"
    else: opm_gpm_trend = "⚙️ 效率調整｜獲利指標尚在調整中"

    if logger: logger(f" ({row['stock_id']}) 獲利效率檢核為: {opm_gpm_trend} ")

    #營收與利潤的「四象限矩陣」
    trend = res_growth['趨勢值']
    if trend > 0 and (latest_opm - avg_4q_opm) > 0: four_q = "💎 黃金擴張｜價量齊揚，具戴維斯雙擊潛力"
    elif trend > 0 and (latest_opm - avg_4q_opm) <= 0: four_q = "⚙️ 虛胖成長｜營收創高但獲利稀釋，小心修正"
    elif trend <= 0 and (latest_opm - avg_4q_opm) > 0: four_q = "🛡️ 效率轉型｜營收縮減但獲利更精實"
    else: four_q = "❌ 全面衰退｜營收獲利雙殺，基本面轉差"


    if logger: logger(f" ({row['stock_id']}) 成長品質矩陣為: {four_q} ")

    #結構性反轉偵測
    if slope_opm_8q > 0 and latest_opm > avg_4q_opm: four_r = "🚀 強勢擴張｜主升段，獲利能力持續墊高"
    elif slope_opm_8q < 0 and latest_opm > avg_4q_opm: four_r = "🔥 結構轉機｜長期趨勢反轉，爆發前夕"
    elif slope_opm_8q > 0 and latest_opm < avg_4q_opm: four_r = "⚠️ 成長疲態｜趨勢向上但短線失速"
    else: four_r = "❌ 趨勢惡化｜獲利能力處於下行軌道"


    if logger: logger(f" ({row['stock_id']}) 利潤率趨勢導航為: {four_r} ")

    #利潤分 (S4)
    max_8q_gpm = df['OPM'].tail(8).max()
    if latest_opm >= max_8q_gpm: profit_score = 100
    elif latest_opm >=0.035: profit_score = 100
    elif latest_opm >=0.033: profit_score = 90
    elif latest_opm >=0.031: profit_score = 80
    elif latest_opm >=0.029: profit_score = 70
    elif latest_opm >=0.027: profit_score = 60
    else: profit_score = 40


    #利潤改善分(S5)
    if profit_improvement >= 0.005: profitImp_score = 100
    elif profit_improvement >= 0.001: profitImp_score = 80
    elif profit_improvement >= -0.001: profitImp_score = 60
    else: profitImp_score = 40


    bonus_gpm = 5 if slope_gpm_8q > 0 else 0
    bonus_opm = 0 if slope_opm_8q > 0 else -5

    total_score = (profit_score * 0.6) + (profitImp_score * 0.4) + bonus_gpm + bonus_opm

    if logger: logger(f" ({row['stock_id']}) 利潤分 (S4): {profit_score}")
    if logger: logger(f" ({row['stock_id']}) 利潤改善分(S5): {profitImp_score}")


    if total_score >= 85: action = "🚀 全力衝刺｜市場瘋狂期，抱緊處理"
    elif total_score >= 75: action = "💎 精選重倉｜轉機確立，加碼最佳窗口"
    elif total_score >= 60: action = "📈 穩定持有｜體質健康，適合中長線"
    elif total_score >= 40: action = "🔄 減碼觀望｜動能轉弱，檢視持股安全性"
    else: action = "❌ 空手避開｜基本面不佳，嚴守停損"

    if logger: logger(f" ({row['stock_id']}) 獲利總分為: {total_score}")
    if logger: logger(f" ({row['stock_id']}) 獲利含金量總評: {action}")

    if logger: logger(f"======== 結束分析 ({row['stock_id']}) 獲利資料 ========")

    result = {
        "latest_gpm": round(latest_gpm, 3),
        "gpm_growth": gpm_growth,
        "latest_opm": round(latest_opm, 3),
        "opm_growth": opm_growth,
        "avg_4q_gpm": round(avg_4q_gpm, 3),
        "avg_4q_opm": round(avg_4q_opm, 3),
        "slope_gpm_8q": slope_gpm_8q,
        "slope_opm_8q": slope_opm_8q,
        "profit_improvement": round(profit_improvement, 2),
        "opm_gpm_trend": opm_gpm_trend,
        "four_q": four_q,
        "four_r": four_r,
        "profit_score": profit_score,
        "profitImp_score": profitImp_score,
        "total_score": total_score,
        "action": action
    }

    return result