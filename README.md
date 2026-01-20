# 🏭 HỆ THỐNG QUẢN TRỊ KHO THIẾT BỊ LIÊN MIỀN (WAREHOUSE V1.0)

![Status](https://img.shields.com/badge/Status-Developing-yellow)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Framework](https://img.shields.io/badge/Framework-Streamlit-red)

## 📖 Tổng quan
Project này được tách riêng để quản lý chuyên sâu luồng luân chuyển thiết bị giữa các chi nhánh (Đà Nẵng & Miền Bắc). Hệ thống tự động xử lý logic nhận máy, trả máy và loại biên tài sản thanh lý.

## 🚀 Tính năng nổi bật
- **Hợp nhất dữ liệu:** Tự động gộp dữ liệu từ các chi nhánh khác nhau về một màn hình duy nhất.
- **Tính toán thực tế:** KPI "Tổng máy nhận" tự động trừ đi các máy đã xác nhận "Thanh lý".
- **Theo dõi trạng thái:** Phân loại máy theo 3 mức độ (Đang sửa - Đã trả - Thanh lý).

## 🛠 Hướng dẫn triển khai

### 1. Cài đặt môi trường
Cài đặt các thư viện cần thiết để chạy App:
```bash
pip install streamlit pandas plotly
