# assign_camps_node — 陣営分け・初期化ノード(草案②)

## 役割

ディベート進行に使うStateのフィールドをすべて初期化する。
LLMもベクトルストアも使わない、純粋な初期化ノード。

- 先攻は肯定側(`"pro"`)固定とする。
- 先攻の1ターン目には「反論対象になる相手の発言」がまだ無いので、
  **相手の立場文そのものを最初の反論対象**として `turns` に仕込んでおく
  (これで debate_turn_node は毎ターン同じ処理で書ける)。

## State との入出力

| 方向 | キー | 内容 |
|---|---|---|
| 入力 | `stance_con` | 否定側の立場文(初回の反論対象に使う) |
| 戻り値 | `current_speaker` | `"pro"`(先攻) |
| 戻り値 | `turns` | 初期発言1件(下記参照)だけが入ったリスト |
| 戻り値 | `used_doc_ids` | `{"pro": [], "con": []}` |
| 戻り値 | `dry_streak` | `{"pro": 0, "con": 0}` |
| 戻り値 | `turn_count` | `0` |
| 戻り値 | `end_reason` | `""` |

## ファイル

`debate_agent/nodes/assign_camps_node.py`

## コード骨子

```python
from debate_agent.debate_state import DebateState


def create_assign_camps_node():

    def assign_camps_node(state: DebateState) -> dict:
        # DebateStateから、初回の反論対象になる相手の立場文を取り出す
        stance_con = state["stance_con"]

        # assign_camps_nodeが呼び出されたことを確認するために表示しておく
        print("\n[assign_camps_node]")
        print("先攻: 肯定側(pro) / 後攻: 否定側(con)")

        # ==========================================
        # 初期発言(turn_no=0)をつくる
        # ==========================================
        # 「否定側が立場文を主張した」ことにしておくと、
        # 先攻(pro)の1ターン目が「相手の直前発言への反論」として
        # 他のターンと同じ形で処理できる
        initial_turn = {
            "turn_no": 0,
            "speaker": "con",
            "target_claim": "",
            "query": "",
            "claim": stance_con,     # 否定側の立場文を最初の主張とみなす
            "evidences": [],
        }

        # ディベート進行用フィールドを初期化してreturnする
        return {
            "current_speaker": "pro",              # 先攻は肯定側
            "turns": [initial_turn],
            "used_doc_ids": {"pro": [], "con": []},
            "dry_streak": {"pro": 0, "con": 0},
            "turn_count": 0,
            "end_reason": "",
        }

    return assign_camps_node
```

## 処理の説明

| ブロック | 説明 |
|---|---|
| `initial_turn` | 「turn_no=0 の con の発言」というダミー発言。evidences が空なのは立場文には論拠がまだ無いため。**⑥の集計では turn_no=0 を除外する**こと |
| `used_doc_ids` | 同じチャンクを二度使わないための記録。陣営ごとに分ける |
| `dry_streak` | 「新規論拠が見つからなかった連続回数」。弾切れ判定(⑤)の材料 |

## 動作確認

```
[assign_camps_node]
先攻: 肯定側(pro) / 後攻: 否定側(con)
```

→ 戻り値の `turns` に1件だけ入っていて、`current_speaker` が `"pro"` ならOK。
