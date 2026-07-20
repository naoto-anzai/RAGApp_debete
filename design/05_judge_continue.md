# judge_continue — 弾切れ判定(草案⑤)

## 役割

debate_turn_node のあとに「ループを続けるか、集計に進むか」を決める。

- **ノードではなく、条件分岐エッジの判定関数**として実装する。
  実習①完成版の「中止/修正/OK」分岐(`add_conditional_edges`)と同じ仕組み。
- LLMは使わない。判定材料(`end_reason`)は debate_turn_node がターン終了時に
  すでに確定させているので、この関数はそれを見て分岐先を返すだけ。

## 判定の全体像(どこで何を判定しているか)

| 判定 | 場所 | 内容 |
|---|---|---|
| 新規論拠が尽きたか | debate_turn_node (d) | 採用0件のターンで `dry_streak[speaker] += 1` |
| 陣営の弾切れ | debate_turn_node 終了処理 | `dry_streak >= DRY_LIMIT`(=2回連続パス)で弾切れ |
| 試合終了 | debate_turn_node 終了処理 | 両陣営弾切れ→`"both_exhausted"` / 上限到達→`"max_turns"` を `end_reason` にセット |
| 分岐 | **judge_continue(ここ)** | `end_reason` が空なら続行、入っていれば集計へ |

> 判定ロジック本体をノード側に置くのは、`dry_streak` の更新と終了判定が
> 同じターン内の情報を使うため。judge_continue は「読むだけ」に保つ。

## ファイル

`debate_agent/debate_graph.py` 内に記述(独立ファイルにしない)。

## コード

```python
def judge_continue(state: DebateState) -> str:
    """debate_turn_nodeのあとの分岐先を決める(草案⑤の弾切れ判定)"""
    # debate_turn_nodeが終了理由をセットしていれば集計へ
    if state["end_reason"] != "":
        print(f"\n[judge_continue] 試合終了: {state['end_reason']}")
        return "finish"

    # まだ弾がある(どちらかが新規論拠を出せる)ので次のターンへ
    return "continue"
```

グラフへの登録(debate_graph.py):

```python
builder.add_conditional_edges(
    "debate_turn",
    judge_continue,
    {
        "continue": "debate_turn",   # ループ: 次の発言ターンへ
        "finish": "aggregate",       # 弾切れ or 上限: 集計へ
    },
)
```

## 動作確認

両陣営が2回ずつパスしたあとのターンで、以下が表示されて集計に進めばOK。

```
[judge_continue] 試合終了: both_exhausted

[aggregate_node]
```

## 注意

- ループするグラフなので、LangGraphの再帰上限(既定25)に注意。
  `max_turns=12` でもノード実行回数は上限を超えうるため、
  メインで `graph.invoke(initial_state, {"recursion_limit": 50})` とする。
- `max_turns` は無限ループ防止の**安全網**。正常系は `both_exhausted` で終わるのが理想
  (=「リソースから反証が出なくなるまで探させる」という草案の解決案そのもの)。
