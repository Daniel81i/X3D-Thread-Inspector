# AMD Ryzen X3D - Dual-CCD & Thread Inspector

🌐 **[English](README.md)** | **[日本語](README.ja.md)**

---

**AMD Ryzen 9 7950X3D / 9950X3D** などのデュアルCCD構成（**CCD0: 3D V-Cache** / **CCD1: Frequency**）に最適化された、リアルタイム・プロセッサ＆スレッド診断ツールです。

VRChatなどのVR環境や高負荷ゲームにおいて、**「メイン描画や物理演算が本当に 3D V-Cache（CCD0）に乗っているか」**、**「音声や通信などのサブ処理が 高クロック（CCD1）にうまく逃げてヘッドルームを確保できているか」** を安全かつ視覚的に検証できます。

---

## 主な特徴

* **100% アンチチートセーフ（完全無害）**
  * Easy Anti-Cheat (EAC) や BattlEye などの保護下にあるゲームでもブロックされません。
  * メモリ改ざんやインジェクションは一切行わず、Windows標準の安全な情報取得APIのみを使用しています。
* **高精度なスレッド役割の推定**
  * OS起動時に最初に生成された Primary Thread を厳密特定（`Main/GameLoop` 確証度100%）。
  * CPUサイクル消費順位に基づき、`Render/Gfx`（描画）、`Physics/IK`（物理・PhysBones）、`Audio/Network`（音声・通信）などを自動分類。
* **CCD0 Top 5 vs CCD1 Top 5 の並列インスペクター**
  * 左右2カラムで各CCDの主力スレッド5本（計10本）をリアルタイム追跡。
  * コア間を移動（マイグレーション）したスレッドには **`⮀`（オレンジ色マーク）** が点灯。
* **連動リサイズ対応の折りたたみUI**
  * 「スレッド詳細を隠す」ボタンを押すと、**ウィンドウが自動でコンパクト（高さ250px）に縮小**。
  * 展開すると大画面（高さ560px）の詳細ダッシュボードに戻ります。
* **📌 Always on Top（常時最前面）切り替え**
  * 普段はチェックを外して普通のウィンドウとして背面に回せます。

---

## 画面イメージ

### 1. 詳細展開モード（大画面）
```text
┌──────────────────────────────────────────────────────────────────────────┐
│ AMD Ryzen 9 X3D - Dual-CCD & Thread Inspector                     — □ ✕ │
├──────────────────────────────────────────────────────────────────────────┤
│ Target Process: [ vrchat.exe          ] [ Set / Refresh ]  [x] Always on Top │
│ ● Target: vrchat.exe  |  PID: 18420  |  Threads: 68  |  [Affinity: All Cores]│
├──────────────────────────────────────────────────────────────────────────┤
│ ⚡ CCD0 (3D V-Cache): 61.2%  [38 th]       🚀 CCD1 (Frequency): 38.8%  [30 th] │
│ [██████████████████████░░░░░░]             [██████████████░░░░░░░░░░░░░░]│
│ Logical Core Allocation (0-15: CCD0 V-Cache | 16-31: CCD1 Freq)          │
│ ■■■■■■■■ ■■■■■■■■   ■■■■■■□□ □□□□□□□□                                    │
├──────────────────────────────────────────────────────────────────────────┤
│ [▼ スレッド詳細分析 (CCD0 Top 5 vs CCD1 Top 5) を隠す]                   │
├────────────────────────────────────┬─────────────────────────────────────┤
│ ⚡ CCD0 (3D V-Cache) Top 5 Threads │ 🚀 CCD1 (Frequency) Top 5 Threads   │
│                                    │                                     │
│ #1 C04  Main/GameLoop   35.2%      │ #1 C18  Physics/Job    8.5%         │
│ #2 C02  Render/Gfx      18.0%      │ #2 C20  Audio/Network  6.1% ⮀       │
│ #3 C06  Physics/IK       4.2% ⮀    │ #3 C16  Worker (TID:14220) 2.5%     │
│ #4 C00  Worker (TID:14208) 1.5%    │ #4 C24  Worker (TID:14224) 1.2%     │
│ #5 C08  Worker (TID:14212) 0.8%    │ #5 C22  Worker (TID:14228) 0.5%     │
└────────────────────────────────────┴─────────────────────────────────────┘
```

### 2. コンパクトモード（折りたたみ時）
```text
┌──────────────────────────────────────────────────────────────────────────┐
│ AMD Ryzen 9 X3D - Dual-CCD & Thread Inspector                     — □ ✕ │
├──────────────────────────────────────────────────────────────────────────┤
│ Target Process: [ vrchat.exe          ] [ Set / Refresh ]  [ ] Always on Top │
│ ● Target: vrchat.exe  |  PID: 18420  |  Threads: 68  |  [Affinity: All Cores]│
├──────────────────────────────────────────────────────────────────────────┤
│ ⚡ CCD0 (3D V-Cache): 61.2%  [38 th]       🚀 CCD1 (Frequency): 38.8%  [30 th] │
│ [██████████████████████░░░░░░]             [██████████████░░░░░░░░░░░░░░]│
│ Logical Core Allocation (0-15: CCD0 V-Cache | 16-31: CCD1 Freq)          │
│ ■■■■■■■■ ■■■■■■■■   ■■■■■■□□ □□□□□□□□                                    │
├──────────────────────────────────────────────────────────────────────────┤
│ [▶ スレッド詳細分析 (CCD0 Top 5 vs CCD1 Top 5) を展開]                   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 使い方

### A. Python環境で直接動かす場合
Python 3.10以上がインストールされていれば、追加のパッケージ（pip等）は不要です。
```bash
python ccd_monitor.py
# または start_monitor.bat をダブルクリック
```

### B. 単体 EXE をビルドする場合（PyInstaller）
```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --clean --name "X3D-Thread-Inspector" ccd_monitor.py
```
`dist/X3D-Thread-Inspector.exe` が生成されます。

---

## GitHub Actions 自動ビルド

このリポジトリを GitHub にプッシュすると、GitHub Actions により自動的に Windows 用の単体 `.exe` がビルドされます。

1. **Actions タブ**: すべての Push / PR でビルド成果物（Artifact）としてダウンロード可能。
2. **Releases**: GitHub Release ページに自動でバージョンがカウントアップ（`v0.0.1` → `v0.0.2`...）され、最新の `X3D-Thread-Inspector.exe` および ZIP パッケージが自動公開されます。

---

## ライセンス
MIT License
