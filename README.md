# 字引 Jibiki

Bộ công cụ tự học tiếng Nhật đi kèm Anki:

- [`kanji-app/`](kanji-app/) — web app chạy trên máy: vẽ chữ lên bảng trắng để nhận diện kanji, mở thẻ kiểu Kanji Look and Learn (hình thành phần, thứ tự nét, từ ví dụ), học thẻ trực tiếp trên bộ sưu tập Anki qua AnkiConnect.
- Quét chữ để xem nghĩa / Hán Việt / cách đọc, và ghi chú theo ngày ngay trong app.
- [`minna-n5/`](minna-n5/) — 5 đề N5, mỗi đề gộp 5 bài Minna no Nihongo I, phủ toàn bộ từ vựng và ngữ pháp; có đồng hồ làm đề và lịch sử điểm.
- [`minna-n4/`](minna-n4/) — 25 đề N4, mỗi đề một bài Minna no Nihongo II (26–50): ngữ pháp, từ vựng, kanji.

## Dữ liệu không có trong repo

Nội dung sách (cách nhớ và ví dụ của Kanji Look and Learn, danh sách từ vựng Minna no Nihongo) được trích từ deck Anki cá nhân nên không đưa lên đây. Sau khi clone:

1. `kanji-app/app/data/app-data.js`: chạy `kanji-app/tools/build_data.py` trên bản sao `collection.anki2` của bạn (xem [kanji-app/README.md](kanji-app/README.md)).
2. `minna-n5/data/vocab.json`, `minna-n4/data/vocab.json`: danh sách từ vựng theo bài (các trường cần có xem trong `tools/check.py` của từng thư mục). Có tệp này rồi thì chạy `tools/build.py` trong từng thư mục để tạo trang đề ở `dist/`, rồi chép sang `kanji-app/app/minna/n5.html` và `n4.html`.

Đề thi, giải thích ngữ pháp, 392 cách nhớ kanji bổ sung (`kanji-app/tools/extra_vi_*.txt`) và hình thành phần là phần tự soạn trong repo này.

## Nguồn và giấy phép

- Nhận diện chữ viết tay: [KanjiCanvas](https://github.com/asdfjkl/kanjicanvas) — MIT.
- Tranh gợi nhớ: [OpenMoji](https://openmoji.org) — CC BY-SA 4.0.
- Thứ tự nét và hình thành phần: [KanjiVG](http://kanjivg.tagaini.net) — Ulrich Apel, CC BY-SA 3.0.
- Âm on/kun, số nét: [KANJIDIC2](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project) — EDRDG, CC BY-SA 4.0.
