# Phase 1 – B7 Database SQLite

Phase này mở rộng source hiện tại bằng database và API phân quyền tối thiểu. Chưa triển khai Batch Upload, sinh PDF, gửi email, OpenCV Measurement hay Carousel. Không train lại hoặc thay đổi pipeline EfficientNet-B0.

## 1. Kết quả và phạm vi

- 11 bảng nghiệp vụ: users, cases, case_images, analyses, analysis_results, doctor_reviews, upload_batches, reports, email_logs, site_settings, slides.
- Một bảng hạ tầng `alembic_version` để theo dõi migration.
- Tách nhận xét bác sĩ khỏi kết quả AI; một ảnh có nhiều lần phân tích; lịch sử truy qua case → image → analysis → result.
- Database và CLI chạy được mà không import PyTorch/load checkpoint.
- API đăng nhập JSON + session + CSRF để kiểm thử quyền thật. Phase này chưa có trang giao diện đăng nhập/quản trị.
- Doctor tạo case cho User; chỉ xem ca mình phụ trách. Admin đọc mọi ca và tạo ca gán Doctor. User chỉ đọc ca, analysis, review và report của mình.
- Route `/predict` cũ giữ nguyên xử lý ảnh/model, thêm kiểm tra ADMIN/DOCTOR và CSRF. User/khách không được chạy AI. Luồng lưu kết quả inference vào database sẽ tích hợp ở phase sau.
- Báo cáo có API đọc metadata và tải file đã tồn tại; không có API tạo PDF trong Phase 1.

## 2. Cài đặt – chạy tại thư mục gốc sau giải nén

Khuyến nghị Python 3.11 hoặc 3.12. Môi trường kiểm thử thực tế: Python 3.12.14.

Windows CMD:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-test.txt
copy .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Dán chuỗi vừa sinh vào `SECRET_KEY` trong `.env`. Các giá trị khác cho demo cục bộ:

```dotenv
SECRET_KEY=<chuỗi ngẫu nhiên vừa sinh>
ALLOW_DEMO_SEED=true
DEMO_PASSWORD=<mật khẩu demo tự chọn dài 12–256 ký tự>
SESSION_COOKIE_SECURE=false
```

Không ghi dấu `< >` vào giá trị thực. `.env` không được đưa vào git. Khi dùng HTTPS, đặt SESSION_COOKIE_SECURE=true. Seed chỉ dành cho dữ liệu giả lập; ALLOW_DEMO_SEED mặc định false.

Linux/macOS: thay lệnh activate bằng `source .venv/bin/activate` và copy bằng `cp .env.example .env`.

## 3. Migration và seed

Đã kèm migration ban đầu `e8e27e26f978`. Không chạy lại `db init` hoặc sinh lại migration đầu tiên.

```bat
python -m flask --app skin_cancer.webapp.database_app db upgrade
python -m flask --app skin_cancer.webapp.database_app db current
python -m flask --app skin_cancer.webapp.database_app db check
python -m flask --app skin_cancer.webapp.database_app seed-demo
python -m pytest -q
```

Database mặc định: `instance/dermascan.db`, tính theo thư mục source, không phụ thuộc nơi gọi chương trình. Có thể đặt `DATABASE_URL` thành URL SQLite tuyệt đối trong `.env`, ví dụ `sqlite:////absolute/path/to/instance/dermascan.db`. Thư mục cha của đường dẫn tùy chọn phải tồn tại.

Sau này có thay đổi models:

```bat
python -m flask --app skin_cancer.webapp.database_app db migrate -m "Mo ta thay doi schema"
python -m flask --app skin_cancer.webapp.database_app db upgrade
```

Lệnh quay lại một revision: `python -m flask --app skin_cancer.webapp.database_app db downgrade`. Với migration đầu tiên, lệnh này xóa các bảng; chỉ dùng trên DB thử nghiệm hoặc đã sao lưu. Không dùng downgrade để đổi version khi đang có dữ liệu cần giữ.

## 4. Tài khoản demo

| Email | Role |
|---|---|
| admin@dermascan.local | ADMIN |
| doctor@dermascan.local | DOCTOR |
| patient@dermascan.local | USER A |
| patient2@dermascan.local | USER B |

