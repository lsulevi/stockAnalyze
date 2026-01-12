# data.py
import pandas as pd
import requests
from datetime import datetime, timedelta
from FinMind.data import DataLoader

class StockData:
    def __init__(self, token):
        self.dl = DataLoader()
        self.dl.token = token

    def get_stock_info(self, stock_id):
        """取得股票名稱"""
        try:
            # 抓取台灣股票基本資料
            df_info = self.dl.taiwan_stock_info()
            # 篩選出對應的代號
            name = df_info[df_info['stock_id'] == stock_id]['stock_name'].values[0]
            industry = df_info[df_info['stock_id'] == stock_id]['industry_category'].values[0]

            return {
                "name": name,
                "industry": industry,
            }
        except:
            return "未知股票"

    def get_revenue(self, stock_id, start_date="2023-01-01"):

        # 1. 抓取資料
        df = self.dl.taiwan_stock_month_revenue(stock_id=stock_id, start_date=start_date)
        
        if df is None or len(df) < 24:
            return pd.DataFrame()
    
        # 2. 清洗日期
        df['date'] = pd.to_datetime(df['revenue_year'].astype(str) + '-' + df['revenue_month'].astype(str) + '-01')
        df = df.sort_values('date')
        
        # 3. 基礎計算 (今年本月營收 - 去年同月營收) / 去年同月營收 = 年增率
        df['Mon_YoY'] = (df['revenue'].pct_change(periods=12)).round(3)
        
        # 累計營收計算
        df['Cum_Rev'] = df.groupby('revenue_year')['revenue'].cumsum()
        #累計年增 
        df['Cum_YoY'] = (df['Cum_Rev'].pct_change(periods=12)).round(3)
        
        return df
    
    def get_profitability(self, stock_id, start_date="2022-01-01"):
        """
        抓取季度損益表並計算毛利率、營業利益率
        """
        try:
            # 1. 抓取綜合損益表資料
            df = self.dl.taiwan_stock_financial_statement(
                stock_id=stock_id, 
                start_date=start_date
            )
            
            if df.empty:
                return pd.DataFrame()

            # 2. 轉置表格
            df_pivot = df.pivot_table(
                index=['date', 'stock_id'], 
                columns='type', 
                values='value'
            ).reset_index()

            # 3. 計算獲利能力指標
            # 毛利率 = 營業毛利 / 營業收入
            if 'GrossProfit' in df_pivot.columns and 'Revenue' in df_pivot.columns:
                df_pivot['GPM'] = (df_pivot['GrossProfit'] / df_pivot['Revenue']).round(4)

            # 營業利益率 = 營業利益 / 營業收入
            if 'OperatingIncome' in df_pivot.columns:
                df_pivot['OPM'] = (df_pivot['OperatingIncome'] / df_pivot['Revenue']).round(4)
            
            # 4. 排序並過濾
            df_pivot['date'] = pd.to_datetime(df_pivot['date'])
            df_pivot = df_pivot.sort_values('date')

            # 5. 回傳近八季資料
            target_cols = ['date', 'stock_id', 'GPM', 'OPM']
            existing_cols = [c for c in target_cols if c in df_pivot.columns]
            
            return df_pivot[existing_cols].tail(8)
            
        except Exception as e:
            print(f"抓取獲利指標時發生錯誤: {e}")
            return pd.DataFrame()
        
    def get_shareholder_return(self, stock_id, start_date="2019-01-01", logger=None):

        try:
            if logger: logger(f"    [Data] 正在從報表手動計算 {stock_id} 股東報酬率...")

            # 損益表
            df = self.dl.taiwan_stock_financial_statement(
                stock_id=stock_id, 
                start_date=start_date
            )
            #資產負債表
            #取EquityAttributableToOwnersOfParent 歸屬於母公司業主之權益合計
            df_bl = self.dl.taiwan_stock_balance_sheet(
                stock_id=stock_id, 
                start_date=start_date
            )

            # 表格轉置
            df_pivot = df.pivot_table(
                index=['date'], 
                columns='type', 
                values='value'
            ).reset_index()

            df_bl_pivot = df_bl.pivot_table(
                index=['date'], 
                columns='type', 
                values='value'
            ).reset_index()

            df_all = pd.merge(df_pivot, df_bl_pivot, on='date', how='outer')
            df_all['date'] = pd.to_datetime(df_all['date'])
            df_all = df_all.sort_values('date')
            df_all['year'] = df_all['date'].dt.year


            # print(f"df_all 欄位清單: {df_all.columns.tolist()}")
            # print(f"2. 筆資料內容 (最新一季):\n{df_all.iloc[-1].to_string()}")
            # print(f"2. 筆資料內容 (最新一季):\n{df_all.iloc[-1]['EquityAttributableToOwnersOfParent_x']}")
  
            #稅後淨利
            ni_col = "EquityAttributableToOwnersOfParent_x"

            #歸屬於母公司業主之權益合計
            eq_col = "EquityAttributableToOwnersOfParent_y"
 
            # --- 年度數據處理邏輯 ---
            annual_list = []
            years = sorted(df_all['year'].unique())
 
            for i, year in enumerate(years):
                year_data = df_all[df_all['year'] == year].copy()
                q_count = len(year_data) # 該年公佈了幾季
                    
                if q_count == 0: continue

                # A. 取得該年「累計」淨利與 EPS (加總單季值)
                raw_ni = year_data[ni_col].sum() if ni_col in year_data.columns else 0
                raw_eps = year_data['EPS'].sum() if 'EPS' in year_data.columns else 0

                #print(raw_ni)

                # B. 年度化推估 (Extrapolation)
                # 1季: *4, 2季: *2, 3季: *4/3, 4季: *1
                factor = 4 / q_count if q_count > 0 else 0
                projected_ni = raw_ni * factor
                projected_eps = raw_eps * factor

                # 取得今年所有已公佈季度的權益清單
                curr_equities = year_data[eq_col].tolist() if eq_col in year_data.columns else [0]
                
                # 找尋去年的 Q4 (最後一季) 權益
                prev_q4_equity = None
                if i > 0:
                    prev_year_data = df_all[df_all['year'] == years[i-1]]
                    if not prev_year_data.empty:
                        # 去年的最後一筆即為 Q4
                        prev_q4_equity = prev_year_data.iloc[-1][eq_col] if eq_col in prev_year_data.columns else None

                # 組成平均點位清單：[去年Q4, 今年Q1, 今年Q2, ...]
                avg_points = []
                if prev_q4_equity is not None:
                    avg_points.append(prev_q4_equity)
                avg_points.extend(curr_equities)

                # 計算平均值
                if len(avg_points) > 0:
                    avg_equity = sum(avg_points) / len(avg_points)
                else:
                    avg_equity = curr_equities[0] if curr_equities else 0

                # D. 計算 ROE
                roe = (projected_ni / avg_equity) if avg_equity != 0 else 0

                # 取得該年最後一季的資料作為記錄
                latest_row = year_data.iloc[-1]

                annual_list.append({
                    'year': year,
                    'stock_id': stock_id,
                    'ROE': roe,
                    'EPS': round(projected_eps, 2),
                    'date': latest_row['date'],
                    'q_count': q_count,
                    'avg_points_used': len(avg_points), # 記錄用了幾個點平均
                    'is_projected': q_count < 4
                })

            annual_data = pd.DataFrame(annual_list)

            print("\n" + "="*20 + f" [ROE 多點平均對帳: {stock_id}] " + "="*20)
            print(f"計算邏輯：(去年Q4 + 今年各季) / 總點數")
            print(annual_data.to_string(index=False))
            print("="*60 + "\n")

            return annual_data
        
        
            #print(len(df_pivot))

            #EquityAttributableToOwnersOfParent 稅後淨利
            #print(f"2. 筆資料內容 (最新一季):\n{df_pivot.iloc[-1].to_string()}")
            #print(f"2. :{df_pivot["EquityAttributableToOwnersOfParent"].iloc[-1]}")



            #print(f"df_pivot 欄位清單: {df_bl_pivot.columns.tolist()}")
            #print(len(df_bl_pivot))
            #print(f"2. 最後一筆資料內容 (最新一季):\n{df_bl_pivot.iloc[-1].to_string()}")


        except Exception as e:
            if logger: logger(f"    [Data] ❌ 手動計算 ROE 失敗: {str(e)}")
            return pd.DataFrame()


    def get_valuation_history(self, stock_id, years=5, logger=None):
        """
        抓取過去 N 年的本益比 (PER) 與 股價淨值比 (PBR)
        資料集：TaiwanStockPER
        """
        try:
            start_date = (datetime.now() - timedelta(days=years*365)).strftime('%Y-%m-%d')
            
            df = self.dl.taiwan_stock_per_pbr(
                stock_id=stock_id, 
                start_date=start_date
            )

            if df.empty: return pd.DataFrame()
            
            cols = ['PER', 'PBR', 'dividend_yield']
            for c in cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce')
            
            df['date'] = pd.to_datetime(df['date'])
            return df.sort_values('date')
            
        except Exception as e:
            if logger: logger(f"    [Data] ❌ 估價數據抓取失敗: {str(e)}")
            return pd.DataFrame()

    def get_latest_price(self, stock_id, logger=None):
        """
        抓取最新收盤價 (TaiwanStockPrice)
        """
        try:

            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
            df = self.dl.taiwan_stock_daily(
                stock_id=stock_id, 
                start_date=start_date
            )
            
            if not df.empty:
                latest = df.iloc[-1]

                return {
                    "date": latest['date'],
                    "close": float(latest['close'])
                }
            return None
        except:
            return None

    def get_us_bond_yield(self, logger=None):
        """
        抓取 10 年期美債殖利率 (USGovernmentBondYield)
        """

        try:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            df = self.dl.get_data(
                dataset="GovernmentBondsYield",
                data_id="United States 10-Year",
                start_date=start_date
            )
                        

            if not df.empty:

                latest_value = float(df.sort_values('date').iloc[-1]['value'])
                print(latest_value)
                return latest_value
            
            
            if logger: logger("    [Data] ⚠️ 無法取得美債數據，使用預設值 4.0%")
            return 4.0
        except:
            return 4.0
        
    def get_stock_news(self, stock_id, days=90, logger=None):
        """
        抓取個股新聞數據
        """
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            if logger: logger(f"📡 正在從 FinMind 獲取 {stock_id} 新聞 (自 {start_date})...")
            
            df = self.dl.taiwan_stock_news(
                stock_id=stock_id,
                start_date=start_date
            )
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                return df.sort_values('date', ascending=False)
            return pd.DataFrame()
        except Exception as e:
            if logger: logger(f"⚠️ 新聞抓取異常: {str(e)}")
            return pd.DataFrame()