# スプリンターズS 勝率分析ダッシュボード

**DuckDB + Polars + Streamlit** を使って、スプリンターズステークス過去10年の勝率分析を行い
Webダッシュボードとして公開している。

公開サイト: **[Streamlit App](https://sprinters-app-zakuoji.streamlit.app/)**

---

## 🔧 技術スタック
- **Python 3.22**
- **Polars**: 高速データ処理
- **DuckDB**: SQLで集計処理
- **Streamlit**: Webアプリ化
- **Matplotlib**: グラフ描画

---

## 📂 セットアップ手順

1. **リポジトリをクローン**
   ```
   git clone https://github.com/your-account/sprinters-app.git
   cd sprinters-app
   ```

2. **必要ライブラリをインストール**

   ```
   pip install -r requirements.txt
   ```

3. **CSV データ配置**
   過去10年分のスプリンターズSデータを `sprinters_stakes_2015_2024.csv` としてリポジトリ直下に置く。  
   ※データのフォーマットはcsvのヘッダー内容次第で自由に項目を設定できます。

4. **ローカル実行**

   ```
   streamlit run SprintersStakes.py
   ```

   ブラウザで localhost が開きます。

---

## 📊 機能

* **人気別勝率**
  各人気の勝率をバーグラフ表示（取消馬を除外）
* **枠順別勝率**
  枠番ごとの勝率を色付きテーブル＋グラフ表示
* **年ごとの平均馬体重・平均上がり3F**
  年ごとの平均推移を折れ線グラフで可視化

サイドバーから表示モードを切り替え可能です。  
※ここでは載せていませんが複勝率や連対率も載せることができます。

---

## 🌐 デプロイ (Streamlit Cloud)

1. [Streamlit Cloud](https://share.streamlit.io/) に GitHub アカウントでログイン
2. 新規アプリを作成し、GitHub のリポジトリとブランチを指定
3. `requirements.txt` を元に環境が構築、自動デプロイされる

---

## 📝 補足

* 日本語フォントの文字化けを回避するため複数設定
* DuckDB を使うことで **SQL 集計のわかりやすさ** と **高速処理** の両立を実現
* Polars でデータ前処理をシンプルに記述
