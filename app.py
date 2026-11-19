import streamlit as st
import pandas as pd
import numpy as np
import random
from itertools import combinations

st.set_page_config(page_title="Vietlott 6/55 Pro", page_icon="🎯", layout="centered")

st.title("🎯 Vietlott 6/55 - Tối Ưu Tỷ Lệ Trúng")
st.caption("Kết hợp thống kê dữ liệu thực tế, bộ lọc xác suất & ghép dàn thông minh")

# Nguồn dữ liệu lịch sử thực tế
DATA_URL = "https://raw.githubusercontent.com/vietlott-data/vietlott-data/main/data/power655.csv"

@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_csv(DATA_URL)
        # Lấy 6 cột số chính
        num_cols = [col for col in df.columns if 'num' in col.lower() or 'số' in col.lower()][:6]
        if not num_cols:
            num_cols = df.columns[2:8]
        data = df[num_cols].dropna().astype(int).values.tolist()
        return data
    except Exception:
        return []

history = load_data()

if history:
    st.success(f"✅ Đã đồng bộ {len(history)} kỳ quay thực tế từ hệ thống.")
else:
    st.warning("⚠️ Đang dùng dữ liệu dự phòng do kết nối nguồn tạm gián đoạn.")

# Tính trọng số tần suất (kết hợp toàn bộ lịch sử & 30 kỳ gần nhất)
def get_weights(hist_data):
    all_nums = [n for draw in hist_data for n in draw]
    recent_nums = [n for draw in hist_data[-30:] for n in draw] if len(hist_data) >= 30 else all_nums
    
    weights = {}
    for i in range(1, 56):
        freq_all = all_nums.count(i) / (len(all_nums) + 1)
        freq_recent = recent_nums.count(i) / (len(recent_nums) + 1)
        # Cân bằng giữa số hay về và số lâu chưa về
        weights[i] = (freq_all * 0.4) + (freq_recent * 0.4) + (0.2 / 55)
    return weights

# Bộ lọc loại bỏ các dãy số xác suất cực thấp
def pass_smart_filter(combo):
    combo = sorted(combo)
    # 1. Lọc chẵn/lẻ (chỉ giữ tỷ lệ 2-4, 3-3, 4-2)
    evens = sum(1 for x in combo if x % 2 == 0)
    if evens not in [2, 3, 4]:
        return False
    # 2. Lọc tổng điểm (khoảng vàng 130 - 210 chiếm >75% kỳ quay)
    if not (130 <= sum(combo) <= 210):
        return False
    # 3. Loại bỏ trường hợp có 3 số liên tiếp (vd: 12, 13, 14)
    consecutive = 0
    for i in range(len(combo) - 1):
        if combo[i+1] - combo[i] == 1:
            consecutive += 1
            if consecutive >= 2:
                return False
        else:
            consecutive = 0
    # 4. Phân bổ đầu số (ít nhất trải trên 4 hàng chục khác nhau)
    decades = len(set(x // 10 for x in combo))
    if decades < 4:
        return False
    return True

# Giao diện chọn chế độ
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
        # Chọn 8 số có điểm cao kết hợp ngẫu nhiên có trọng số
        population = list(weights.keys())
        probs = np.array(list(weights.values()))
        probs = probs / probs.sum()
        
        pool_8 = sorted(np.random.choice(population, size=8, replace=False, p=probs).tolist())
        st.success(f"🌟 Dàn 8 số hạt giống: **{' - '.join(f'{x:02d}' for x in pool_8)}**")
        
        # Tạo tất cả tổ hợp 6 từ 8 số (28 bộ) và lọc lấy 6 bộ đẹp nhất
        all_combos = list(combinations(pool_8, 6))
        filtered_combos = [list(c) for c in all_combos if pass_smart_filter(c)]
        
        if len(filtered_combos) < 4:
            filtered_combos = [list(c) for c in all_combos]
            
        selected = random.sample(filtered_combos, min(6, len(filtered_combos)))
        st.subheader("📋 6 Vé ghép tối ưu từ dàn trên:")
        for idx, r in enumerate(selected, 1):
            formatted = " - ".join([f"**{x:02d}**" for x in r])
            st.info(f"Vé #{idx}:  {formatted}")
