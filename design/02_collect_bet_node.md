# collect_bet_node — 賭け入力ノード(草案①の立場選択)

## 役割

論題と両陣営の立場をユーザーに提示し、
「どちらのAIが勝つと思うか」を入力してもらう。

- 実習①完成版の `human_select_node`(人間が"1"/"2"/"3"を入力)と同じ、
  `input()` を使う人間入力ノード。
- 賭けは**観戦用**。ディベートの進行や勝敗判定には一切影響させない。

## State との入出力

| 方向 | キー | 内容 |
|---|---|---|
| 入力 | `topic` | 命題文 |
| 入力 | `stance_pro` | 肯定側の立場文 |
| 入力 | `stance_con` | 否定側の立場文 |
| 戻り値 | `user_bet` | `"pro"` または `"con"` |

## ファイル

`debate_agent/nodes/collect_bet_node.py`

## コード骨子

```python
from debate_agent.debate_state import DebateState


def create_collect_bet_node():
    # LLMもvectorstoreも使わないので、create関数の引数はなし

    def collect_bet_node(state: DebateState) -> dict:
        # DebateStateから、提示に使う情報を取り出す
        topic = state["topic"]
        stance_pro = state["stance_pro"]
        stance_con = state["stance_con"]

        # collect_bet_nodeが呼び出されたことを確認するために表示しておく
        print("\n[collect_bet_node]")

        # ==========================================
        # (1) 対戦カードの提示
        # ==========================================
        print(f"論題: {topic}")
        print(f"  AI-1(肯定側): {stance_pro}")
        print(f"  AI-2(否定側): {stance_con}")

        # ==========================================
        # (2) 賭けの入力("1" or "2" 以外は再入力)
        # ==========================================
        while True:
            select = input("どちらが勝つと思いますか? (1:肯定側 / 2:否定側): ")
            if select in ("1", "2"):
                break
            print("1 か 2 を入力してください。")

        # 入力値をState用の値に変換する
        user_bet = "pro" if select == "1" else "con"

        # DebateStateに格納する戻り値"user_bet"をreturnする
        return {"user_bet": user_bet}

    return collect_bet_node
```

## 処理の説明

| ブロック | 説明 |
|---|---|
| `while True` + `input()` | 実習①の human_select_node と同じ方式。不正入力は再入力させる |
| `"pro" if select == "1" else "con"` | 表示用の"1"/"2"を、State内部表現の"pro"/"con"に変換 |

> Streamlit化するときは、このノードだけ `input()` をUI部品に差し替えれば済むよう、
> 提示と入力以外の処理を入れないこと。

## 動作確認

```
[collect_bet_node]
論題: 地球温暖化は進行している
  AI-1(肯定側): ...
  AI-2(否定側): ...
どちらが勝つと思いますか? (1:肯定側 / 2:否定側): 1
```

→ 戻り値が `{"user_bet": "pro"}` になればOK。
