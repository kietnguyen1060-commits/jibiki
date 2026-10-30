"""Thêm bảng chia (bang) và lưu ý (luu) cho các mẫu ngữ pháp N5 tạo thể mới, sửa các mẫu đã rà soát.

Chạy lại được nhiều lần: ghi đè các trường bang/luu/n/p của đúng các mẫu liệt kê dưới đây.
Cách dùng: py chia_dong_tu.py
"""
import json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "grammar.json")

NHOM = ["Nhóm", "Cách chia", "Ví dụ"]

SUA = {
    "4-2": {
        "bang": [{"t": "Bốn dạng lịch sự của động từ", "h": ["Dạng", "Đuôi", "Ví dụ"], "r": [
            ["Hiện tại / tương lai", "～ます", "行きます ／ 食べます ／ 勉強します"],
            ["Phủ định", "～ません", "行きません ／ 食べません ／ 勉強しません"],
            ["Quá khứ", "～ました", "行きました ／ 食べました ／ 勉強しました"],
            ["Quá khứ phủ định", "～ませんでした", "行きませんでした ／ 食べませんでした ／ 勉強しませんでした"]]}]},
    "4-3": {
        "n": "Dùng に với thời điểm có số (giờ, ngày, tháng, năm). Với thứ trong tuần có thể dùng hoặc bỏ に. Không dùng に với きょう、あした、きのう、毎朝、いつ…"},
    "8-1": {
        "bang": [{"t": "Tính từ ở hiện tại (lịch sự)", "h": ["Loại", "Khẳng định", "Phủ định"], "r": [
            ["Tính từ い", "高いです", "高くないです（高くありません）"],
            ["いい (ngoại lệ)", "いいです", "よくないです"],
            ["Tính từ な", "静かです", "静かじゃありません（静かではありません）"]]}],
        "luu": ["Tính từ い: bỏ い, thêm くないです. Tính từ な: bỏ な, giống danh từ.",
                "きれい、有名、嫌い là tính từ な dù kết thúc bằng い: きれいじゃありません (không nói きれくない)."]},
    "12-2": {
        "bang": [{"t": "Quá khứ của tính từ và danh từ (lịch sự)", "h": ["Loại", "Quá khứ", "Quá khứ phủ định"], "r": [
            ["Tính từ い", "暑かったです", "暑くなかったです（暑くありませんでした）"],
            ["いい (ngoại lệ)", "よかったです", "よくなかったです"],
            ["Tính từ な", "簡単でした", "簡単じゃありませんでした"],
            ["Danh từ", "雨でした", "雨じゃありませんでした"]]}],
        "luu": ["Không nói 暑いでした: quá khứ của tính từ い nằm ở đuôi かった, không ở です."]},
    "13-2": {
        "bang": [{"t": "Chia ～たい như tính từ い", "h": ["Dạng", "Ví dụ"], "r": [
            ["Khẳng định", "行きたいです"],
            ["Phủ định", "行きたくないです"],
            ["Quá khứ", "行きたかったです"],
            ["Quá khứ phủ định", "行きたくなかったです"]]}],
        "luu": ["Chỉ dùng cho mong muốn của người nói (hoặc hỏi người nghe), không nói thẳng mong muốn của người thứ ba."]},
    "14-1": {
        "n": "Thể て nối câu và là phần đầu của nhiều mẫu (～てください、～ています…). Muốn chia đúng, trước hết phải biết động từ thuộc nhóm nào.",
        "bang": [
            {"t": "Nhận biết nhóm động từ (nhìn âm ngay trước ます)", "h": ["Nhóm", "Dấu hiệu", "Ví dụ"], "r": [
                ["I", "Âm trước ます thuộc hàng い (い、き、ぎ、し、ち、に、び、み、り)", "買います ／ 書きます ／ 話します ／ 待ちます ／ 飲みます ／ 帰ります"],
                ["II", "Âm trước ます thuộc hàng え; và một số động từ hàng い cần học thuộc", "食べます ／ 寝ます ／ 見ます ／ 起きます ／ 借ります ／ 浴びます ／ います ／ できます"],
                ["III", "します, 来ます và N + します", "します ／ 来ます ／ 勉強します ／ 結婚します"]]},
            {"t": "Cách chia thể て", "h": NHOM, "r": [
                ["I: い・ち・り", "→ って", "買います → 買って ／ 待ちます → 待って ／ 帰ります → 帰って"],
                ["I: み・び・に", "→ んで", "飲みます → 飲んで ／ 遊びます → 遊んで ／ 死にます → 死んで"],
                ["I: き", "→ いて", "書きます → 書いて ／ 聞きます → 聞いて"],
                ["I: ぎ", "→ いで", "泳ぎます → 泳いで ／ 急ぎます → 急いで"],
                ["I: し", "→ して", "話します → 話して ／ 貸します → 貸して"],
                ["II", "Bỏ ます, thêm て", "食べます → 食べて ／ 見ます → 見て ／ 起きます → 起きて"],
                ["III", "Bất quy tắc", "します → して ／ 来ます → 来（き）て ／ 勉強します → 勉強して"]]}],
        "luu": ["Ngoại lệ duy nhất cần nhớ: 行きます → 行って (không phải 行いて).",
                "Mẹo nhớ nhóm I: い・ち・り → って; み・び・に → んで; き → いて; ぎ → いで; し → して."]},
    "17-1": {
        "n": "Thể ない là dạng phủ định ngắn của động từ, dùng trong nhiều mẫu (～ないでください、～なければなりません…).",
        "bang": [{"t": "Cách chia thể ない", "h": NHOM, "r": [
            ["I", "Thể ます: âm trước ます đổi từ hàng い sang hàng あ, bỏ ます, thêm ない",
             "書きます → 書かない ／ 急ぎます → 急がない ／ 話します → 話さない ／ 待ちます → 待たない ／ 遊びます → 遊ばない ／ 飲みます → 飲まない ／ 帰ります → 帰らない ／ 買います → 買わない"],
            ["II", "Bỏ ます, thêm ない", "食べます → 食べない ／ 見ます → 見ない ／ 起きます → 起きない"],
            ["III", "Bất quy tắc", "します → しない ／ 来ます → 来（こ）ない ／ 勉強します → 勉強しない"]]}],
        "luu": ["Âm い đổi thành わ, không phải あ: 買います → 買わない、会います → 会わない.",
                "あります → ない (không nói あらない).",
                "来ない đọc là こない."]},
    "18-1": {
        "n": "Thể từ điển là dạng gốc của động từ, dạng được ghi trong từ điển. Dùng trong ～ことができます、～まえに…",
        "bang": [{"t": "Cách chia thể từ điển", "h": NHOM, "r": [
            ["I", "Thể ます: âm trước ます đổi từ hàng い sang hàng う, bỏ ます",
             "書きます → 書く ／ 急ぎます → 急ぐ ／ 話します → 話す ／ 待ちます → 待つ ／ 遊びます → 遊ぶ ／ 飲みます → 飲む ／ 帰ります → 帰る ／ 買います → 買う"],
            ["II", "Bỏ ます, thêm る", "食べます → 食べる ／ 見ます → 見る ／ 起きます → 起きる"],
            ["III", "Bất quy tắc", "します → する ／ 来ます → 来（く）る ／ 勉強します → 勉強する"]]}],
        "luu": ["来る đọc là くる (khác 来ます: きます, 来ない: こない).",
                "Có động từ nhóm I tận cùng ～える／～いる trông như nhóm II: 帰る、入る、走る、知る、要る、切る. Thể ます của chúng là 帰ります、入ります… (hàng い) nên vẫn là nhóm I."]},
    "19-1": {
        "n": "Thể た là dạng quá khứ ngắn. Chia giống hệt thể て, chỉ đổi て → た và で → だ.",
        "bang": [{"t": "Cách chia thể た", "h": NHOM, "r": [
            ["I: い・ち・り", "→ った", "買います → 買った ／ 待ちます → 待った ／ 帰ります → 帰った"],
            ["I: み・び・に", "→ んだ", "飲みます → 飲んだ ／ 遊びます → 遊んだ ／ 死にます → 死んだ"],
            ["I: き", "→ いた", "書きます → 書いた（行きます → 行った）"],
            ["I: ぎ", "→ いだ", "泳ぎます → 泳いだ"],
            ["I: し", "→ した", "話します → 話した"],
            ["II", "Bỏ ます, thêm た", "食べます → 食べた ／ 見ます → 見た"],
            ["III", "Bất quy tắc", "します → した ／ 来ます → 来（き）た"]]}]},
    "20-2": {
        "n": "Thể thông thường có bốn dạng cho mỗi loại từ. Dạng này được dùng trong hội thoại thân mật và làm phần đầu của nhiều mẫu ngữ pháp (～と思います、～でしょう…).",
        "bang": [{"t": "Bảng thể thông thường", "h": ["Loại", "Hiện tại", "Hiện tại phủ định", "Quá khứ", "Quá khứ phủ định"], "r": [
            ["Động từ", "行く", "行かない", "行った", "行かなかった"],
            ["あります", "ある", "ない", "あった", "なかった"],
            ["Tính từ い", "大きい", "大きくない", "大きかった", "大きくなかった"],
            ["いい", "いい", "よくない", "よかった", "よくなかった"],
            ["Tính từ な", "きれいだ", "きれいじゃない", "きれいだった", "きれいじゃなかった"],
            ["Danh từ", "雨だ", "雨じゃない", "雨だった", "雨じゃなかった"]]}],
        "luu": ["Quá khứ phủ định: đổi ない → なかった (行かない → 行かなかった).",
                "Trong câu hỏi thân mật, danh từ và tính từ な thường bỏ だ: あした 暇？"]},
    "24-5": {"p": "N（người）が V (hỏi, trả lời về người làm)"},
    "25-1": {
        "bang": [{"t": "Cách tạo ～たら", "h": ["Loại", "Khẳng định", "Phủ định"], "r": [
            ["Động từ", "行ったら（thể た + ら）", "行かなかったら"],
            ["Tính từ い", "安かったら ／ いい → よかったら", "安くなかったら"],
            ["Tính từ な", "暇だったら", "暇じゃなかったら"],
            ["Danh từ", "雨だったら", "雨じゃなかったら"]]}]},
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
