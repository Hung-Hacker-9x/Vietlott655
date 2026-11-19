from collections import Counter
import os
import random
import time
from bs4 import BeautifulSoup
import pandas as pd
import requests
import streamlit as st
import urllib3

# Tắt cảnh báo chứng chỉ SSL khi gọi trực tiếp tới vietlott.vn
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Vietlott 6/55 Auto-Data", page_icon="🎱")

FILE_DATA = "vietlott_data.csv"
URL_VIETLOTT = (
    "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/winning-number-655"
)


def doc_du_lieu_luu_tru():
  """Đọc kho dữ liệu lịch sử đã lưu từ các lần cập nhật trước."""
  if os.path.exists(FILE_DATA):
    try:
      df = pd.read_csv(FILE_DATA, dtype={"Ky": str})
      # Chuyển cột Bo_so từ chuỗi "01-02-03-04-05-06" về list số nguyên [1, 2, 3, 4, 5, 6]
      df["Bo_so"] = df["Bo_so"].apply(
          lambda x: [int(i) for i in str(x).split("-")]
      )
      return df
    except Exception:
      return pd.DataFrame()
  return pd.DataFrame()


def luu_du_lieu(df):
  """Lưu toàn bộ dữ liệu đã cập nhật xuống file CSV làm kho dữ liệu gốc."""
  df_save = df.copy()
  df_save["Bo_so"] = df_save["Bo_so"].apply(
      lambda lst: "-".join([f"{int(i):02d}" for i in lst])
  )
  df_save.to_csv(FILE_DATA, index=False, encoding="utf-8-sig")


def cap_nhat_tu_vietlott(df_cu, so_trang_khoi_tao=40):
  """
    Tự động kết nối vietlott.vn:
    - Nếu đã có data cũ: Chỉ tải các trang đầu cho đến khi gặp kỳ quay đã lưu -> Dừng ngay (siêu nhanh).
    - Nếu chưa có data cũ: Quét sâu theo số trang khởi tạo để xây kho data ban đầu.
    """
  session = requests.Session()
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "vi-VN,vi;q=0.9",
      "Referer": URL_VIETLOTT,
  }

  cac_ky_da_co = set(df_cu["Ky"].astype(str)) if not df_cu.empty else set()
  so_trang_quet = 10 if cac_ky_da_co else so_trang_khoi_tao

  du_lieu_moi = []
  da_cham_ky_cu = False
  thanh_tien_trinh = st.progress(
      0, text="Đang kiểm tra kỳ quay mới trên vietlott.vn..."
  )

  try:
    res = session.get(URL_VIETLOTT, headers=headers, timeout=15, verify=False)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    for page in range(1, so_trang_quet + 1):
      thanh_tien_trinh.progress(
          page / so_trang_quet,
          text=(
              f"Đang quét trang {page}/{so_trang_quet} trên vietlott.vn (Tìm"
              f" thấy {len(du_lieu_moi)} kỳ mới)..."
          ),
      )

      rows = soup.select("table tbody tr")
      if not rows:
        break

      so_ky_trang_nay = 0
      for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 3:
          ngay = cols[0].get_text(strip=True)
          ky = cols[1].get_text(strip=True)
          bong = [
              int(b.get_text(strip=True))
              for b in cols[2].select("span.bong_tron")
              if b.get_text(strip=True).isdigit()
          ]

          if len(bong) >= 6:
            so_ky_trang_nay += 1
            # Nếu kỳ này đã tồn tại trong kho data -> Báo hiệu dừng quét
            if ky in cac_ky_da_co:
              da_cham_ky_cu = True
              continue

            du_lieu_moi.append({
                "Ngay": ngay,
                "Ky": ky,
                "Bo_so": sorted(bong[:6]),
                "Dac_biet": bong[6] if len(bong) > 6 else None,
            })

      if so_ky_trang_nay == 0 or da_cham_ky_cu:
        break

      # Chuyển sang trang tiếp theo trên web Vietlott
      viewstate = soup.find("input", {"id": "__VIEWSTATE"})
      eventvalidation = soup.find("input", {"id": "__EVENTVALIDATION"})
      viewstategen = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})

      if not viewstate or not eventvalidation:
        break

      payload = {
          "__EVENTTARGET": "ctl00$ContentPlaceHolder1$Pager1",
          "__EVENTARGUMENT": str(page + 1),
          "__VIEWSTATE": viewstate["value"],
          "__EVENTVALIDATION": eventvalidation["value"],
          "__VIEWSTATEGENERATOR": (
              viewstategen["value"] if viewstategen else ""
          ),
      }

      time.sleep(0.25)
      res = session.post(
          URL_VIETLOTT, data=payload, headers=headers, timeout=15, verify=False
      )
      soup = BeautifulSoup(res.text, "html.parser")

    thanh_tien_trinh.empty()

    # Ghép dữ liệu mới lên đầu dữ liệu cũ và lưu lại thành kho data chuẩn
    if du_lieu_moi:
      df_moi = pd.DataFrame(du_lieu_moi)
      df_tong = pd.concat([df_moi, df_cu], ignore_index=True)
      df_tong = df_tong.drop_duplicates(subset=["Ky"]).sort_values(
          by="Ky", ascending=False
      )
      luu_du_lieu(df_tong)
      return df_tong, len(du_lieu_moi), None

    return df_cu, 0, None

  except Exception as e:
    thanh_tien_trinh.empty()
    return df_cu, 0, str(e)


# --- GIAO DIỆN CHÍNH ---
st.title("🎱 Hệ thống Tự Động Cập Nhật & Phân Tích Vietlott 6/55")

