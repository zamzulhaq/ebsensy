from flask import Blueprint

academic_bp = Blueprint('academic', __name__, template_folder='../../templates/academic')

from domains.academic.routes import academic_routes
