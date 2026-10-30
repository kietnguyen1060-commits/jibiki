"""Thêm bảng chia động từ (bang) và lưu ý (luu) cho các mẫu ngữ pháp tạo thể mới, sửa các mẫu đã rà soát.

Chạy lại được nhiều lần: ghi đè các trường bang/luu/n/ex của đúng các mẫu liệt kê dưới đây.
Cách dùng: py chia_dong_tu.py
"""
import json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "grammar.json")

NHOM = ["Nhóm", "Cách chia", "Ví dụ"]

SUA = {
    "27-1": {
        "n": "Động từ khả năng cho biết ai đó có năng lực hoặc hoàn cảnh cho phép làm V. Tân ngữ đi với を thường đổi thành が.",
        "bang": [{"t": "Cách chia thể khả năng (可能形)", "h": NHOM, "r": [
            ["I", "Thể ます: âm trước ます đổi từ hàng い sang hàng え, giữ ます",
             "書きます → 書けます ／ 話します → 話せます ／ 待ちます → 待てます ／ 泳ぎます → 泳げます ／ 買います → 買えます ／ 読みます → 読めます ／ 帰ります → 帰れます"],
            ["II", "Bỏ ます, thêm られます", "食べます → 食べられます ／ 見ます → 見られます ／ 起きます → 起きられます"],
            ["III", "Bất quy tắc", "します → できます（勉強します → 勉強できます） ／ 来ます → 来（こ）られます"]]}],
        "luu": ["Động từ khả năng chia tiếp như động từ nhóm II: 書けます → 書ける、書けない、書けた、書けて.",
                "わかります、見えます、聞こえます đã mang nghĩa khả năng nên không chia thể khả năng.",
                "Nhóm II: thể khả năng và thể bị động (bài 37) có cùng hình thức 食べられます — phân biệt bằng ngữ cảnh.",
                "Văn nói hay bỏ ら (見れる、食べれる) nhưng khi làm bài thi hãy dùng dạng chuẩn 見られる、食べられる."]},
    "31-1": {
        "n": "Thể ý chí là dạng thân mật của ～ましょう (rủ rê, đề nghị) và là phần đầu của mẫu ～ようと思っています (31-2).",
        "bang": [{"t": "Cách chia thể ý chí (意向形)", "h": NHOM, "r": [
            ["I", "Thể ます: âm trước ます đổi từ hàng い sang hàng お, bỏ ます, thêm う",
             "書きます → 書こう ／ 急ぎます → 急ごう ／ 話します → 話そう ／ 待ちます → 待とう ／ 遊びます → 遊ぼう ／ 休みます → 休もう ／ 帰ります → 帰ろう ／ 買います → 買おう"],
            ["II", "Bỏ ます, thêm よう", "食べます → 食べよう ／ 見ます → 見よう ／ 寝ます → 寝よう"],
            ["III", "Bất quy tắc", "します → しよう ／ 来ます → 来（こ）よう"]]}],
        "luu": ["Rủ rê thân mật: いっしょに 行こう (= 行きましょう). Đề nghị giúp: 手伝おうか (= 手伝いましょうか).",
                "Nói ý định của mình: Vよう と 思って います (31-2). Câu ～と思います chỉ ý định nảy ra ngay lúc nói."]},
    "33-1": {
        "n": "Thể mệnh lệnh ra lệnh trực tiếp (Làm đi!), thể cấm chỉ cấm trực tiếp (Không được làm!). Cả hai rất mạnh và thô, nên chỉ dùng trong vài tình huống nhất định (bảng dưới).",
        "bang": [
            {"t": "Cách chia thể mệnh lệnh (命令形)", "h": NHOM, "r": [
                ["I", "Thể ます: bỏ ます, âm cuối đổi từ hàng い sang hàng え",
                 "書きます → 書け ／ 急ぎます → 急げ ／ 話します → 話せ ／ 待ちます → 待て ／ 呼びます → 呼べ ／ 飲みます → 飲め ／ 帰ります → 帰れ ／ 言います → 言え"],
                ["II", "Thể ます: bỏ ます, thêm ろ", "食べます → 食べろ ／ 寝ます → 寝ろ ／ 起きます → 起きろ ／ 見ます → 見ろ"],
                ["III", "Bất quy tắc", "します → しろ（勉強します → 勉強しろ） ／ 来ます → 来い（こい）"]]},
            {"t": "Cách chia thể cấm chỉ (禁止形)", "h": NHOM, "r": [
                ["Mọi nhóm", "Thể từ điển + な", "書く → 書くな ／ 急ぐ → 急ぐな ／ 食べる → 食べるな ／ 見る → 見るな ／ する → するな ／ 来る（くる）→ 来るな"]]},
            {"t": "Khi nào dùng", "h": ["Tình huống", "Ví dụ"], "r": [
                ["Người trên (thường là nam) nói với người dưới, bố nói với con", "早く 寝ろ。 — Ngủ sớm đi!"],
                ["Giữa bạn bè nam thân thiết", "あした うちへ 来い。 — Mai qua nhà tớ!"],
                ["Khẩn cấp, không kịp nói lịch sự; ra lệnh ở công trường, khi huấn luyện", "火事だ。逃げろ！ — Cháy! Chạy đi!"],
                ["Cổ vũ thể thao (nữ cũng dùng)", "頑張れ！ — Cố lên!"],
                ["Biển báo, khẩu hiệu giao thông (cần ngắn, mạnh)", "止まれ。 — Dừng lại! ／ スピードを 出すな。 — Đừng chạy quá nhanh!"]]}],
        "luu": ["Không dùng với người trên; nữ giới hầu như không dùng, trừ khi cổ vũ.",
                "Mẹo nhớ hàng え: き→け、ぎ→げ、し→せ、ち→て、に→ね、び→べ、み→め、り→れ、い→え.",
                "Đọc đúng: 来い là こい, còn 来るな là くるな.",
                "Mệnh lệnh nhẹ hơn: Vます (bỏ ます) + なさい (書きなさい、早く 寝なさい) — bố mẹ nói với con, thầy cô với học sinh, câu lệnh trong đề thi.",
                "Đừng nhầm: 書くな (cấm: đừng viết) dùng thể từ điển; 書きな (thân mật của 書きなさい: viết đi) dùng thể ます bỏ ます."]},
    "33-5": {
        "n": "Nhờ người nghe chuyển lời tới người thứ ba. Nội dung nhắn ở thể thông thường, đặt trước と.",
        "ex": [["すみませんが、田中さんに あしたの 会議は 10時からだと 伝えて いただけませんか。", "Xin lỗi, nhắn giúp tôi với anh Tanaka là cuộc họp ngày mai bắt đầu từ 10 giờ được không ạ?"],
               ["わかりました。必ず 伝えます。", "Vâng, tôi nhất định sẽ nhắn lại."]]},
    "35-1": {
        "n": "Thể điều kiện ば nêu điều kiện cần để vế sau xảy ra: nếu A thì B.",
        "bang": [{"t": "Cách chia thể điều kiện (条件形)", "h": ["Loại từ", "Cách chia", "Ví dụ"], "r": [
            ["Động từ I", "Thể ます: âm trước ます đổi từ hàng い sang hàng え, bỏ ます, thêm ば", "書きます → 書けば ／ 急ぎます → 急げば ／ 押します → 押せば ／ 待ちます → 待てば ／ 買います → 買えば ／ 降ります → 降れば"],
            ["Động từ II", "Bỏ ます, thêm れば", "食べます → 食べれば ／ 見ます → 見れば"],
            ["Động từ III", "Bất quy tắc", "します → すれば ／ 来ます → 来（く）れば"],
            ["Phủ định", "Thể ない: bỏ い, thêm ければ", "行かない → 行かなければ ／ 食べない → 食べなければ ／ しない → しなければ"],
            ["Tính từ い", "Bỏ い, thêm ければ", "安い → 安ければ ／ いい → よければ ／ ない → なければ"],
            ["Tính từ な", "Bỏ な, thêm なら", "暇（な）→ 暇なら ／ 静か（な）→ 静かなら"],
            ["Danh từ", "Thêm なら", "雨 → 雨なら ／ 学生 → 学生なら"]]}],
        "luu": ["Khi hai vế cùng chủ ngữ và vế trước là động từ ý chí, vế sau không dùng ý chí (～たい、～ましょう、～てください); khi đó dùng ～たら.",
                "いい → よければ (không phải いければ)."]},
    "37-1": {
        "n": "Câu bị động lấy người chịu tác động (N1) làm chủ ngữ; người thực hiện (N2) đi với に.",
        "bang": [{"t": "Cách chia thể bị động (受身形)", "h": NHOM, "r": [
            ["I", "Thể ます: âm trước ます đổi từ hàng い sang hàng あ, thêm れます",
             "書きます → 書かれます ／ 呼びます → 呼ばれます ／ 踏みます → 踏まれます ／ 待ちます → 待たれます ／ 盗みます → 盗まれます ／ 叱ります → 叱られます ／ 言います → 言われます"],
            ["II", "Bỏ ます, thêm られます", "褒めます → 褒められます ／ 見ます → 見られます ／ 建てます → 建てられます"],
            ["III", "Bất quy tắc", "します → されます（招待します → 招待されます） ／ 来ます → 来（こ）られます"]]}],
        "luu": ["Âm い đổi thành わ, không phải あ: 言います → 言われます、買います → 買われます.",
                "Thể bị động chia tiếp như động từ nhóm II: 叱られる、叱られない、叱られた.",
                "Nhóm II: thể bị động và thể khả năng giống nhau (食べられます) — xem ngữ cảnh."]},
    "48-1": {
        "n": "Thể sai khiến diễn tả việc người trên bắt hoặc cho phép người dưới làm V.",
        "bang": [{"t": "Cách chia thể sai khiến (使役形)", "h": NHOM, "r": [
            ["I", "Thể ます: âm trước ます đổi từ hàng い sang hàng あ, thêm せます",
             "行きます → 行かせます ／ 急ぎます → 急がせます ／ 待ちます → 待たせます ／ 遊びます → 遊ばせます ／ 読みます → 読ませます ／ 作ります → 作らせます ／ 習います → 習わせます"],
            ["II", "Bỏ ます, thêm させます", "食べます → 食べさせます ／ 見ます → 見させます"],
            ["III", "Bất quy tắc", "します → させます（勉強します → 勉強させます） ／ 来ます → 来（こ）させます"]]}],
        "luu": ["Âm い đổi thành わ: 習います → 習わせます、言います → 言わせます.",
                "Thể sai khiến chia tiếp như nhóm II: 行かせる、行かせない、行かせた.",
                "Chỉ dùng khi người ra lệnh ở vị trí trên (bố mẹ – con, cấp trên – cấp dưới). Với người trên, dùng ～て いただきます.",
                "Người bị sai khiến: tự động từ → を (48-2); tha động từ → に, vì を đã dùng cho tân ngữ (48-3)."]},
    "49-1": {
        "n": "Dùng đúng hình thức bị động để tôn kính hành động của người trên. Mức kính trọng nhẹ, hay gặp trong văn viết, tin tức.",
        "bang": [{"t": "Cách chia (giống thể bị động)", "h": NHOM, "r": [
            ["I", "Hàng い → hàng あ + れます", "書きます → 書かれます ／ 帰ります → 帰られます ／ 読みます → 読まれます ／ 言います → 言われます"],
            ["II", "Bỏ ます + られます", "出かけます → 出かけられます ／ やめます → やめられます"],
            ["III", "Bất quy tắc", "します → されます ／ 来ます → 来（こ）られます"]]}]},
    "49-2": {
        "n": "Kính ngữ lịch sự hơn ～られます. Không dùng với động từ mà phần trước ます chỉ có một âm (見ます、寝ます、います) và với します、来ます; các động từ này dùng động từ tôn kính đặc biệt (49-3).",
        "bang": [{"t": "Cách tạo", "h": ["Loại", "Cách tạo", "Ví dụ"], "r": [
            ["Động từ thường", "お + Vます (bỏ ます) + に なります", "帰ります → お帰りに なります ／ 待ちます → お待ちに なります ／ 読みます → お読みに なります"],
            ["Động từ Hán Nhật (N します)", "ご + N + に なります", "利用します → ご利用に なります ／ 出席します → ご出席に なります"]]}]},
    "49-3": {
        "bang": [{"t": "Động từ tôn kính đặc biệt (尊敬語)", "h": ["Động từ thường", "Tôn kính ngữ", "Ví dụ"], "r": [
            ["行きます／来ます／います", "いらっしゃいます", "部長は 会議室に いらっしゃいます。"],
            ["食べます／飲みます", "召し上がります", "どうぞ 召し上がって ください。"],
            ["言います", "おっしゃいます", "先生が そう おっしゃいました。"],
            ["見ます", "ご覧に なります", "この 写真を ご覧に なりましたか。"],
            ["します", "なさいます", "週末は 何を なさいますか。"],
            ["知って います", "ご存じです", "田中さんの 住所を ご存じですか。"],
            ["くれます", "くださいます", "先生が 辞書を くださいました。"],
            ["寝ます", "お休みに なります", "社長は もう お休みに なりました。"]]}],
        "luu": ["いらっしゃいます、おっしゃいます、くださいます、なさいます: thể từ điển là ～る nhưng thể ます là ～います (không phải ～ります); thể て: いらっしゃって、おっしゃって."]},
    "50-1": {
        "n": "Khiêm nhường ngữ: hạ thấp hành động của mình (hoặc người nhà, người cùng công ty) khi hành động đó liên quan tới người trên, qua đó tỏ lòng kính trọng.",
        "bang": [{"t": "Cách tạo", "h": ["Loại", "Cách tạo", "Ví dụ"], "r": [
            ["Động từ thường", "お + Vます (bỏ ます) + します", "持ちます → お持ちします ／ 待ちます → お待ちします ／ 送ります → お送りします ／ 知らせます → お知らせします"],
            ["Động từ Hán Nhật (N します)", "ご + N + します", "案内します → ご案内します ／ 説明します → ご説明します ／ 連絡します → ご連絡します ／ 紹介します → ご紹介します"]]}],
        "luu": ["Không dùng với động từ mà phần trước ます chỉ có một âm (見ます、います); các động từ này có dạng khiêm nhường đặc biệt (50-2).",
                "Chỉ dùng khi hành động có liên quan tới người nghe/người trên: 私が お持ちします (xách cho anh). Không nói お歩きします."]},
    "50-2": {
        "bang": [{"t": "Động từ khiêm nhường đặc biệt (謙譲語)", "h": ["Động từ thường", "Khiêm nhường ngữ", "Ví dụ"], "r": [
            ["行きます／来ます", "参ります", "あした 大阪へ 参ります。"],
            ["います", "おります", "毎晩 9時まで 会社に おります。"],
            ["食べます／飲みます／もらいます", "いただきます", "先生に 本を いただきました。"],
            ["言います", "申します", "ミラーと 申します。"],
            ["します", "いたします", "わたしが ご案内いたします。"],
            ["見ます", "拝見します", "お写真を 拝見しました。"],
            ["聞きます／（nhà người trên）行きます", "伺います", "あした お宅に 伺っても よろしいですか。"],
            ["知って います／知りません", "存じて おります／存じません", "その ことは 存じて おります。"],
            ["会います", "お目に かかります", "社長に お目に かかりたいんですが。"]]}],
        "luu": ["参ります và おります cũng dùng để nói lịch sự, trang trọng về sự việc không liên quan tới người trên (丁重語): 電車が 参ります."]},
}


def main():
    g = json.load(open(PATH, encoding="utf-8"))
    by_id = {x["id"]: x for b in g.values() for x in b}
    for gid, upd in SUA.items():
        by_id[gid].update(upd)
    with open(PATH, "w", encoding="utf-8") as fh:
        fh.write("{\n")
        keys = sorted(g, key=int)
        for i, b in enumerate(keys):
            fh.write(f'"{b}": [\n')
            fh.write(",\n".join(" " + json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in g[b]))
            fh.write("\n]" + ("," if i < len(keys) - 1 else "") + "\n")
        fh.write("}\n")
    print("đã cập nhật", len(SUA), "mẫu")


main()
