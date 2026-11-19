import streamlit as st
import pandas as pd
import numpy as np
import requests
import re
import random
from itertools import combinations

st.set_page_config(page_title="Vietlott 6/55 Pro", page_icon="🎯", layout="centered")

st.title("🎯 Vietlott 6/55 - Tối Ưu Tỷ Lệ Trúng")
st.caption("Kết hợp thống kê dữ liệu thực tế, bộ lọc xác suất & ghép dàn thông minh")

@st.cache_data(ttl=1800)
def load_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # Nguồn 1: Kho dữ liệu mở Vietlott Power 6/55 (JSONL)
    jsonl_urls = [
        "https://raw.githubusercontent.com/vietlott-data/vietlott-data/main/data/power655.jsonl",
        "https://raw.githubusercontent.com/vietlott-data/vietlott-data/master/data/power655.jsonl"
    ]
    for url in jsonl_urls:
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                df = pd.read_json(res.text, lines=True)
                if "result" in df.columns:
                    # Lấy 6 số chính từ cột result
                    data = [sorted([int(x) for x in r[:6]]) for r in df["result"].dropna() if len(r) >= 6]
                    if len(data) > 50:
                        return data, "Kho dữ liệu lịch sử toàn kỳ"
        except Exception:
            continue

    # Nguồn 2: Cào trực tiếp các kỳ quay mới nhất từ kết quả xổ số web
    try:
        res = requests.get("https://xskt.com.vn/xs-power-655", headers=headers, timeout=8)
        if res.status_code == 200:
            # Tìm chuỗi 6 cặp số từ 01-55
            blocks = re.findall(r'((?:\b(?:0[1-9]|[1-4][0-9]|5[0-5])\b[\s\-]+){5}\b(?:0[1-9]|[1-4][0-9]|5[0-5])\b)', res.text)
            data = []
            for b in blocks:
                nums = sorted([int(x) for x in re.findall(r'\d{2}', b)])
                if len(set(nums)) == 6:
                    data.append(nums)
            if len(data) >= 5:
                return data[::-1], "Kết quả trực tiếp từ XSKT"
    except Exception:
        pass

    return [], ""

history, source_name = load_data()

if history:
    latest_str = " - ".join(f"{x:02d}" for x in history[-1])
    st.success(f"✅ Đã đồng bộ **{len(history)}** kỳ thực tế ({source_name}).\n\nKỳ mới nhất ghi nhận: **{latest_str}**")
else:
    st.error("❌ Không thể kết nối máy chủ dữ liệu. Anh hãy bấm 'Manage app' -> 'Reboot app' để thử lại.")

# Tính trọng số tần suất (kết hợp toàn bộ lịch sử & 30 kỳ gần nhất)
def get_weights(hist_data):
    all_nums = [n for draw in hist_data for n in draw]
    recent_nums = [n for draw in hist_data[-30:] for n in draw] if len(hist_data) >= 30 else all_nums
    
    weights = {}
    for i in range(1, 56):
        freq_all = all_nums.count(i) / (len(all_nums) + 1)
        freq_recent = recent_nums.count(i) / (len(recent_nums) + 1)
        # Cân bằng giữa số hay về và số lâu chưa về
        weights[i] = (freq_all * 0.45) + (freq_recent * 0.40) + (0.15 / 55)
    return weights

# Bộ lọc loại bỏ các dãy số xác suất cực thấp
def pass_smart_filter(combo):
    combo = sorted(combo)
    evens = sum(1 for x in combo if x % 2 == 0)
    if evens not in [2, 3, 4]:
        return False
    if not (130 <= sum(combo) <= 210):
        return False
    consecutive = 0
    for i in range(len(combo) - 1):
        if combo[i+1] - combo[i] == 1:
            consecutive += 1
            if consecutive >= 2:
                return False
        else:
            consecutive = 0
    decades = len(set(x // 10 for x in combo))
    if decades < 4:
        return False
    return True

mode = st.radio(
    "Chọn chiến thuật tạo số:",
    ["🎲 Lọc Thông Minh (Tối ưu từng vé lẻ)", "🕸️ Ghép Bao Dàn (Tăng tỷ lệ trúng giải phụ)"]
)

if mode == "🎲 Lọc Thông Minh (Tối ưu từng vé lẻ)":
    num_tickets = st.slider("Số lượng bộ số muốn tạo:", 1, 10, 5)
    
    if st.button("🚀 Tạo Bộ Số Tối Ưu", use_container_width=True):
        weights = get_weights(history) if history else {i: 1 for i in range(1, 56)}
        population = list(weights.keys())
        probs = np.array(list(weights.values()))
        probs = probs / probs.sum()
        
        results = []
        attempts = 0
        while len(results) < num_tickets and attempts < 5000:
            attempts += 1
            pick = sorted(np.random.choice(population, size=6, replace=False, p=probs).tolist())
            if pass_smart_filter(pick) and pick not in results:
                results.append(pick)
        
        st.subheader("🎯 Các bộ số đã vượt qua bộ lọc:")
        for idx, r in enumerate(results, 1):
            formatted = " - ".join([f"**{x:02d}**" for x in r])
            st.info(f"Vé #{idx}:  {formatted}  *(Tổng: {sum(r)})*")

else:
    st.write("Hệ thống chọn ra **8 số sáng giá nhất** và ghép thành các bộ 6 số có độ phủ cao nhất.")
    if st.button("🕸️ Tạo Dàn Ghép 8 Số", use_container_width=True):
        weights = get_weights(history) if history else {i: 1 for i in range(1, 56)}
        population = list(weights.keys())
        probs = np.array(list(weights.values()))
        probs = probs / probs.sum()
        
        pool_8 = sorted(np.random.choice(population, size=8, replace=False, p=probs).tolist())
        st.success(f"🌟 Dàn 8 số hạt giống: **{' - '.join(f'{x:02d}' for x in pool_8)}**")
        
        all_combos = list(combinations(pool_8, 6))
        filtered_combos = [list(c) for c in all_combos if pass_smart_filter(c)]
        
