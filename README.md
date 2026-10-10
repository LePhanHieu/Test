# DermaScan AI – Phân loại tổn thương da

Ứng dụng Flask dùng EfficientNet-B0 để phân loại ảnh dermoscopy, hỗ trợ
Grad-CAM, đo lường tổn thương bằng OpenCV, sinh PDF và quản lý lịch sử theo
User/Doctor/Admin.

> AI chỉ hỗ trợ tham khảo trong nghiên cứu/sàng lọc, không thay thế chẩn đoán,
> tư vấn hoặc quyết định điều trị của bác sĩ/chuyên gia y tế.

## Trạng thái project

- Database/API: SQLite + Flask-SQLAlchemy + Flask-Migrate.
- Batch upload: JPG/JPEG/PNG/WEBP, UUID filename, tối đa 20 ảnh/batch,
  10 MiB/file và 25 triệu pixel/ảnh, trạng thái từng ảnh, CSV upload và CSV
  kết quả phân tích sinh động từ database.
- Measurement: OpenCV threshold/morphology/contour/bounding box, chỉ dùng đơn vị
  pixel khi chưa có calibration.
- Report: ReportLab, dữ liệu thật từ database, version `v1`, `v2`, `v3`, file
  nằm ngoài database trong `instance/reports/`. Có thể tạo report trước Doctor
  Review; PDF sẽ hiển thị rõ trạng thái chưa có chẩn đoán.
- Email: Flask-Mail/SMTP, cấu hình từ `.env`, log `PENDING/SENT/FAILED`.
- Homepage: slide và site settings lấy từ database; slide tự chuyển và có empty state.
- Schema hiện tại gồm 11 bảng nghiệp vụ, không cần migration mới cho các phase trên.

## Cây thư mục

```text
.
├── skin_cancer/
│   ├── webapp/
│   │   ├── app.py                 # Legacy AI app: EfficientNet-B0 + Grad-CAM
│   │   ├── database_app.py        # Flask API/database app không load PyTorch
│   │   ├── models/                # SQLAlchemy models
│   │   ├── routes/                # Auth, case, upload, measurement, report, email...
│   │   ├── services/              # Access, upload, measurement, PDF, email, slides...
│   │   ├── templates/             # Homepage shell
│   │   ├── static/                # CSS/JavaScript
│   │   └── assets/                # Asset dùng chung
│   ├── notebooks/                 # Nghiên cứu, huấn luyện và phân tích local
│   ├── class_weights_bin.pt       # Class weights được version control
│   └── class_weights_mc.pt
├── src/                           # Training/inference utilities cũ
├── migrations/                    # Alembic/Flask-Migrate
├── tests/                         # Regression, route, migration và access tests
├── test_images/                   # Ảnh mẫu development
├── instance/                      # DB và file private sinh lúc chạy; không commit
├── requirements.txt               # Dependency đầy đủ, gồm AI + database
├── requirements-database.txt      # Runtime database/API nhẹ hơn
├── requirements-test.txt          # Database/API + pytest
├── .env.example
└── README.md
```

`instance/`, `.env` và database local được ignore bởi Git. Không đưa ảnh upload,
PDF, SMTP password hoặc database local lên repository.

## Database schema

Migration head hiện tại: `9d731c80a1f2_add_patient_snapshot.py`, kế tiếp
`e8e27e26f978_phase_1_eleven_database_tables.py`.

| Bảng | Nội dung chính |
|---|---|
| `users` | Tài khoản, role `ADMIN/DOCTOR/USER`, password hash |
| `cases` | Mã Case, User/bệnh nhân, Doctor phụ trách, vị trí, trạng thái |
| `case_images` | Ảnh upload, MIME, size, hash, trạng thái và lỗi từng ảnh |
| `upload_batches` | Batch upload, tổng số/thành công/thất bại, CSV và item results |
| `analyses` | Trạng thái phân tích, Grad-CAM, measurement, bounding box, contour |
| `analysis_results` | Model name, binary/multiclass prediction và probabilities |
| `doctor_reviews` | Clinical note, kết luận, khuyến nghị, trạng thái review |
| `reports` | Case/Analysis, path PDF tương đối, người tạo, report version |
| `email_logs` | Người nhận, subject, trạng thái gửi, thời gian và lỗi |
| `site_settings` | Singleton `id=1`: logo, favicon, site/footer/contact |
| `slides` | Banner, image path, thứ tự, active và lịch hiển thị |

