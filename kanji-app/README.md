# 字引 Jibiki

A local app for looking up kanji by handwriting, viewing cards in the style of Kanji Look and Learn, taking the Minna N5/N4 tests and studying Anki cards. The interface is in Vietnamese, so the button and tab names below are given as they appear in the app.

## Opening the app

1. Open Anki (with the AnkiConnect add-on installed, code `2055492159`).
2. Double-click `start.bat`. Your browser opens `http://localhost:8780`. If the server is already running, this only opens the browser and does not start a second copy.
   To run the server in the background at startup, create a shortcut in the `shell:startup` folder that points to `pyw -3 server.py --no-browser`, with `kanji-app` as the working folder.

Lookup and the Minna tests work while Anki is closed. Studying cards, the review schedule and editing mnemonics need Anki to be open.

## Text scan and notes

- **Text scan** (button in the top bar, "Quét chữ"): select Japanese text anywhere (lookup cards, Minna test pages, Anki cards) to see the meaning and Sino-Vietnamese reading of each kanji, the meaning of the word (if it is in Minna/KLL), and katakana converted to hiragana. Selecting a whole sentence (5 characters or more) adds a machine translation from Google Translate through the server's `/api/dich`. Each kanji has a link that opens its card in a new tab. Characters outside the card set use `app/data/tu-dien.js` (built by `tools/build_tudien.py` from KANJIDIC2 and Unihan).
- **Notes** ("Ghi chú" tab): one page per day, saved automatically to `notes/YYYY-MM-DD.md` on your computer (not published to the repo). The sidebar lists every day that has a note, so empty days don't appear. There is a search box, and a "＋ Ghi chú hôm nay" button in the text scan popup. If the server is down, what you type is kept in the browser and saved once the server is back.

## Study log on GitHub

Each finished task adds one contribution to your GitHub graph:

- **Anki:** finishing a whole deck in "Học với Anki" (no new, learning or due cards left, after grading at least one card). Counts once per deck per day.
- **Minna N4/N5:** submitting a test ("Nộp bài" on a `#de-…` page). Practice pages don't count.

The server appends a line such as `- 20:15 Nộp đề Minna N4 bài 26: 38/42` to `YYYY-MM.md` in a private log repo, commits it and pushes in the background. If you're offline, the commit stays on your computer and goes up with the next push. Setup:

```
gh repo create jibiki-log --private
git clone https://github.com/<you>/jibiki-log.git kanji-app/nhat-ky
```

`kanji-app/nhat-ky/` is ignored by this repo; set `JIBIKI_LOG` to use another folder. Commits use your global git name and email, which must be linked to your GitHub account. Contributions from a private repo only show to other people if "Include private contributions on my profile" is on in your GitHub profile settings.

## Reverse study ("Học với Anki")

The **Học ngược** button on the review bar:
- Kanji cards (the Kanji / 漢字 / character field is a single kanji): shows the Sino-Vietnamese reading and meaning (with a button for a mnemonic hint) and a writing board. After writing, press "Kiểm tra" (Enter). The app reads your handwriting with Google's recognition, compares it with the correct character, then shows the back of the card for grading.
- Other cards: shows the back of the card with any text from the front (including in example sentences) hidden as ＿＿. Once you remember it, flip the card to check.

Grades still go to the Anki card under review.

## Syncing with Anki

Anki is the only place data is kept. The app has no card database of its own:

- The deck list and the new, learning and due counts come straight from Anki.
- While you study, the app drives Anki's own reviewer (`guiDeckReview`, `guiCurrentCard`, `guiShowAnswer`, `guiAnswerCard`): Anki picks the card, and the app displays it and sends the button you press. Card order, daily limits, learning steps, FSRS, the interval on each button and answer time are all calculated by Anki, exactly as if you studied in Anki. The Anki window switches to the review screen while you study. Press "Dừng" to return Anki to the deck list.
- Cards can't be graded out of order: since Anki 23.10 (the v3 scheduler) only the card at the top of the queue can be graded, so the button on a kanji card opens the KLL lesson containing that character.
- Editing "Cách nhớ" (mnemonic) on a kanji card writes directly to the Anki note. Edits made in Anki appear the next time you open the card in the app.
- The "Đồng bộ AnkiWeb" button runs Anki's sync so your changes reach your phone.

