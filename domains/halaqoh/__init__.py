from flask import Blueprint

halaqoh_bp = Blueprint('halaqoh', __name__, template_folder='templates')

from .routes import halaqoh_routes