Các file binary không được lưu trong SQLite. Foreign key SQLite được bật trên
mỗi connection; dữ liệu tham chiếu chéo giữa Case và các bản ghi liên quan được
kiểm tra bằng constraint trong migration.

## API list

Tất cả mutation cần CSRF token trong header `X-CSRFToken`. `USER` chỉ đọc dữ liệu
Case của mình; `DOCTOR` chỉ truy cập Case được giao; `ADMIN` có phạm vi toàn hệ thống.

### Authentication và Case

| Method | Endpoint | Quyền |
|---|---|---|
| GET | `/api/auth/csrf` | Public |
| POST | `/api/auth/login` | Public + CSRF |
| GET | `/api/auth/me` | Đã đăng nhập |
| POST | `/api/auth/logout` | Đã đăng nhập + CSRF |
| POST | `/api/cases` | Doctor/Admin |
| GET | `/api/cases/<case_id>` | Theo quyền Case |
| GET | `/api/users/<user_id>/cases` | Theo ownership/role |
| GET | `/api/analyses/<analysis_id>` | Theo quyền Case |
| GET | `/api/analyses/<analysis_id>/review` | Theo quyền Case |
| POST | `/api/analyses/<analysis_id>/review` | Doctor phụ trách/Admin |
| POST | `/api/analyses/<analysis_id>/review/draft` | Doctor phụ trách/Admin |
| GET | `/api/reviews/<review_id>` | Theo quyền Case |

### Upload, measurement, report và email

| Method | Endpoint | Quyền |
|---|---|---|
| POST | `/api/cases/<case_id>/upload-batch` | Doctor/Admin |
| GET | `/api/upload-batches/<batch_id>/csv` | Doctor phụ trách/Admin |
| GET | `/api/upload-batches/<batch_id>/analysis.csv` | Doctor phụ trách/Admin |
| POST | `/api/analyses/<analysis_id>/measure` | Doctor phụ trách/Admin |
| GET | `/api/analyses/<analysis_id>/contour` | Theo quyền Case |
| POST | `/api/cases/<case_id>/reports` | Doctor phụ trách/Admin |
| GET | `/api/reports/<report_id>` | Theo quyền Case |
| GET | `/api/reports/<report_id>/download` | Theo quyền Case |
| POST | `/api/reports/<report_id>/email` | Doctor phụ trách/Admin |

#### CSV kết quả phân tích theo batch

Endpoint `/api/upload-batches/<batch_id>/analysis.csv` tạo file từ trạng thái
database tại thời điểm tải xuống. Mỗi dòng là một ảnh trong batch; file upload bị
từ chối vẫn có dòng trạng thái/lỗi riêng. Với mỗi ảnh, hệ thống xuất Analysis,
AnalysisResult và DoctorReview mới nhất. Nếu bác sĩ chưa đánh giá, các cột review
được để trống.

Các nhóm cột gồm:

- Định danh/upload: batch, Case, ảnh, tên file, trạng thái, lỗi và thời gian upload.
- AI: `ai_binary_result` (`BENIGN`/`MALIGNANT`), xác suất nhị phân, lớp dự đoán,
  xác suất tám lớp `MEL/NV/BCC/AK/BKL/DF/VASC/SCC`, model và inference time.
- Đo lường: diện tích/chu vi theo pixel, tỷ lệ tổn thương và bounding box.
- Review bác sĩ: trạng thái, kết luận, ghi chú, khuyến nghị, người đánh giá và
  thời điểm cập nhật.
- Vòng đời phân tích: trạng thái, lỗi, thời điểm bắt đầu/kết thúc và tạo kết quả.

