import os
import polars as pl
import duckdb
import re
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
from matplotlib import rcParams


# フォント設定（全体に適用）
# plt.rcParams["font.family"] = ["Noto Sans CJK JP", "sans-serif"]
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Hiragino Maru Gothic Pro', 'Yu Gothic', 'Meirio', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']

# rcParams['font.family'] = 'Meiryo'  # Windowsならメイリオ
# macOS: 'Hiragino Sans'
# Linux: 'IPAexGothic' など

st.set_page_config(page_title="スプリンターズS分析", layout="wide")

# === (1) CSV読込 ===
csv_path = os.path.join(os.path.dirname(__file__), "sprinters_stakes_2015_2024.csv")
df = pl.read_csv(csv_path)

# タイムを秒数に変換
def to_seconds(time_str):
    if not isinstance(time_str, str) or time_str.strip() == "":
        return None
    if ":" in time_str:
        m, s = time_str.split(":")
        return int(m) * 60 + float(s)
    try:
        return float(time_str)
    except ValueError:
        return None

df = df.with_columns(
    pl.col("タイム").map_elements(to_seconds, return_dtype=pl.Float64).alias("タイム秒")
)

# 馬体重を分割
def split_weight(w):
    if isinstance(w, str) and "(" in w:
        m = re.match(r"(\d{3})\(([+-]?\d+)\)", w)
        if m:
            base, diff = m.groups()
            return int(base), int(diff)
    return None, None

df = df.with_columns([
    pl.col("馬体重").map_elements(lambda x: split_weight(x)[0], return_dtype=pl.Int64).alias("馬体重kg"),
    pl.col("馬体重").map_elements(lambda x: split_weight(x)[1], return_dtype=pl.Int64).alias("体重増減")
])

# 性齢を分割
def split_seirei(s):
    if not isinstance(s, str) or s == "":
        return None, None
    sex = s[0]
    age = int(s[1:]) if s[1:].isdigit() else None
    return sex, age

df = df.with_columns([
    pl.col("性齢").map_elements(lambda x: split_seirei(x)[0], return_dtype=pl.Utf8).alias("性別"),
    pl.col("性齢").map_elements(lambda x: split_seirei(x)[1], return_dtype=pl.Int64).alias("年齢")
])

# 数値キャスト
df = df.with_columns([
    pl.col("人気").cast(pl.Int64, strict=False),
    pl.col("単勝").cast(pl.Float64, strict=False),
    pl.col("上がり3F").cast(pl.Float64, strict=False)
])

# DuckDBに登録
con = duckdb.connect()
con.register("races", df)

# Streamlit サイドバーで選択
mode = st.sidebar.radio("表示モードを選択", ["人気別勝率", "枠順別勝率", "年ごとの平均馬体重・平均上がり3F"])

# === 人気別勝率 ===
if mode == "人気別勝率":
    q_pop_stats = con.execute("""
        SELECT
            人気,
            COUNT(*) AS 出走数,
            SUM(CASE 
                    WHEN (着差 IS NULL OR TRIM(着差) = '') 
                         AND NOT (year = 2015 AND 馬名 = 'マジンプロスパー')
                         AND NOT (year = 2018 AND 馬名 = 'ラッキーバブルズ')
                    THEN 1 ELSE 0 END
               ) AS 勝利数,
            100.0 * SUM(CASE 
                           WHEN (着差 IS NULL OR TRIM(着差) = '') 
                                AND NOT (year = 2015 AND 馬名 = 'マジンプロスパー')
                                AND NOT (year = 2018 AND 馬名 = 'ラッキーバブルズ')
                           THEN 1 ELSE 0 END
                        ) / COUNT(*) AS 勝率
        FROM races
        WHERE 人気 IS NOT NULL
        GROUP BY 人気
        ORDER BY 人気
    """).df()

    st.subheader("人気別勝率（過去10年）")
    st.dataframe(q_pop_stats.set_index("人気"))

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(q_pop_stats["人気"].astype(str), q_pop_stats["勝率"], color="orange")
    ax.set_xlabel("人気")
    ax.set_ylabel("勝率 (%)")
    ax.set_title("スプリンターズS 過去10年 人気別勝率")
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    # ラベル（0 のときは非表示）
    for bar, rate, wins in zip(bars, q_pop_stats["勝率"], q_pop_stats["勝利数"]):
        if rate > 0:
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height()-0.5,
                    f"{int(rate)}%", ha="center", va="top",
                    fontsize=9, color="black")
        if wins > 0:
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height()-2.0,
                    f"{int(wins)}勝", ha="center", va="top",
                    fontsize=9, color="red")

    st.pyplot(fig)

