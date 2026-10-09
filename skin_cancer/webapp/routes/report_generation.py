from flask import Blueprint, abort, current_app, jsonify, request
from flask_login import current_user

from ..extensions import db
from ..models import Analysis
from ..services.access import require_roles, visible_case_or_404
from ..services.report_service import ReportService


bp = Blueprint('report_generation', __name__, url_prefix='/api')


@bp.post('/cases/<int:case_id>/reports')
@require_roles('ADMIN', 'DOCTOR')
def create_report(case_id):
    case = visible_case_or_404(case_id)
    payload = request.get_json(silent=True) or {}
    analysis_id = payload.get('analysis_id')
    if type(analysis_id) is not int or analysis_id <= 0:
        abort(400, description='Cần cung cấp analysis_id hợp lệ')
    analysis = db.session.get(Analysis, analysis_id)
    if not analysis or analysis.case_id != case.id:
        abort(404)

    report = ReportService(current_app).generate(case, analysis, current_user)
    return jsonify(
        id=report.id,
        case_id=report.case_id,
        analysis_id=report.analysis_id,
        report_version=report.report_version,
        pdf_path=report.pdf_path,
        download_url=f'/api/reports/{report.id}/download',
    ), 201
