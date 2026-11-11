"""Merge the Kanji Look and Learn decks "2. Từ ghép" and "3. Ứng dụng (câu Workbook)" into one deck, lesson by lesson,
so each lesson is studied as: the compound words, the same words in Workbook sentences, then writing the words.

Every card moves to "2. Từ ghép + câu Workbook::Bài NN" with its schedule unchanged, the deck options stay
"KLL --Bài con", and the old decks are removed once empty. Order inside a lesson comes from Anki itself: new cards are
gathered by deck, then card type, so recognition and sentence cards (card type 1) come before the writing cards
(card type 2), and "bury new siblings" pushes a word's writing card to the next day. AnkiConnect can't set new-card
positions, so the script doesn't try to interleave words and sentences further.

Usage: py gop_kll.py            (writes _build/gop-kll-backup.json first: every card's old deck and position)
       py gop_kll.py --dry-run  (prints the plan only)
"""
import json, os, re, sys, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = "Kanji Look and Learn"
WORDS = ROOT + "::2. Từ ghép"
SENTS = ROOT + "::3. Ứng dụng (câu Workbook)"
NEW = ROOT + "::2. Từ ghép + câu Workbook"
HERE = os.path.dirname(os.path.abspath(__file__))
BACKUP = os.path.join(HERE, "..", "_build", "gop-kll-backup.json")


def call(action, **params):
    req = urllib.request.Request("http://127.0.0.1:8765", json.dumps({"action": action, "version": 6, "params": params}).encode("utf-8"))
    r = json.loads(urllib.request.urlopen(req, timeout=120).read().decode("utf-8"))
    if r.get("error"):
        raise RuntimeError(r["error"])
    return r["result"]


def text(v):
    return re.sub(r"<[^>]+>", "", v or "").replace("&nbsp;", " ").strip()


def lesson_of(deck):
    m = re.search(r"::Bài (\d+)$", deck)
    return int(m.group(1)) if m else None


def main():
    dry = "--dry-run" in sys.argv
    cards = call("cardsInfo", cards=call("findCards", query=f'"deck:{WORDS}" or "deck:{SENTS}"'))
    conf = call("getDeckConfig", deck=WORDS)["id"]
    by_lesson = {}
    for c in cards:
        b = lesson_of(c["deckName"])
        if b is None:
            raise SystemExit(f"card {c['cardId']} is not in a lesson subdeck: {c['deckName']}")
        by_lesson.setdefault(b, []).append(c)

    order, moves = [], {}
    for b in sorted(by_lesson):
        cs = sorted(by_lesson[b], key=lambda c: c["cardId"])  # creation order = book order
        words = [c for c in cs if c["deckName"].startswith(WORDS)]
        sents = [c for c in cs if c["deckName"].startswith(SENTS)]
        rec = [c for c in words if c["ord"] == 0]
        prod = [c for c in words if c["ord"] == 1]
        left = list(sents)
        seq = []
        for r in rec:
            seq.append(r)
            w = text(r["fields"]["Từ"]["value"])
            mine = [s for s in left if text(s["fields"]["Từ"]["value"]) == w]
            seq += mine
            left = [s for s in left if s not in mine]
        seq += left + prod
        order += seq
        target = f"{NEW}::Bài {b:02d}"
        for c in cs:
            moves.setdefault(target, []).append(c["cardId"])
        print(f"Bài {b:02d}: {len(rec)} recognition, {len(sents)} sentences ({len(sents) - len(left)} right after their word), {len(prod)} writing")

    new_cards = [c for c in order if c["type"] == 0]
    print(f"total {len(cards)} cards ({len(new_cards)} new), into {len(moves)} lessons of {NEW}")
    if dry:
        return

    os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
    if not os.path.exists(BACKUP):
        json.dump([{"card": c["cardId"], "deck": c["deckName"], "due": c["due"], "type": c["type"]} for c in cards],
                  open(BACKUP, "w", encoding="utf-8"), ensure_ascii=False)
        print("backup:", os.path.abspath(BACKUP))

    for deck, ids in moves.items():
        call("changeDeck", cards=ids, deck=deck)
    for deck in [NEW] + list(moves):
        call("setDeckConfigId", decks=[deck], configId=conf)

    # Remove the old decks only if they are now empty. Deleting a parent deck also deletes its lesson subdecks.
    old = [d for d in (WORDS, SENTS) if d in call("deckNames")]
    left = call("findCards", query=" or ".join(f'"deck:{d}"' for d in old)) if old else []
    if left:
        print(f"old decks still hold {len(left)} cards, not removed")
    elif old:
        call("deleteDecks", decks=old, cardsToo=True)
        print(f"removed the empty old decks: {old}")
    print("done")


if __name__ == "__main__":
    main()