# === 枠順別勝率 ===
elif mode == "枠順別勝率":
    q_waku = con.execute("""
    WITH base AS (
        SELECT DISTINCT year, 枠番
        FROM races
        WHERE NOT (
                (year = 2015 AND 馬名 = 'マジンプロスパー')
             OR (year = 2018 AND 馬名 = 'ラッキーバブルズ')
        )
    )
    SELECT
        b.枠番,
        COUNT(*) AS 出走数,
        SUM(CASE WHEN EXISTS (
            SELECT 1
            FROM races r2
            WHERE r2.year = b.year
              AND r2.枠番 = b.枠番
              AND (r2.着差 IS NULL OR TRIM(r2.着差) = '')
              AND NOT (
                  (r2.year = 2015 AND r2.馬名 = 'マジンプロスパー')
               OR (r2.year = 2018 AND r2.馬名 = 'ラッキーバブルズ')
              )
        ) THEN 1 ELSE 0 END) AS 勝利数,
        ROUND(100.0 * SUM(CASE WHEN EXISTS (
            SELECT 1
            FROM races r2
            WHERE r2.year = b.year
              AND r2.枠番 = b.枠番
              AND (r2.着差 IS NULL OR TRIM(r2.着差) = '')
              AND NOT (
                  (r2.year = 2015 AND r2.馬名 = 'マジンプロスパー')
               OR (r2.year = 2018 AND r2.馬名 = 'ラッキーバブルズ')
              )
        ) THEN 1 ELSE 0 END) / COUNT(*), 1) AS 勝率
    FROM base b
    GROUP BY b.枠番
    ORDER BY b.枠番;

    """).df()

   # 表示用に整数化
    df_disp = q_waku.copy()
    for c in ["出走数", "勝利数", "勝率"]:
        df_disp[c] = df_disp[c].astype(int)

    st.subheader("枠順別勝率（過去10年）")

    # 枠色スタイル
    waku_colors = {1:"#FFFFFF",2:"#000000",3:"#FF0000",4:"#0000FF",
                   5:"#FFFF00",6:"#008000",7:"#FF7F00",8:"#FFC0CB"}

    def color_waku(val):
        txt = "black" if val == 1 else "white"
        return f"background-color:{waku_colors.get(val,'#FFFFFF')}; color:{txt}; font-weight:bold;"

    # 枠番列だけ色付け＆インデックス非表示
    styled = (df_disp.style
              .applymap(color_waku, subset=["枠番"])
              .hide(axis="index"))  # pandas>=2

    st.dataframe(styled, use_container_width=True)

    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar(q_waku["枠番"].astype(str), q_waku["勝率"], color="skyblue")
    ax.set_xlabel("枠番")
    ax.set_ylabel("勝率 (%)")
    ax.set_title("スプリンターズS 過去10年 枠順別勝率")
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    # ラベル（0 のときは非表示）
    for bar, rate, wins in zip(bars, q_waku["勝率"], q_waku["勝利数"]):
        if rate > 0:
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height()-0.5,
                    f"{rate:.1f}%", ha="center", va="top",
                    fontsize=9, color="black")
        if wins > 0:
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height()-1.5,
                    f"{int(wins)}勝", ha="center", va="top",
                    fontsize=9, color="red")

    st.pyplot(fig)

# === 年ごとの平均馬体重・上がり3F ===
elif mode == "年ごとの平均馬体重・平均上がり3F":
    # === (5) 年ごとの平均馬体重・平均上がり3F ===
    q_avg = con.execute("""
        SELECT year AS Year,
               ROUND(AVG(馬体重kg), 1) AS 平均馬体重,
               ROUND(AVG("上がり3F"), 1) AS 平均上がり3F
        FROM races
        WHERE 馬体重kg IS NOT NULL AND "上がり3F" IS NOT NULL
        GROUP BY year
        ORDER BY year
    """).df()

    st.subheader("年ごとの平均馬体重・平均上がり3F")
    st.dataframe(q_avg.set_index("Year"))

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(q_avg["Year"], q_avg["平均馬体重"], marker="o", color="green", label="平均馬体重 (kg)")
    ax1.set_ylabel("平均馬体重 (kg)")
    ax1.set_xlabel("Year")
    ax1.grid(True)

    for x, y in zip(q_avg["Year"], q_avg["平均馬体重"]):
        ax1.text(x, y, f"{y:.1f}", ha="left", va="bottom", fontsize=9, color="green")

    ax1.xaxis.set_major_locator(ticker.MultipleLocator(1))
    plt.xticks(range(2015, 2025, 1))

    ax2 = ax1.twinx()
    ax2.plot(q_avg["Year"], q_avg["平均上がり3F"], marker="^", color="red", label="平均上がり3F (秒)")
    ax2.set_ylabel("平均上がり3F (秒)")

    for x, y in zip(q_avg["Year"], q_avg["平均上がり3F"]):
        ax2.text(x, y, f"{y:.1f}", ha="left", va="bottom", fontsize=9, color="red")

    fig.legend(loc="upper left", bbox_to_anchor=(0.1, 1.0))
    plt.title("スプリンターズS 過去10年 平均馬体重・平均上がり3Fの推移")

    st.pyplot(fig)