AnkiConnect only accepts requests from `http://localhost:8780` (the add-on's `webCorsOriginList` setting).

## Updating the lookup data

Kanji card content (meanings, Sino-Vietnamese readings, examples, compounds, sentences) is extracted from your Anki collection into `app/data/app-data.js`. After adding or editing many notes in Anki, run this again:

```
py tools/build_data.py "<path to a copy of collection.anki2>" _dl/kanjivg/kanjivg.xml.gz _dl/kanjicanvas/kanjicanvas-master/docs/resources/javascript/ref-patterns.js
```

## Component pictures and additional kanji

- `tools/cat_tranh_sach.py` crops the illustrations of 512 characters from your own PDF of Kanji Look and Learn (`kll_book_<code>.png` in `_build/sach`, not published to the repo). Numbers follow the number strip printed at the top of each page, and `_xem.html` is for checking the result. Then run `py tools/anki_update.py media_sach fill`.
- `tools/doc_n3n2.py` reads the PDF "Kanji Look and Learn N3 N2 (tiếng Việt)" (322 characters: Sino-Vietnamese readings, meanings, mnemonic sentences, readings, compounds, pictures) into `_build/n3n2` (not published to the repo). Then run `py tools/make_images.py <new characters> _build/media_n3` and `py tools/anki_update.py media_n3 media_n3_hinh n3n2 fill`. New characters go into the deck `Kanji Look and Learn::5. N3–N2 (sách tiếng Việt)` (numbered `N3·1`…), and additional Minna characters that overlap receive the book's mnemonic sentence and picture.
- `tools/make_tranh.py` draws book-style pictures: an OpenMoji line drawing → the kanji (`kll_pic_<code>.svg`). The picture for each character is chosen in `tools/tranh.txt` (`character|emoji…`).
- `tools/make_images.py` draws two SVG images per character from KanjiVG: the component breakdown (`kll_comp_<code>.svg`, for example 彳 + 夋 → 後) and the stroke order strip (`kll_stroke_<code>.svg`).
- `tools/anki_update.py` adds the images to Anki: it adds the "Hình" and "Nét viết" fields, uploads images to the media folder, changes the back of the card to a book-like layout, and adds 392 kanji found in the Minna vocabulary but not in Kanji Look and Learn (deck `Kanji Look and Learn::4. Bổ sung từ Minna`, numbered `+1`, `+2`…).
- `tools/toeic_bang_viet.py` adds a handwriting board to the back of every card of the "TOEIC EZ Vocab" note type: a strip with the word and its meaning, a lined board for writing (pen pressure, undo, clear) and nothing else changed. The original template is saved to `_build/toeic-template-backup.json` first; run it again to update the board, or with `--remove` to take it out.
- Meanings, Sino-Vietnamese readings and mnemonics for the additional characters are in `tools/extra_vi_*.txt` (`character|SINO-VIETNAMESE|meaning|mnemonic`), written in the Look and Learn style from the components and not copied from the book.

## Sources and licenses

- Handwriting recognition: Google Input Tools (through the server's `/api/viet`; stroke order and stroke count don't matter, and connected strokes are still read), with [KanjiCanvas](https://github.com/asdfjkl/kanjicanvas) — MIT (`app/lib/kanjicanvas/LICENSE.txt`) as the offline fallback.
- Mnemonic pictures: [OpenMoji](https://openmoji.org) — CC BY-SA 4.0.
- Stroke order and component pictures: [KanjiVG](http://kanjivg.tagaini.net) — Ulrich Apel, CC BY-SA 3.0.
- On/kun readings and stroke counts for additional characters: [KANJIDIC2](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project) — EDRDG, CC BY-SA 4.0.
- Kanji content, compounds, example sentences and vocabulary: your own Anki decks.
