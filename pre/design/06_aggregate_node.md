# aggregate_node — 結果集計ノード(草案⑥)

## 役割

ディベート終了後、発言履歴 `turns` を数え上げて勝敗を決める。

- **LLMは使わない。ルールベースの数勘定だけで決める。**
  草案の懸念「ジャッジAIを作るのも違う」への回答であり、
  「リソースから反証が出なくなるまで探させ、多く出せた方が勝ち」という
  草案の解決案をそのまま実装したもの。判定に恣意性がない。

## 勝敗ルール

1. **有効論拠数**(採用された evidence の総数)が多い陣営の勝ち
2. 同数なら**パス回数**が少ない陣営の勝ち
3. それも同じなら引き分け(`"draw"`)

## State との入出力

| 方向 | キー | 内容 |
|---|---|---|
| 入力 | `turns` | 発言履歴 |
| 戻り値 | `scores` | 陣営ごとの集計値(下記の形) |
| 戻り値 | `winner` | `"pro"` / `"con"` / `"draw"` |

### scores の形

```python
{
    "pro": {"evidences": 5, "passes": 1, "turns": 4},
    "con": {"evidences": 3, "passes": 2, "turns": 4},
}
```

## ファイル

`debate_agent/nodes/aggregate_node.py`

## コード骨子

```python
from debate_agent.debate_state import DebateState


def create_aggregate_node():
    # 数勘定だけなので、create関数の引数はなし(LLM不使用)

    def aggregate_node(state: DebateState) -> dict:
        turns = state["turns"]

        # aggregate_nodeが呼び出されたことを確認するために表示しておく
        print("\n[aggregate_node]")

        # ==========================================
        # (1) 陣営ごとに数え上げる
        # ==========================================
        scores = {
            "pro": {"evidences": 0, "passes": 0, "turns": 0},
            "con": {"evidences": 0, "passes": 0, "turns": 0},
        }
        for turn in turns:
            # turn_no=0はassign_camps_nodeが仕込んだダミー発言なので除外する
            if turn["turn_no"] == 0:
                continue
            side = turn["speaker"]
            scores[side]["turns"] += 1
            if len(turn["evidences"]) > 0:
                scores[side]["evidences"] += len(turn["evidences"])
            else:
                scores[side]["passes"] += 1       # 採用0件=パス

        # ==========================================
        # (2) 勝敗を決める
        # ==========================================
        pro, con = scores["pro"], scores["con"]
        if pro["evidences"] != con["evidences"]:
            # ルール1: 有効論拠数の多い方が勝ち
            winner = "pro" if pro["evidences"] > con["evidences"] else "con"
        elif pro["passes"] != con["passes"]:
            # ルール2: パス回数の少ない方が勝ち
            winner = "pro" if pro["passes"] < con["passes"] else "con"
        else:
            # ルール3: 引き分け
            winner = "draw"

        # 動作確認用に集計結果を表示しておく
        print(f'肯定側: 論拠{pro["evidences"]}件 / パス{pro["passes"]}回')
        print(f'否定側: 論拠{con["evidences"]}件 / パス{con["passes"]}回')
        print(f"勝者: {winner}")

        # DebateStateに格納する戻り値をreturnする
        return {"scores": scores, "winner": winner}

    return aggregate_node
```

## 処理の説明

| ブロック | 説明 |
|---|---|
| `turn_no == 0` の除外 | 初期発言(相手の立場文)は論拠を持たないダミーなので集計対象外 |
| 論拠数で勝敗 | 「反証を多く出し続けられた=リソース上で主張が支えられている」とみなす |
| LLM不使用 | 集計・勝敗にLLMを挟まないことで、毎回同じ入力なら同じ勝敗になる(再現性) |

## 動作確認

```
[aggregate_node]
肯定側: 論拠5件 / パス1回
否定側: 論拠3件 / パス2回
勝者: pro
```

## ver2への拡張ポイント

- `scores` に「論拠の角度の多様さ」(debate_turn_node ver2の新規性スコアの平均)を
  追加し、同数時のタイブレークに使う
- LLMによる「各論拠の質コメント」を⑦の解説用に生成する
  (**勝敗判定には使わない**こと。使うとジャッジAI問題が再発する)