Mật khẩu lấy từ DEMO_PASSWORD khi tạo lần đầu. Seed lần sau giữ nguyên mật khẩu tài khoản đã có, không reset theo giá trị mới. Nếu email demo đã thuộc tài khoản khác hoặc role khác, seed dừng và rollback.

Seed tạo hai case cho hai User khác nhau, mỗi ca có ảnh mẫu/analysis/result/review giả lập, một site_settings và ba slide. Kết quả ghi `DEMO – not inference`, không gán xác suất AI giả như kết quả thật. Các đường dẫn ảnh seed trỏ đến ảnh nghiên cứu có sẵn tính từ gốc project; chưa đưa vào hệ thống upload. Không tạo Report/EmailLog giả hoặc file PDF giả. Test tự tạo bản ghi report và file fixture trong thư mục tạm để kiểm tra tải và quyền; chúng không được đóng gói.

## 5. Chạy API database độc lập

```bat
python -m flask --app skin_cancer.webapp.database_app run --host 127.0.0.1 --port 5000
```

Đây là server API, không có trang Home. Mở `http://127.0.0.1:5000/api/auth/csrf` để kiểm tra kết nối. Để thử trong Postman: GET token trước, giữ cookie session, gửi header X-CSRFToken khi POST.

Ví dụ Python chạy ở terminal khác, chỉ dùng thư viện chuẩn, không cần cài requests:

```python
import json
import getpass
import urllib.request
import http.cookiejar

base = 'http://127.0.0.1:5000'
client = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def get(path):
    return json.load(client.open(base + path))

def post(path, data):
    token = get('/api/auth/csrf')['csrf_token']
    request = urllib.request.Request(
        base + path, data=json.dumps(data).encode(),
        headers={'Content-Type': 'application/json', 'X-CSRFToken': token},
        method='POST')
    return json.load(client.open(request))

result = post('/api/auth/login', {
    'email': 'patient@dermascan.local',
    'password': getpass.getpass('Demo password: ')})
user_id = result['user']['id']
print(get(f'/api/users/{user_id}/cases'))
```

Lấy CSRF token mới sau khi login/logout vì session đã đổi. API trả 401 nếu chưa đăng nhập; 403 nếu sai role; 404 cho tài nguyên không có quyền hoặc không tồn tại, để không lộ sự tồn tại ca của người khác. CSRF thiếu/sai trả 400 trước bước kiểm tra role.

## 6. API có trong Phase 1

| Method | Route | Quyền |
|---|---|---|
| GET | /api/auth/csrf | Khởi tạo token cho session |
| POST | /api/auth/login | Email + password, CSRF |
| GET | /api/auth/me | Đã đăng nhập |
| POST | /api/auth/logout | Đã đăng nhập + CSRF |
| POST | /api/cases | Doctor/Admin; Admin phải chỉ định doctor_id |
| GET | /api/cases/<id> | Chủ sở hữu / Doctor phụ trách / Admin |
| GET | /api/users/<id>/cases | User của mình / Doctor được giao / Admin |
| GET | /api/analyses/<id> | Theo quyền case |
| GET | /api/reviews/<id> | Theo quyền case |
| GET | /api/reports/<id> | Theo quyền case |
| GET | /api/reports/<id>/download | Theo quyền case; file phải tồn tại trong REPORT_FOLDER |

Ví dụ POST case: `{"patient_user_id": 3, "lesion_location": "Cánh tay trái"}`. Với Admin thêm `doctor_id` hợp lệ. ID trong demo không nên đoán; lấy từ API hoặc database.

Chưa có endpoint batch, upload storage, sửa AI result/review, tạo báo cáo, email hoặc CRUD slides. Admin toàn quyền trong các route Phase 1 đã triển khai; UI và CRUD cho các module còn lại thuộc phase tương ứng.

## 7a. Phase 2 – B1 upload nhiều ảnh

B1 dùng schema Phase 1 hiện có, không cần migration mới. Doctor đăng nhập rồi gửi multipart request đến:

```text
POST /api/cases/<case_id>/upload-batch
```

Field bắt buộc là `images` và có thể lặp nhiều lần. Endpoint nhận JPG/JPEG/PNG/WEBP, tối đa 20 ảnh mỗi batch và tối đa 10 MiB mỗi ảnh. File hợp lệ được lưu ngoài `static/` với tên UUID; tên client chỉ được giữ làm metadata. File lỗi tạo trạng thái `FAILED` riêng, không làm hỏng các file còn lại. CSV được tạo bằng pandas trong thư mục private `instance/uploads/csv/` với 10 cột cố định theo yêu cầu B1.

