from typing import TypedDict


class DebateState(TypedDict):
    # --- セットアップ ---
    topic: str            # 論題(ユーザー入力を命題文に正規化したもの)
    stance_pro: str       # 肯定側の立場文
    stance_con: str       # 否定側の立場文
    user_bet: str         # ユーザーの勝敗予想 "pro" or "con"

    # --- ディベート進行 ---
    current_speaker: str  # いま発言する側 "pro" or "con"
    turns: list           # 発言履歴(1発言 = dict)
    used_doc_ids: dict    # 使用済みチャンクID {"pro": [...], "con": [...]}
    dry_streak: dict      # 新規論拠なしの連続回数 {"pro": 0, "con": 0}
    turn_count: int       # 現在のターン数
    max_turns: int        # 安全上限(例: 12)
    end_reason: str       # 終了理由 "exhausted" / "max_turns" / ""

    # --- 結果 ---
    scores: dict          # 集計結果(陣営ごとの論拠数など)
    winner: str           # "pro" / "con" / "draw"
    report: str           # 最終レポート(Markdown文字列)
