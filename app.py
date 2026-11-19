import streamlit as st
import numpy as np
import random
import os
from itertools import combinations

st.set_page_config(page_title="Vietlott 6/55 Pro", page_icon="🎯", layout="centered")

st.title("🎯 Vietlott 6/55 - Tối Ưu Tỷ Lệ Trúng")
st.caption("Thống kê dữ liệu thực tế • Bộ lọc xác suất • Ghép dàn thông minh")

def load_local_data():
    data = []
    if os.path.exists("data.csv"):
        try:
            with open("data.csv", "r", encoding="utf-8") as f:
                for line in f:
                    parts = [int(x.strip()) for x in line.strip().split(",") if x.strip().isdigit()]
                    if len(parts) >= 6:
                        data.append(sorted(parts[:6]))
        except Exception:
            pass
    if data:
        return data
    return [
        [4, 12, 19, 27, 38, 49], [2, 15, 21, 33, 41, 52],
        [7, 11, 24, 30, 44, 55], [1, 18, 26, 35, 42, 50],
        [5, 14, 22, 29, 39, 47], [9, 16, 23, 31, 45, 53],
        [3, 13, 20, 28, 37, 48], [8, 17, 25, 34, 43, 54]
    ]

history = load_local_data()

with st.expander("➕ Cập nhật kết quả kỳ mới nhất (Tùy chọn)"):
    new_draw = st.text_input(
        "Nhập 6 số kỳ mới nhất (cách nhau dấu cách):",
        placeholder="Ví dụ: 05 14 23 31 44 52"
    )
    if new_draw.strip():
        parts = [int(x) for x in new_draw.replace(",", " ").split() if x.isdigit() and 1 <= int(x) <= 55]
        if len(set(parts)) == 6:
            history.append(sorted(parts))
            st.success("Đã cập nhật kỳ mới vào bộ tính toán!")
        else:
            st.warning("Vui lòng nhập đủ 6 số khác nhau từ 01 đến 55.")

latest_str = " - ".join(f"{x:02d}" for x in history[-1])
st.success(f"✅ Dữ liệu sẵn sàng (**{len(history)}** kỳ lưu trữ). Kỳ gần nhất: **{latest_str}**")

def get_weights(hist_data):
    all_nums = [n for draw in hist_data for n in draw]
    recent_nums = [n for draw in hist_data[-15:] for n in draw]
    weights = {}
    for i in range(1, 56):
        freq_all = all_nums.count(i) / (len(all_nums) + 1)
        freq_recent = recent_nums.count(i) / (len(recent_nums) + 1)
        weights[i] = (freq_all * 0.45) + (freq_recent * 0.40) + (0.15 / 55)
    return weights

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
    if len(set(x // 10 for x in combo)) < 4:
        return False
    return True

mode = st.radio(
    "Chọn chiến thuật tạo số:",
    ["🎲 Lọc Thông Minh (Tối ưu từng vé lẻ)", "🕸️ Ghép Bao Dàn (Tăng tỷ lệ trúng giải phụ)"]
)

if mode == "🎲 Lọc Thông Minh (Tối ưu từng vé lẻ)":
    num_tickets = st.slider("Số lượng bộ số muốn tạo:", 1, 10, 5)
    if st.button("🚀 Tạo Bộ Số Tối Ưu", use_container_width=True):
        weights = get_weights(history)
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
        weights = get_weights(history)
        population = list(weights.keys())
        probs = np.array(list(weights.values()))
        probs = probs / probs.sum()
        
        pool_8 = sorted(np.random.choice(population, size=8, replace=False, p=probs).tolist())
        st.success(f"🌟 Dàn 8 số hạt giống: **{' - '.join(f'{x:02d}' for x in pool_8)}**")
        
        all_combos = list(combinations(pool_8, 6))
        filtered_combos = [list(c) for c in all_combos if pass_smart_filter(c)]
        if len(filtered_combos) < 4:
            filtered_combos = [list(c) for c in all_combos]
            
        selected = random.sample(filtered_combos, min(6, len(filtered_combos)))
        st.subheader("📋 6 Vé ghép tối ưu từ dàn trên:")
        for idx, r in enumerate(selected, 1):
            formatted = " - ".join([f"**{x:02d}**" for x in r])
            st.info(f"Vé #{idx}:  {formatted}")