`ai_binary_result` là dự đoán của AI, không phải chẩn đoán của bác sĩ. Kết luận
lâm sàng chỉ nằm trong `doctor_conclusion`. CSV không chứa đường dẫn file nội bộ,
email bệnh nhân hoặc thông tin xác thực; mọi trường text đều được vô hiệu hóa tiền
tố công thức bảng tính.

### Slides và site settings

| Method | Endpoint | Quyền |
|---|---|---|
| GET | `/api/slides/active` | Public |
| GET | `/api/slides/<slide_id>/image` | Public, chỉ slide active |
| GET | `/api/admin/slides` | Admin |
| GET | `/api/admin/slides/<slide_id>` | Admin |
| POST | `/api/admin/slides` | Admin |
| PATCH | `/api/admin/slides/<slide_id>` | Admin |
| DELETE | `/api/admin/slides/<slide_id>` | Admin |
| POST | `/api/admin/slides/<slide_id>/toggle` | Admin |
| POST | `/api/admin/slides/reorder` | Admin |
| GET | `/api/site-settings` | Public |
| GET | `/api/site-settings/assets/<logo\|favicon>` | Public |
| PUT | `/api/admin/site-settings` | Admin |

### Legacy AI app

Khi chạy `skin_cancer.webapp.app`, ngoài các API database còn có:

| Method | Endpoint | Quyền |
|---|---|---|
| GET | `/` | Public |
| GET | `/health` | Public |
| POST | `/predict` | Doctor/Admin + CSRF + AI dependencies/checkpoints |
| POST | `/api/case-images/<case_image_id>/analyze` | Doctor phụ trách/Admin + CSRF + AI dependencies/checkpoints |

## Dependency list

- Python 3.11 hoặc 3.12.
- Database/API: Flask 3.1, Flask-SQLAlchemy, SQLAlchemy, Flask-Migrate,
  Flask-Login, Flask-WTF, Flask-Mail, Flask-Limiter, python-dotenv, pandas,
  OpenCV, ReportLab.
- AI/training: PyTorch, torchvision, timm, NumPy, Pillow, pytorch-grad-cam,
  scikit-learn, matplotlib, seaborn, gradio, tqdm.
- Test: pytest.
- `requirements.txt` là manifest đầy đủ; `requirements-test.txt` chỉ cài stack
  database/API và test, không bắt buộc PyTorch.
- `skin_cancer/webapp/requirements.txt` chỉ là compatibility manifest trỏ về
  requirements ở project root, tránh duplicate dependency list.

## Cách setup

Từ thư mục gốc project:

### Windows CMD

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-test.txt
copy .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-test.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Dán chuỗi ngẫu nhiên vào `SECRET_KEY`. Khi dùng seed development, đặt:

```dotenv
SECRET_KEY=<secret-ngau-nhien>
ALLOW_DEMO_SEED=true
DEMO_PASSWORD=<mat-khau-demo-tu-12-den-256-ky-tu>
SESSION_COOKIE_SECURE=false
```

Không commit `.env`. Khi triển khai HTTPS, đặt `SESSION_COOKIE_SECURE=true`.
Cấu hình SMTP chỉ đặt trong `.env`; không ghi username/password vào source.
Khi chạy nhiều worker, đổi `RATELIMIT_STORAGE_URI` từ `memory://` sang backend
dùng chung như Redis; memory storage chỉ phù hợp local development và test.

Muốn chạy `/predict` và AI runtime, cài thêm dependency đầy đủ:

```bash
python -m pip install -r requirements.txt
```

Đồng thời cần có:

```text
skin_cancer/checkpoints/best_binary.pth
skin_cancer/checkpoints/best_multiclass.pth
```

## Cách tạo DB

Database mặc định là `instance/dermascan.db`, được tính từ project root nên không
phụ thuộc thư mục hiện tại của process.

```bash
python -m flask --app skin_cancer.webapp.database_app db upgrade
python -m flask --app skin_cancer.webapp.database_app db current
python -m flask --app skin_cancer.webapp.database_app db check
```

