# 字引 Jibiki

App chạy trên máy để tra kanji bằng chữ viết tay, xem thẻ kiểu Kanji Look and Learn, làm bộ đề Minna N5/N4 và học thẻ Anki.

## Mở app

1. Mở Anki (đã cài add-on AnkiConnect, mã `2055492159`).
2. Bấm đúp `start.bat`. Trình duyệt sẽ mở `http://localhost:8780`.

Tra cứu và bộ đề Minna dùng được cả khi Anki đóng. Phần học thẻ, lịch ôn và sửa cách nhớ cần Anki đang mở.

## Đồng bộ với Anki

Anki là nơi giữ dữ liệu duy nhất. App không có cơ sở dữ liệu thẻ riêng:

- Danh sách deck, số thẻ mới, đang học, đến hạn lấy trực tiếp từ Anki.
- Khi học, app điều khiển chính trình ôn tập của Anki (`guiDeckReview`, `guiCurrentCard`, `guiShowAnswer`, `guiAnswerCard`): Anki chọn thẻ, app hiển thị và gửi nút bạn bấm. Thứ tự thẻ, giới hạn mỗi ngày, bước học, FSRS, khoảng ôn trên từng nút và thời gian trả lời đều do Anki tính, giống hệt học trong Anki. Cửa sổ Anki sẽ chuyển sang màn hình ôn tập trong lúc học; bấm "Dừng" để đưa Anki về danh sách deck.
- Không chấm thẻ lẻ ngoài thứ tự: từ Anki 23.10 (bộ lập lịch v3) chỉ thẻ đứng đầu hàng đợi mới chấm được, nên nút trên thẻ kanji mở bài KLL chứa chữ đó.
- Sửa "Cách nhớ" trên thẻ kanji ghi thẳng vào ghi chú Anki; sửa trong Anki thì app thấy ngay lần mở thẻ sau.
- Nút "Đồng bộ AnkiWeb" gọi lệnh đồng bộ của Anki để đưa sang điện thoại.

AnkiConnect chỉ nhận yêu cầu từ `http://localhost:8780` (cấu hình `webCorsOriginList` trong add-on).

## Cập nhật dữ liệu tra cứu

Nội dung thẻ kanji (nghĩa, Hán Việt, ví dụ, từ ghép, câu) được trích từ bộ sưu tập Anki vào `app/data/app-data.js`. Sau khi thêm hoặc sửa nhiều ghi chú trong Anki, chạy lại:

```
py tools/build_data.py "<đường dẫn collection.anki2 (bản sao)>" _dl/kanjivg/kanjivg.xml.gz _dl/kanjicanvas/kanjicanvas-master/docs/resources/javascript/ref-patterns.js
```

## Hình thành phần và kanji bổ sung

- `tools/make_tranh.py` vẽ hình kiểu sách: tranh nét OpenMoji → chữ kanji (`kll_pic_<mã>.svg`). Tranh cho từng chữ chọn trong `tools/tranh.txt` (`chữ|emoji…`).
- `tools/make_images.py` vẽ cho mỗi chữ hai hình SVG từ KanjiVG: thành phần ghép (`kll_comp_<mã>.svg`, ví dụ 彳 + 夋 → 後) và dải thứ tự nét (`kll_stroke_<mã>.svg`).
- `tools/anki_update.py` đưa hình vào Anki: thêm trường "Hình" và "Nét viết", tải ảnh vào thư mục media, đổi mặt sau thẻ thành bố cục giống trang sách, và thêm 392 kanji có trong từ vựng Minna mà Kanji Look and Learn không có (deck `Kanji Look and Learn::4. Bổ sung từ Minna`, số `+1`, `+2`…).
- Nghĩa, âm Hán Việt và cách nhớ của chữ bổ sung nằm ở `tools/extra_vi_*.txt` (`chữ|HÁN VIỆT|nghĩa|cách nhớ`), soạn theo kiểu Look and Learn dựa trên các thành phần, không chép từ sách.

## Nguồn và giấy phép

- Nhận diện chữ viết tay: [KanjiCanvas](https://github.com/asdfjkl/kanjicanvas) — MIT (`app/lib/kanjicanvas/LICENSE.txt`).
- Tranh gợi nhớ: [OpenMoji](https://openmoji.org) — CC BY-SA 4.0.
- Thứ tự nét và hình thành phần: [KanjiVG](http://kanjivg.tagaini.net) — Ulrich Apel, CC BY-SA 3.0.
- Âm on/kun và số nét của chữ bổ sung: [KANJIDIC2](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project) — EDRDG, CC BY-SA 4.0.
- Nội dung kanji, từ ghép, câu ví dụ và từ vựng: các deck Anki của bạn.
