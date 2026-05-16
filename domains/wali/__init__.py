from flask import Blueprint

wali_bp = Blueprint('wali', __name__, template_folder='templates')

from .routes import wali_routes