Không chạy `db init` trên project đã có migration. Nếu thay đổi schema trong
tương lai, tạo migration mới rồi chạy `db upgrade`; không sửa migration đã phát hành.

## Cách chạy

### API/database app nhẹ

```bash
python -m flask --app skin_cancer.webapp.database_app run \
  --host 127.0.0.1 --port 5000
```

Mở `http://127.0.0.1:5000/api/auth/csrf` để kiểm tra server.

### Legacy AI app có giao diện và `/predict`

```bash
python -m skin_cancer.webapp.app
```

Lệnh được chạy từ project root trên máy mới; toàn bộ path nội bộ được resolve từ
`Path(__file__)`, không phụ thuộc ổ đĩa phát triển cũ. Có thể dùng
`SKIN_CANCER_BASE` và `ISIC_DATA_DIR` cho các script training/legacy khi cần.

### Seed dữ liệu demo

```bash
python -m flask --app skin_cancer.webapp.database_app seed-demo
```

Seed chỉ chạy khi `ALLOW_DEMO_SEED=true` và `DEMO_PASSWORD` hợp lệ. Seed có tính
transactional, không tạo PDF/email giả và không reset password tài khoản đã tồn tại.

## Tài khoản demo

| Email | Role |
|---|---|
| `admin@dermascan.local` | ADMIN |
| `doctor@dermascan.local` | DOCTOR |
| `patient@dermascan.local` | USER A |
| `patient2@dermascan.local` | USER B |

Mật khẩu được lấy từ `DEMO_PASSWORD` lúc seed. Đây là dữ liệu development; không
dùng các tài khoản này trong production.

## Cách test

```bash
python -m pytest -q
python -m compileall -q skin_cancer src tests
node --check skin_cancer/webapp/static/js/main.js
```

Test hiện có bao phủ migration/schema drift, password hash, CSRF,
authentication/authorization, IDOR giữa User/Doctor, temporary patient snapshot,
PDF concurrency và reviewer attribution, AI interpretation/failure audit, upload
format/size/pixel/cleanup, CSV formula injection, JSON validation, rate limiting và
vòng đời contour khi đo lại.

## Kiểm tra migration và database thủ công

```bash
python -m flask --app skin_cancer.webapp.database_app db check
python -m flask --app skin_cancer.webapp.database_app db current
```

Có thể kiểm tra SQLite bằng Python:

```python
import sqlite3

connection = sqlite3.connect('instance/dermascan.db')
print(connection.execute('PRAGMA integrity_check').fetchone())
print(connection.execute('PRAGMA foreign_key_check').fetchall())
connection.close()
```

## Limitations hiện tại

1. Batch upload và AI analysis là hai bước riêng; client gọi endpoint analyze cho
   từng `CaseImage` sau khi upload thay vì tự động chạy model cho toàn batch.
2. `/predict` legacy trả kết quả inference/Grad-CAM trực tiếp; endpoint này không
   persist kết quả. Dùng `/api/case-images/<id>/analyze` cho workflow database.
3. Measurement chỉ là pixel (`px`, `px²`, fraction), chưa quy đổi sang mm khi
   chưa có calibration.
4. AI runtime cần PyTorch, checkpoint và môi trường phù hợp; test database nhẹ
   không load PyTorch. Không xem việc test database là xác nhận inference y tế.
5. Rate limiting dùng memory storage mặc định; production nhiều worker cần shared
   storage. Repository chưa cung cấp WSGI deployment profile, security headers đầy
   đủ hoặc browser end-to-end test.
6. SMTP thật phụ thuộc cấu hình nhà cung cấp và chưa được kiểm chứng trong CI/local
   test suite hiện tại.

## Medical disclaimer

Đây là hệ thống hỗ trợ nghiên cứu và tham khảo. Kết quả AI, Grad-CAM và số đo
OpenCV không phải chẩn đoán y khoa và phải được bác sĩ/chuyên gia đánh giá độc lập.
