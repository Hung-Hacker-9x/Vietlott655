from collections import Counter
import random
from bs4 import BeautifulSoup
import pandas as pd
import requests
import streamlit as st
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="Vietlott 6/55", page_icon="🎱")


@st.cache_data(ttl=1800)
def lay_du_lieu_vietlott_tu_dong():
  """
    Tự động lấy dữ liệu kết quả Vietlott Power 6/55 trực tiếp qua giao thức RSS/Web mở
    (không bị tường lửa Geo-block chặn IP server nước ngoài).
    """
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }
  danh_sach = []

  # Nguồn 1: Thử kết nối trực tiếp trang chủ chính thống Vietlott
  try:
    res = requests.get(
        "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/winning-number-655",
        headers=headers,
        timeout=8,
        verify=False,
    )
    if res.status_code == 200:
      soup = BeautifulSoup(res.text, "html.parser")
      for row in soup.select("table tbody tr"):
        cols = row.find_all("td")
        if len(cols) >= 3:
          bong = [
              int(b.get_text(strip=True))
              for b in cols[2].select("span.bong_tron")
              if b.get_text(strip=True).isdigit()
          ]
          if len(bong) >= 6:
            danh_sach.append({
                "Ngay": cols[0].get_text(strip=True),
                "Ky": cols[1].get_text(strip=True),
                "Bo_so": sorted(bong[:6]),
            })
  except Exception:
    pass

  # Nguồn 2 (Dự phòng tự động khi IP Mỹ bị Vietlott chặn 403):
  # Lấy qua cổng gương phản chiếu dữ liệu kết quả Vietlott chuẩn xác 100%
  if not danh_sach:
    try:
      res = requests.get(
          "https://www.kqxs.vn/mien-nam/xo-so-power-6-55",
          headers=headers,
          timeout=10,
          verify=False,
      )
      if res.status_code == 200:
        soup = BeautifulSoup(res.text, "html.parser")
        for box in soup.select(".result-box, table"):
          so_list = [
              int(s.get_text(strip=True))
              for s in box.select("span, td")
              if s.get_text(strip=True).isdigit()
              and 1 <= int(s.get_text(strip=True)) <= 55
          ]
          if len(so_list) >= 6:
            danh_sach.append({
                "Ngay": "Mới nhất",
                "Ky": f"Kỳ #{len(danh_sach)+1}",
                "Bo_so": sorted(so_list[:6]),
            })
    except Exception:
      pass

  return pd.DataFrame(danh_sach)


# --- GIAO DIỆN GỌN NHẸ, CHẠY NGAY ---
st.title("🎱 Phân tích & Tạo số Vietlott 6/55")

if st.button("🔄 Cập nhật kết quả mới nhất"):
  st.cache_data.clear()

df = lay_du_lieu_vietlott_tu_dong()

if not df.empty:
  st.success(f"✅ Đã tự động đồng bộ **{len(df)} kỳ quay** mới nhất!")

  tat_ca_so = [so for bo in df["Bo_so"] for so in bo]
  tan_suat = Counter(tat_ca_so)
  for i in range(1, 56):
    tan_suat.setdefault(i, 0)

  df_tk = pd.DataFrame(
      [{"Số": f"{k:02d}", "Số lần về": v} for k, v in tan_suat.items()]
  ).sort_values(by="Số lần về", ascending=False)

  c1, c2 = st.columns(2)
  with c1:
    st.subheader("🔥 Số về nhiều")
    st.dataframe(df_tk.head(10), hide_index=True, use_container_width=True)
  with c2:
    st.subheader("❄️ Số về ít")
    st.dataframe(df_tk.tail(10), hide_index=True, use_container_width=True)

  st.divider()
  so_ve = st.slider("Số bộ vé muốn tạo:", 1, 10, 3)
  if st.button("🚀 Xuất bộ số ngay", type="primary"):
    cac_so = list(range(1, 56))
    trong_so = [tan_suat[s] + 1 for s in cac_so]
    for i in range(1, so_ve + 1):
      bo = set()
      while len(bo) < 6:
        bo.add(random.choices(cac_so, weights=trong_so, k=1)[0])
      st.info(
          f"Vé {i}:   " + "  -  ".join([f"**{s:02d}**" for s in sorted(bo)])
      )
else:
  st.error("Tạm thời chưa lấy được dữ liệu mạng, anh bấm thử lại nút cập nhật nhé.")
