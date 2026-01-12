import pandas as pd
import numpy as np

def analyze_shareholder_return(df_annual,res_growth ,res_profit,logger=None):
    """
    分析年度 ROE 與 EPS 表現
    """

    # 近4年平均ROE
    df_annual['4M_ROE'] = df_annual['ROE'].rolling(4).mean().round(4)
    row = df_annual.iloc[-1].copy()
    Mfour_ROE = row['4M_ROE']

    if logger: logger(f" ({row['stock_id']}) 近4年平均ROE: {round(Mfour_ROE * 100, 2)} %")
    
    # 3年EPS複合成長率 (CAGR)
    new_eps = df_annual.iloc[-1]['EPS']
    old_eps = df_annual.iloc[-4]['EPS']
    if old_eps > 0 and new_eps > 0:
        growth_eps = (new_eps / old_eps) ** (1/3) - 1
    else:
        growth_eps = 0  # 或給予一個預設值
    
    if logger: logger(f" ({row['stock_id']}) 3年EPS複合成長率 (CAGR): {round(growth_eps * 100, 2)} %")


    # ROE 水平分(S6a)
    m_ROE = df_annual.iloc[-1]['4M_ROE']
    max_4y_roe = df_annual['ROE'].tail(4).max()
    roe = df_annual.iloc[-1]['ROE']


    if roe >= max_4y_roe: roe_score = 100
    elif m_ROE >= 0.15: roe_score = 100
    elif m_ROE >= 0.12: roe_score = 90
    elif m_ROE >= 0.1: roe_score = 80
    elif m_ROE >= 0.08: roe_score = 60
    else: roe_score = 40


    if logger: logger(f" ({row['stock_id']}) ROE 水平分(S6a): {roe_score} ")

    # ROE 成長分(S6b)
    roe_1 = df_annual.iloc[-1]['ROE']
    roe_2 = df_annual.iloc[-2]['ROE']
    roe_3 = df_annual.iloc[-3]['ROE']
    roe_4 = df_annual.iloc[-4]['ROE']

    avg_roe_gpm = df_annual['ROE'].tail(4).mean()
    roe_growth = round(((roe_1 - roe_2) / abs(roe_2)) * 100, 2)


    eps_1 = df_annual.iloc[-1]['EPS']
    eps_2 = df_annual.iloc[-2]['EPS']
    eps_growth = round(((eps_1 - eps_2) / abs(eps_2)) * 100, 2)


    if roe_1 > roe_2 and eps_1 < eps_2: roe_groth_score = 40
    elif roe_1 > roe_2 and roe_2 > roe_3 and roe_3 > roe_4: roe_groth_score = 100
    elif roe_1 > avg_roe_gpm: roe_groth_score = 80
    elif roe_1 >= roe_4: roe_groth_score = 60
    else: roe_groth_score = 40


    if logger: logger(f" ({row['stock_id']}) ROE 成長分(S6b): {roe_groth_score} ")

    # EPS 成長動能 (S7)
    if old_eps <= 0 and new_eps > 0: eps_groth_score = 100
    elif old_eps <= 0 and new_eps <= 0: eps_groth_score = 20
    elif growth_eps >= 0.2 : eps_groth_score = 100
    elif growth_eps >= 0.12: eps_groth_score = 80
    elif growth_eps >= 0.05: eps_groth_score = 60
    elif growth_eps >= 0: eps_groth_score = 40
    else: eps_groth_score = 20


    if logger: logger(f" ({row['stock_id']}) EPS 成長動能 (S7): {eps_groth_score} ")

    # 股東報酬與獲利分
    eps_roe_score = ( (roe_score*0.5 + roe_groth_score*0.5) * 0.4 ) + ( eps_groth_score * 0.6 )

    if logger: logger(f" ({row['stock_id']}) 股東報酬分: {eps_roe_score} ")

    #推估eps
    avg_4q_opm = res_profit['avg_4q_opm']
    latest_opm = res_profit['latest_opm']
    next_growth = res_growth['推估下一年度成長率']
    print(next_growth)
    print(new_eps)
    if latest_opm > avg_4q_opm : add_score = 1.05
    else: add_score = 0.95
    next_eps = new_eps * ( 1 + next_growth) * add_score

    if logger: logger(f" ({row['stock_id']}) 推估下一年度 EPS: {round(next_eps,2)} ")


    #獲利轉化效率偵測
    trend = res_growth['趨勢值']
    if eps_groth_score >= 80 and latest_opm > avg_4q_opm: return_txt = "🔥 高質量擴張｜規模經濟顯著，獲利增速 > 營收增速"
    elif trend > 0 and latest_opm > avg_4q_opm: return_txt = "💎 效率提升｜利潤率隨營收同步成長"
    else: return_txt = "⚖️ 穩定擴張｜一般性業務擴張"

    if logger: logger(f" ({row['stock_id']}) 規模經濟效應: {return_txt} ")


    #Master Score 最終總評
    growth_score = res_growth['成長總分']
    profit_score = res_profit['total_score']

    masterScore = growth_score * 0.3 + profit_score * 0.3 + eps_roe_score * 0.4

    #最終總評
    if masterScore >=90: final_txt = "🏆 王者姿態｜完美風暴，營收獲利與ROE三箭齊發，頂級標的，估值上限打開。"
    elif masterScore >=80 and growth_score >=80 and profit_score >=80 and eps_roe_score >= 60: final_txt = "💎 實質爆發｜EPS與ROE推動的主升段，營收雖非最猛，但賺錢效率極高，股價含金量最高。"
    elif masterScore >=80 and growth_score >=90 and profit_score < 70: final_txt = "⚠️ 過熱警示｜虛胖型飆股，營收極強推升總分，但獲利品質未跟上，提防營收不如預期時的回馬槍。"
    elif masterScore >=75 and res_profit['profit_improvement'] >0.001 and profit_score > growth_score: final_txt = "🔥 結構轉機｜質變優於量變，獲利結構大幅優化(如轉型成功)，最具潛力的低檔佈局點。"
    elif masterScore >=75 and growth_score>profit_score and trend >0.1: final_txt = "🚀 營收擴張｜攻城掠地期，正處搶市佔率的高速成長階段，獲利雖持平但動能強勁，順勢操作。"
    elif masterScore >=60 and profit_score>=70 and profit_score > growth_score and growth_score < 60: final_txt = "🛡️ 防禦價值｜成熟穩健股，營收動能放緩，但獲利與配息優異，下檔有撐，適合存股。"
    elif masterScore >=60 and profit_score >= 60: final_txt =  "📈【穩健成長】獲利支撐：營收與獲利表現均衡，雖無猛烈爆發力，但趨勢向上，適合波段持有。"
    elif masterScore >=60 and res_profit['profit_improvement'] <0 and trend <0: final_txt = "📉 動能衰退｜觀察名單，總分尚可但營收毛利雙降，建議等待基本面止穩訊號。"
    elif masterScore < 40: final_txt = "❌ 地雷警示｜基本面潰散，營收獲利雙殺，切勿僅看股價便宜就進場接刀，建議空手。"
    else: final_txt = "⚖️ 中性盤整｜體質普通，各項指標無顯著亮點，股價隨大盤波動，需等待新催化劑。"

    return {
        "最新ROE": roe_1,
        "ROE成長": roe_growth,
        "最新EPS": eps_1,
        "EPS成長": eps_growth,
        "近四年平均ROE": Mfour_ROE,
        "三年EPS複合成長率": growth_eps,
        "獲利轉化效率偵測": return_txt,
        "推估eps": next_eps,
        "股東報酬與獲利分": eps_roe_score,
        "MasterScore": masterScore,
        "最終總評": final_txt
    }