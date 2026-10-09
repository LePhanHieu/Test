"""Explicit, transactional development seed. Does not run inference or create PDFs."""
import os
import click
from flask import current_app
from .extensions import db
from .models import User, Case, CaseImage, Analysis, AnalysisResult, DoctorReview, SiteSetting, Slide

ACCOUNTS = [
    ('admin@dermascan.local','DEMO Admin','ADMIN'),
    ('doctor@dermascan.local','DEMO Doctor','DOCTOR'),
    ('patient@dermascan.local','DEMO Patient A','USER'),
    ('patient2@dermascan.local','DEMO Patient B','USER'),
]


def seed_demo(password):
    users = {}
    try:
        for email, name, role in ACCOUNTS:
            user = db.session.scalar(db.select(User).where(User.email == email))
            if user and (user.role != role or user.full_name != name):
                raise ValueError(f'Tài khoản {email} đã tồn tại và không phải dữ liệu demo phù hợp')
            if user is None:
                user = User(email=email, full_name=name, role=role)
                user.set_password(password)
                db.session.add(user)
            users[email] = user
        db.session.flush()
        admin = users['admin@dermascan.local']; doctor = users['doctor@dermascan.local']
        for number, email in enumerate(['patient@dermascan.local','patient2@dermascan.local'], start=1):
            code = f'DEMO-CASE-{number:03d}'
            case = db.session.scalar(db.select(Case).where(Case.case_code == code))
            if case:
                if case.patient_user_id != users[email].id or case.doctor_id != doctor.id:
                    raise ValueError('Mã ca demo đã được dùng bởi dữ liệu khác')
                continue
            case = Case(case_code=code, patient=users[email], doctor=doctor,
                        lesion_location='DEMO – dữ liệu giả lập', status='ANALYZED')
            db.session.add(case); db.session.flush()
            image = CaseImage(case_id=case.id, image_path='skin_cancer/test_examples/NV_1.jpg',
                              original_filename='DEMO_NV_1.jpg', mime_type='image/jpeg',
                              file_size=0, uploaded_by=doctor.id, status='COMPLETED')
            db.session.add(image); db.session.flush()
            analysis = Analysis(case_id=case.id, case_image_id=image.id, status='COMPLETED')
            db.session.add(analysis); db.session.flush()
            db.session.add(AnalysisResult(analysis_id=analysis.id, model_name='DEMO – not inference'))
            db.session.add(DoctorReview(case_id=case.id, analysis_id=analysis.id, doctor_id=doctor.id,
                                        clinical_note='Dữ liệu giả lập để kiểm tra database, không phải kết quả AI/y khoa.'))
        if db.session.get(SiteSetting,1) is None:
            db.session.add(SiteSetting(id=1, site_name='DermaScan AI', updated_by=admin.id,
                                       footer_description='Chỉ dùng cho mục đích nghiên cứu.'))
        for number in range(1,4):
            title=f'DEMO Slide {number}'
            if db.session.scalar(db.select(Slide).where(Slide.title==title)) is None:
                db.session.add(Slide(title=title, subtitle='Dữ liệu minh họa Phase 1',
                                     image_path='skin_cancer/figures/sample_images.png',
                                     display_order=number, created_by=admin.id))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def register_seed(app):
    @app.cli.command('seed-demo')
    def command():
        if not current_app.config.get('ALLOW_DEMO_SEED'):
            raise click.ClickException('Chỉ seed development: đặt ALLOW_DEMO_SEED=true')
        password=os.getenv('DEMO_PASSWORD')
        if not password or not 12 <= len(password) <= 256:
            raise click.ClickException('Đặt DEMO_PASSWORD có 12–256 ký tự; không dùng mật khẩu production')
        try:
            seed_demo(password)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo('Demo seed hoàn tất. Tài khoản có sẵn giữ nguyên mật khẩu; chưa tạo PDF/email.')
