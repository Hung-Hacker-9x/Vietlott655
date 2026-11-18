from collections import Counter
import io
import os
import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Vietlott 6/55 Pro",
    page_icon="🎱",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
    .ball-container {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        align-items: center;
        margin: 8px 0;
    }
    .ball {
        width: 36px;
        height: 36px;
        line-height: 36px;
        text-align: center;
        border-radius: 50%;
        color: white;
        font-weight: bold;
        font-size: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .ball-normal { background: linear-gradient(135deg, #1e88e5, #1565c0); }
    .ball-locked { background: linear-gradient(135deg, #e53935, #b71c1c); border: 2px solid #ffd54f; }
    .ticket-card {
        background-color: rgba(128, 128, 128, 0.08);
        padding: 12px 15px;
        border-radius: 12px;
        margin-bottom: 10px;
        border-left: 4px solid #1e88e5;
    }
    .ticket-meta {
        font-size: 13px;
        opacity: 0.85;
        margin-top: 4px;
    }
</style>
""",
    unsafe_allow_html=True,
)

CSV_FILE = "vietlott_655.csv"

# Danh sách các nguồn dữ liệu dự phòng tự động chuyển đổi
DATA_SOURCES = [
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power655.jsonl",
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/master/data/power655.jsonl",
    "https://cdn.jsdelivr.net/gh/vietvudanh/vietlott-data@main/data/power655.jsonl",
    "https://cdn.jsdelivr.net/gh/vietvudanh/vietlott-data@master/data/power655.jsonl",
]


def update_data():
  headers = {"User-Agent": "Mozilla/5.0"}
  last_error = ""

  for url in DATA_SOURCES:
    try:
      response = requests.get(url, headers=headers, timeout=15)
      if response.status_code == 200 and len(response.text.strip()) > 100:
        df_raw = pd.read_json(io.StringIO(response.text), lines=True)
        records = []
        for _, row in df_raw.iterrows():
          nums = row.get("result", [])
          if isinstance(nums, list) and len(nums) >= 7:
            records.append({
                "Ky": int(row["id"]),
                "Ngay": str(row["date"]),
                "So1": int(nums[0]),
                "So2": int(nums[1]),
                "So3": int(nums[2]),
                "So4": int(nums[3]),
                "So5": int(nums[4]),
                "So6": int(nums[5]),
                "SoDacBiet": int(nums[6]),
            })
        if records:
          df_clean = (
              pd.DataFrame(records).sort_values(by="Ky").reset_index(drop=True)
          )
          df_clean.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
          return True, len(df_clean)
    except Exception as e:
      last_error = str(e)
      continue

  return False, last_error or "Không kết nối được tới máy chủ dữ liệu."


@st.cache_data
def load_data():
  if not os.path.exists(CSV_FILE):
    success, msg = update_data()
    if not success:
      return None, msg
  return pd.read_csv(CSV_FILE), "OK"


def is_valid_ticket(
    ticket,
    past_jackpots,
    use_filter,
    sum_range,
    even_options,
    no_consecutive,
    max_decade,
):
  if len(ticket) == 6:
    if tuple(ticket) in past_jackpots:
      return False
    if not use_filter:
      return True
    even_count = sum(1 for n in ticket if n % 2 == 0)
    if even_count not in even_options:
      return False
    if not (sum_range[0] <= sum(ticket) <= sum_range[1]):
      return False
    decades = [n // 10 for n in ticket]
    if max(Counter(decades).values()) > max_decade:
      return False
  if use_filter and no_consecutive:
    consecutive = 1
    for i in range(1, len(ticket)):
      if ticket[i] == ticket[i - 1] + 1:
        consecutive += 1
        if consecutive >= 3:
          return False
      else:
        consecutive = 1
  return True


def generate_tickets(
    df,
    num_tickets,
    ticket_size,
    strategy,
    locked_nums,
    use_filter,
    sum_range,
    even_options,
    no_consecutive,
    max_decade,
):
  cols = ["So1", "So2", "So3", "So4", "So5", "So6"]
  counts = Counter(df[cols].values.flatten())
  all_numbers = np.array(range(1, 56))
  freq_array = np.array([counts.get(n, 1) for n in all_numbers], dtype=float)

  if strategy == "Cân Bằng (Tối ưu nhất)":
    weights = np.sqrt(freq_array)
  elif strategy == "Số Nóng (Hay về nhất)":
    weights = freq_array
  elif strategy == "Số Lạnh (Lâu chưa về)":
    weights = 1.0 / freq_array
  else:
    weights = np.ones_like(freq_array)

  available_mask = np.isin(all_numbers, locked_nums, invert=True)
  avail_numbers = all_numbers[available_mask]
  avail_weights = weights[available_mask]
  probabilities = avail_weights / avail_weights.sum()

  past_jackpots = set(tuple(sorted(row)) for row in df[cols].values)
  needed = ticket_size - len(locked_nums)
  valid_tickets = []
  attempts = 0

  while len(valid_tickets) < num_tickets and attempts < 15000:
    attempts += 1
    picked = np.random.choice(
        avail_numbers, size=needed, replace=False, p=probabilities
    )
    ticket = sorted([int(x) for x in picked] + locked_nums)
    if (
        is_valid_ticket(
            ticket,
            past_jackpots,
            use_filter,
            sum_range,
            even_options,
            no_consecutive,
            max_decade,
        )
        and ticket not in valid_tickets
    ):
      valid_tickets.append(ticket)

  return valid_tickets, attempts


st.title("🎱 Vietlott 6/55 Pro")
df, status_msg = load_data()

if df is None:
  st.error(f"Không thể tải dữ liệu tự động. Chi tiết: {status_msg}")
  if st.button("🔄 Thử tải lại dữ liệu", type="primary"):
    st.cache_data.clear()
    st.rerun()
  st.stop()

latest = df.iloc[-1]
latest_str = " - ".join([f"{int(latest[f'So{i}']):02d}" for i in range(1, 7)])
c1, c2 = st.columns([3, 1])
with c1:
  st.caption(
      f"📅 Kỳ **#{int(latest['Ky'])}** ({latest['Ngay']}) | Tổng:"
      f" **{len(df):,}** kỳ"
  )
  st.markdown(
      f"**KQ mới nhất:** `{latest_str}` | ĐB:"
      f" `{int(latest['SoDacBiet']):02d}`"
  )
with c2:
  if st.button("🔄 Cập nhật", use_container_width=True):
    with st.spinner("Đang tải..."):
      ok, info = update_data()
      if ok:
        st.cache_data.clear()
        st.rerun()
      else:
        st.error(f"Lỗi: {info}")

tab_gen, tab_check, tab_stat = st.tabs(
    ["🎯 Tạo Số", "🔍 Dò Vé Lịch Sử", "📊 Thống Kê"]
)

with tab_gen:
  col_a, col_b = st.columns(2)
  with col_a:
    mode = st.selectbox(
        "Loại vé:",
        ["Vé thường (6 số)", "Bao 7 (7 số)", "Bao 8 (8 số)", "Bao 9 (9 số)"],
    )
    ticket_size = int(mode.split("(")[1].split(" ")[0])
  with col_b:
    num_tickets = st.number_input(
        "Số lượng vé:", min_value=1, max_value=15, value=5
    )

  strategy = st.selectbox(
      "Chiến thuật xác suất:",
      [
          "Cân Bằng (Tối ưu nhất)",
          "Số Nóng (Hay về nhất)",
          "Số Lạnh (Lâu chưa về)",
          "Ngẫu nhiên thuần túy",
      ],
  )
  max_lock = min(4, ticket_size - 2)
  locked_nums = st.multiselect(
      f"🔒 Khóa số yêu thích (tối đa {max_lock} số):",
      options=list(range(1, 56)),
      max_selections=max_lock,
  )

  with st.expander("⚙️ Tùy chỉnh Bộ lọc thông minh", expanded=False):
    use_filter = st.checkbox("Bật bộ lọc loại bỏ dãy số xấu", value=True)
    sum_range = st.slider(
        "Khoảng tổng điểm (áp dụng vé 6 số):", 60, 300, (115, 225)
    )
    even_options = st.multiselect(
        "Số lượng số Chẵn cho phép:",
        [0, 1, 2, 3, 4, 5, 6],
        default=[2, 3, 4],
    )
    no_consecutive = st.checkbox(
        "Chặn sảnh 3 số liên tiếp (VD: 12-13-14)", value=True
    )
    max_decade = st.slider("Tối đa số cùng đầu hàng chục:", 2, 6, 3)

  if st.button("🚀 TẠO BỘ SỐ MAY MẮN", type="primary", use_container_width=True):
    tickets, attempts = generate_tickets(
        df,
        num_tickets,
        ticket_size,
        strategy,
        locked_nums,
        use_filter,
        sum_range,
        even_options,
        no_consecutive,
        max_decade,
    )
    if not tickets:
      st.warning(
          "⚠️ Không tìm thấy bộ số phù hợp. Anh hãy nới lỏng điều kiện lọc"
          " nhé!"
      )
    else:
      st.caption(f"Đã sàng lọc qua {attempts:,} tổ hợp:")
      copy_lines = []
      for idx, t in enumerate(tickets):
        even_c = sum(1 for n in t if n % 2 == 0)
        balls_html = "".join([
            f"<div class='ball {'ball-locked' if n in locked_nums else 'ball-normal'}'>{n:02d}</div>"
            for n in t
        ])
        st.markdown(
            f"""
                <div class="ticket-card">
                    <div><strong>Vé #{idx+1}</strong></div>
                    <div class="ball-container">{balls_html}</div>
                    <div class="ticket-meta">Tổng điểm: <b>{sum(t)}</b> &nbsp;|&nbsp; Chẵn/Lẻ: <b>{even_c}/{ticket_size - even_c}</b></div>
                </div>
                """,
            unsafe_allow_html=True,
        )
        copy_lines.append(
            f"Vé {idx+1}: " + " - ".join([f"{n:02d}" for n in t])
        )
      st.text_area(
          "📋 Bảng copy nhanh đi mua vé:", "\n".join(copy_lines), height=110
      )

with tab_check:
  st.write(
      "Kiểm tra xem bộ số của anh từng trúng giải nào trong toàn bộ lịch sử"
      " quay thưởng chưa:"
  )
  check_nums = st.multiselect(
      "Chọn đúng 6 con số của anh:",
      options=list(range(1, 56)),
      max_selections=6,
  )
  if len(check_nums) == 6:
    user_set = set(check_nums)
    win_history = []
    for _, row in df.iterrows():
      main_set = {
          row["So1"],
          row["So2"],
          row["So3"],
          row["So4"],
          row["So5"],
          row["So6"],
      }
      match_count = len(user_set.intersection(main_set))
      has_special = row["SoDacBiet"] in user_set
      prize = None
      if match_count == 6:
        prize = "🏆 JACKPOT 1"
      elif match_count == 5 and has_special:
        prize = "🥈 JACKPOT 2"
      elif match_count == 5:
        prize = "🥉 Giải Nhất (40 triệu)"
      elif match_count == 4:
        prize = "🎖️ Giải Nhì (500k)"
      elif match_count == 3:
        prize = "🎫 Giải Ba (50k)"
      if prize:
        win_history.append({
            "Kỳ": int(row["Ky"]),
            "Ngày": row["Ngay"],
            "Giải thưởng": prize,
            "Bộ số kỳ đó": " - ".join(
                [f"{int(row[f'So{i}']):02d}" for i in range(1, 7)]
            ),
        })
    if win_history:
      st.success(
          f"Bộ số này từng trúng **{len(win_history)} lần** trong quá khứ!"
      )
      st.dataframe(
          pd.DataFrame(win_history).sort_values(by="Kỳ", ascending=False),
          use_container_width=True,
          hide_index=True,
      )
    else:
      st.info("Bộ số này chưa từng trúng giải nào trong lịch sử.")

with tab_stat:
  cols = ["So1", "So2", "So3", "So4", "So5", "So6"]
  counts = Counter(df[cols].values.flatten())
  sorted_freq = sorted(counts.items(), key=lambda x: x[1], reverse=True)
  c_hot, c_cold = st.columns(2)
  with c_hot:
    st.markdown("**🔥 Top 5 Số Nóng**")
    for num, cnt in sorted_freq[:5]:
      st.write(f"Số **{num:02d}**: `{cnt}` lần")
  with c_cold:
    st.markdown("**❄️ Top 5 Số Lạnh**")
    for num, cnt in sorted_freq[-5:]:
      st.write(f"Số **{num:02d}**: `{cnt}` lần")
  st.divider()
  chart_df = pd.DataFrame({
      "Số": [f"{i:02d}" for i in range(1, 56)],
      "Số lần về": [counts.get(i, 0) for i in range(1, 56)],
  }).set_index("Số")
  st.bar_chart(chart_df, color="#1e88e5")
  st.dataframe(
      df.tail(10).sort_values(by="Ky", ascending=False),
      use_container_width=True,
      hide_index=True,
  )