# 1. Đọc kho dữ liệu hiện có
df_kho = doc_du_lieu_luu_tru()

# 2. Tự động đồng bộ kỳ mới từ vietlott.vn mỗi khi mở app (cache 30 phút để tránh spam)
@st.cache_data(ttl=1800, show_spinner=False)
def dong_bo_tu_dong():
  df_hien_tai = doc_du_lieu_luu_tru()
  return cap_nhat_tu_vietlott(df_hien_tai, so_trang_khoi_tao=40)


# Cho phép ép cập nhật ngay lập tức bằng nút bấm
col_btn1, col_btn2 = st.columns([2, 1])
with col_btn1:
  if st.button("🔄 Đồng bộ kỳ quay mới ngay bây giờ", use_container_width=True):
    st.cache_data.clear()

df_data, so_ky_moi, loi_ket_noi = dong_bo_tu_dong()

with col_btn2:
  if not df_data.empty:
    # Cho phép tải file data CSV về máy bất cứ lúc nào
    csv_bytes = df_data.to_csv(index=False, encoding="utf-8-sig").encode(
        "utf-8-sig"
    )
    st.download_button(
        label="📥 Tải file Data (.csv)",
        data=csv_bytes,
        file_name="vietlott655_data.csv",
        mime="text/csv",
        use_container_width=True,
    )

# Thông báo trạng thái đồng bộ dữ liệu
if loi_ket_noi:
  st.warning(
      f"⚠️ Không thể kết nối tới vietlott.vn lúc này ({loi_ket_noi}). Đang sử"
      " dụng kho dữ liệu đã lưu gần nhất."
  )
elif so_ky_moi > 0:
  st.success(
      f"🎉 Đã tự động cập nhật thêm **{so_ky_moi} kỳ quay mới** từ"
      f" vietlott.vn! Tổng kho dữ liệu: **{len(df_data)} kỳ**."
  )
elif not df_data.empty:
  st.info(
      f"✅ Dữ liệu đã ở trạng thái mới nhất (**{len(df_data)} kỳ quay** | Kỳ"
      f" gần nhất: **#{df_data.iloc[0]['Ky']}** ngày {df_data.iloc[0]['Ngay']})."
  )

# --- PHÂN TÍCH TRÊN KHO DATA ĐÃ ĐỒNG BỘ ---
if not df_data.empty:
  st.divider()

  # Tùy chọn phạm vi dữ liệu phân tích
  pham_vi = st.radio(
      "Chọn phạm vi dữ liệu để chạy thống kê:",
      options=[
          "Toàn bộ kho dữ liệu",
          "100 kỳ gần nhất",
          "50 kỳ gần nhất",
          "20 kỳ gần nhất",
      ],
      horizontal=True,
  )

  if pham_vi == "100 kỳ gần nhất":
    df_phan_tich = df_data.head(100)
  elif pham_vi == "50 kỳ gần nhất":
    df_phan_tich = df_data.head(50)
  elif pham_vi == "20 kỳ gần nhất":
    df_phan_tich = df_data.head(20)
  else:
    df_phan_tich = df_data

  # Tính tần suất xuất hiện của 55 con số
  tat_ca_so = [so for bo in df_phan_tich["Bo_so"] for so in bo]
  tan_suat = Counter(tat_ca_so)
  for i in range(1, 56):
    tan_suat.setdefault(i, 0)

  df_tan_suat = pd.DataFrame([
      {
          "Số": f"{k:02d}",
          "Số lần về": v,
          "Tỷ lệ (%)": round(v / len(df_phan_tich) * 100, 1),
      }
      for k, v in tan_suat.items()
  ]).sort_values(by="Số lần về", ascending=False)

  c1, c2 = st.columns(2)
  with c1:
    st.subheader("🔥 Top 10 số về nhiều nhất")
    st.dataframe(df_tan_suat.head(10), hide_index=True, use_container_width=True)
  with c2:
    st.subheader("❄️ Top 10 số về ít nhất")
    st.dataframe(df_tan_suat.tail(10), hide_index=True, use_container_width=True)

  st.divider()
  st.subheader("🎯 Xuất bộ số dựa trên dữ liệu đã cập nhật")
  so_ve = st.slider("Số lượng bộ vé muốn tạo:", 1, 10, 3)

  if st.button("🚀 Chạy phân tích & Tạo bộ số", type="primary"):
    cac_so = list(range(1, 56))
    trong_so = [tan_suat[s] + 1 for s in cac_so]

    for idx in range(1, so_ve + 1):
      bo_chon = set()
      while len(bo_chon) < 6:
        bo_chon.add(random.choices(cac_so, weights=trong_so, k=1)[0])
      chuoi_so = "  -  ".join([f"**{s:02d}**" for s in sorted(bo_chon)])
      st.success(f"Bộ số {idx}:   {chuoi_so}")

  with st.expander(f"📋 Xem toàn bộ kho dữ liệu ({len(df_data)} kỳ quay)"):
    df_hien_thi = df_data.copy()
    df_hien_thi["Bo_so"] = df_hien_thi["Bo_so"].apply(
        lambda lst: " - ".join([f"{s:02d}" for s in lst])
    )
    st.dataframe(df_hien_thi, hide_index=True, use_container_width=True)
else:
  st.error(
      "Chưa có dữ liệu trong kho và không kết nối được tới vietlott.vn. Anh"
      " thử bấm nút 'Đồng bộ kỳ quay mới ngay bây giờ' hoặc kiểm tra lại kết"
      " nối mạng nhé."
  )
