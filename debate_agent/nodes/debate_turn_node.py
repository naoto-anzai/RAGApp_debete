from textwrap import dedent

import numpy as np

from debate_agent.debate_state import DebateState

SEARCH_K = 5
MAX_EVIDENCES = 2
DRY_LIMIT = 2
NOVELTY_THRESHOLD = 0.88

PASS_CLAIM = "(有効な新規論拠が見つからず、パス)"


def cosine(a, b) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def is_novel(cand_vec, prev_vecs) -> bool:
    for pv in prev_vecs:
        if cosine(cand_vec, pv) >= NOVELTY_THRESHOLD:
            return False
    return True


def last_substantive_claim(turns, opponent) -> str:
    for turn in reversed(turns):
        if turn["speaker"] == opponent and turn["claim"] != PASS_CLAIM:
            return turn["claim"]
    return turns[-1]["claim"]


def create_debate_turn_node(vectorstores: dict, llm):

    def debate_turn_node(state: DebateState) -> dict:
        speaker = state["current_speaker"]
        turns = state["turns"]
        used_doc_ids = state["used_doc_ids"]
        dry_streak = state["dry_streak"]
        turn_count = state["turn_count"] + 1

        my_stance = state["stance_pro"] if speaker == "pro" else state["stance_con"]
        opponent = "con" if speaker == "pro" else "pro"
        vectorstore = vectorstores[speaker]

        print(f"\n[debate_turn_node] ターン{turn_count}: {speaker}の番")

        # 反論対象の特定(相手のパスには反論しない)
        target_claim = last_substantive_claim(turns, opponent)

        # 反証クエリ生成
        my_past_quotes = [
            ev["quote"][:100]
            for turn in turns if turn["speaker"] == speaker
            for ev in turn["evidences"]
        ]

        query_prompt = dedent(f"""
            あなたはディベートで「{my_stance}」の立場です。
            相手の主張に反する証拠を資料から探すための検索クエリを1つ作ってください。
            既出の論拠とは異なる角度(統計/因果/事例/方法論への批判など)を狙ってください。

            【相手の主張】
            {target_claim}

            【既出の論拠】
            {my_past_quotes}

            検索クエリの文字列だけを出力してください。
            """).strip()

        response = llm.invoke(query_prompt)
        query = response.content.strip()

        # 検索 + フィルタ(自陣営DBなので立場チェックは不要)
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": SEARCH_K}
        )
        docs = retriever.invoke(query)

        embeddings = vectorstore.embeddings

        # この陣営が過去に採用した論拠(全文)を新規性判定の基準にする
        past_quotes = [
            ev["quote"]
            for turn in turns if turn["speaker"] == speaker
            for ev in turn["evidences"]
        ]
        prev_vecs = embeddings.embed_documents(past_quotes) if past_quotes else []

        evidences = []
        skipped = 0

        for doc in docs:
            page_label = doc.metadata.get("page_label", "不明")
            file_name = doc.metadata.get("file_name", "不明")
            doc_id = f"{file_name}_p{page_label}_{hash(doc.page_content) % 100000}"

            if doc_id in used_doc_ids[speaker]:
                continue

            quote = doc.page_content[:300]
            cand_vec = embeddings.embed_query(quote)

            # 既出論拠・今ターン採用済みのどれとも意味的に近ければ棄却
            if not is_novel(cand_vec, prev_vecs):
                skipped += 1
                continue

            evidences.append(
                {
                    "doc_id": doc_id,
                    "file_name": file_name,
                    "page_label": page_label,
                    "quote": quote,
                }
            )
            prev_vecs.append(cand_vec)

            if len(evidences) >= MAX_EVIDENCES:
                break

        print(f"検索{len(docs)}件 → 採用{len(evidences)}件(重複棄却{skipped}件)")

        # 反論生成 / 論拠ゼロならパス
        if len(evidences) > 0:
            evidence_text = "\n".join(
                f'[{ev["file_name"]} p.{ev["page_label"]}] {ev["quote"]}'
                for ev in evidences
            )

            claim_prompt = dedent(f"""
                あなたはディベートで「{my_stance}」の立場です。
                以下の資料だけを根拠に、相手の主張へ150〜250字で反論してください。
                資料にない主張はしないこと。根拠には[出典 ページ]を付けること。

                【相手の主張】
                {target_claim}

                【資料】
                {evidence_text}
                """).strip()

            response = llm.invoke(claim_prompt)
            claim = response.content.strip()
            dry_streak[speaker] = 0
        else:
            claim = PASS_CLAIM
            dry_streak[speaker] += 1

        print(f"--- {speaker}の発言 ---")
        print(claim)

        new_turn = {
            "turn_no": turn_count,
            "speaker": speaker,
            "target_claim": target_claim,
            "query": query,
            "claim": claim,
            "evidences": evidences,
        }

        used_doc_ids[speaker] += [ev["doc_id"] for ev in evidences]

        # どちらか一方でも弾切れ(DRY_LIMIT連続パス)になったら試合終了
        if dry_streak["pro"] >= DRY_LIMIT or dry_streak["con"] >= DRY_LIMIT:
            end_reason = "exhausted"
        elif turn_count >= state["max_turns"]:
            end_reason = "max_turns"
        else:
            end_reason = ""

        return {
            "turns": turns + [new_turn],
            "used_doc_ids": used_doc_ids,
            "dry_streak": dry_streak,
            "current_speaker": opponent,
            "turn_count": turn_count,
            "end_reason": end_reason,
        }

    return debate_turn_node