Response trả `batch_id`, số lượng thành công/thất bại, trạng thái `COMPLETED`/`PARTIAL`/`FAILED` và trạng thái từng ảnh. Inference EfficientNet-B0 chưa được gọi trong B1; các trường phân tích trong CSV để trống cho phase xử lý AI tiếp theo.

CSV của batch được tải qua `GET /api/upload-batches/<batch_id>/csv` bởi Doctor phụ trách hoặc Admin. User không có quyền dùng endpoint này.

## 7b. Phase 3 – C5 khoanh vùng và đo lường

C5 dùng route:

```text
POST /api/analyses/<analysis_id>/measure
```

Pipeline độc lập gồm grayscale/blur → Otsu threshold → morphology opening/closing → `findContours` → bounding box → diện tích/chu vi/tỷ lệ. Kết quả lưu vào bảng `analyses` với đơn vị `px`, `px²` và `fraction`. Không dùng Grad-CAM làm mask và không chuyển đổi sang mm khi chưa có calibration.

Ảnh contour được lưu ngoài `static/` trong `instance/measurements/`. Nếu không tìm thấy contour, Analysis chuyển sang `FAILED` kèm `error_code=NO_CONTOUR`; API không trả lỗi 500.

## 7c. Phase 4 – U4/C4 báo cáo PDF

Doctor hoặc Admin tạo báo cáo từ dữ liệu thật trong database:

```text
POST /api/cases/<case_id>/reports
Body: {"analysis_id": <id>}
```

PDF được tạo bằng ReportLab và lưu trong `REPORT_FOLDER` theo dạng `CASE_CODE/report_vN.pdf`. Bảng `reports` chỉ lưu đường dẫn tương đối, Case, Analysis, người tạo và phiên bản. Tạo lại cùng Case sẽ tăng phiên bản `v1`, `v2`, `v3`. User chỉ được tải báo cáo của chính mình qua route download hiện có.

Nếu thiếu Doctor Review, Grad-CAM, contour hoặc file ảnh, báo cáo vẫn được tạo và hiển thị trạng thái thiếu dữ liệu; không tự tạo dữ liệu y khoa thay thế. Báo cáo luôn ghi rõ AI chỉ hỗ trợ tham khảo và không thay thế chẩn đoán chuyên môn.

## 7. Sơ đồ quan hệ và ràng buộc

| Bảng | Quan hệ chính |
|---|---|
| users | Nguồn tài khoản chung cho ba role; email UNIQUE không phân biệt hoa thường |
| cases | patient_user_id → users; doctor_id → users, hai relationship riêng |
| upload_batches | case_id → cases; doctor_id → users; reserved item_results JSON cho file bị từ chối |
| case_images | case_id → cases; (batch_id, case_id) → upload_batches; uploaded_by → users |
| analyses | (case_image_id, case_id) → case_images; case_id → cases |
| analysis_results | analysis_id → analyses; giữ kết quả AI riêng |
| doctor_reviews | case_id → cases; (analysis_id, case_id) → analyses; doctor_id → users |
| reports | case_id → cases; (analysis_id, case_id) → analyses; generated_by → users |
| email_logs | report_id → reports; sent_by → users |
| site_settings | updated_by → users; chỉ cho record id=1 |
| slides | created_by → users; kiểm tra thời gian kết thúc không trước bắt đầu |

`analysis_id` trong review/report có thể NULL để phục vụ tổng hợp theo ca. Mỗi cặp case_id/report_version là UNIQUE. File/PDF chỉ lưu đường dẫn. FK dùng RESTRICT để không xóa dây chuyền lịch sử. Foreign key bật trên mỗi kết nối, kể cả sau engine.dispose()/mở lại.

Role của patient/doctor được kiểm tra trong service tạo case; CHECK của users bảo đảm ba role hợp lệ. FK không tự xác định user nào là bác sĩ: thao tác SQL trực tiếp là quyền quản trị tin cậy, không phải API dành cho người dùng.

Phần diện tích/chu vi dùng pixel²/pixel, ratio trong [0,1]; chưa có thuật toán đo. Hai xác suất lưu riêng, không lẫn độ tin cậy binary và multiclass. Không tạo bảng riêng cho lịch sử, dark mode hoặc language.

## 7d. Phase 5 – U5 gửi email kết quả

Doctor hoặc Admin gửi PDF của một Report qua SMTP:

```text
POST /api/reports/<report_id>/email
Body: {"recipient_email": "optional", "subject": "optional"}
```

Nếu bỏ trống `recipient_email`, hệ thống dùng email của User/patient thuộc Case. Cấu hình Flask-Mail lấy từ `.env` (`MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`, `MAIL_TIMEOUT`); `.env.example` chỉ chứa placeholder, không chứa secret thật.

Mỗi lần gửi tạo log `PENDING`, sau đó chuyển thành `SENT` hoặc `FAILED`. Lỗi email, SMTP, credentials, file PDF không tồn tại hoặc email không hợp lệ không làm crash hệ thống. Gửi lại cùng Report tạo log mới và giữ lịch sử các lần gửi trước. User không có quyền gửi email.

## 7e. Phase 6 – Slide Show / Banner homepage

Homepage lấy banner từ bảng `slides`, không hard-code nội dung slide trong HTML. Public API là `GET /api/slides/active`; API lọc slide đang `is_active`, kiểm tra khung `start_at`/`end_at` nếu có, rồi sắp xếp `display_order ASC`.

Admin quản lý slide qua các route `/api/admin/slides`: thêm, xem, sửa, xóa, bật/tắt và đổi thứ tự. Doctor/User không có quyền gọi các route quản trị. `image_path` được kiểm tra path traversal, symlink và file không tồn tại trước khi phục vụ qua image endpoint.

Frontend dùng Vanilla JavaScript để render carousel từ API, tự chuyển slide sau 5 giây, có điều hướng và empty state. Khi không có slide active hoặc API lỗi, homepage vẫn giữ khu vực phân tích ảnh hoạt động bình thường.

## 8. Tích hợp với web AI cũ

Để chạy toàn bộ web, dùng môi trường AI hiện có hoặc cài `skin_cancer/webapp/requirements.txt`, sau đó chạy `python skin_cancer/webapp/app.py` từ gốc. Cần `.env` và database đã migrate.

Pipeline và checkpoint giữ nguyên. Đường dẫn model/training đã được chuyển sang project-relative và có biến môi trường tùy chọn; không phụ thuộc ổ đĩa của máy phát triển. Script legacy cũ không phải entrypoint được hỗ trợ; dùng các lệnh trực tiếp trong README gốc.

Web cũ giờ yêu cầu session Doctor/Admin để POST /predict; frontend đã bổ sung CSRF header. Chưa có trang login, nên trong bước tích hợp hiện tại có thể đăng nhập qua API cùng origin và cùng trình duyệt, hoặc chờ module UI authentication. Khi dùng Console của trang web cũ:

```javascript
const token = (await (await fetch('/api/auth/csrf')).json()).csrf_token;
await fetch('/api/auth/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json', 'X-CSRFToken': token},
  body: JSON.stringify({email: 'doctor@dermascan.local', password: prompt('Demo password')})
});
```

Không dùng token của Postman cho trình duyệt; session hai client khác nhau. Không dùng HTTP demo server để triển khai production.

## 9. Kiểm thử và giới hạn

Các test chạy trên SQLite tạm được tạo bằng migration thật, dùng login/session thật; không mock database. Bao gồm rollback dữ liệu sai, FK sau mở lại, cross-case composite FK, phân quyền hai User, Doctor khác, Admin, inactive user, CSRF, traversal/symlink và seed/migration/restart.

Test legacy /predict dùng route/decorator thật trích từ AST và nhánh validate trước inference, không load AI. Việc giữ nguyên model được kiểm tra riêng bằng so sánh AST và SHA-256 checkpoint; đây không thay thế chạy inference thực tế. Môi trường Phase 1 không cài stack AI nên không tuyên bố đã chạy model/Grad-CAM hoặc test giao diện end-to-end.

Chi tiết kết quả, phiên bản và manifest file nằm trong docs/PHASE1_TEST_RESULTS.md và docs/PHASE1_FILES.md. Design và implementation plan nằm trong docs/superpowers/.
