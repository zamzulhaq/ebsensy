from flask import Blueprint, render_template

landing_bp = Blueprint('landing', __name__)

@landing_bp.route('/')
def index():
    return render_template('landing/index.html')

@landing_bp.route('/features')
def features():
    return render_template('landing/features.html')

@landing_bp.route('/pricing')
def pricing():
    return render_template('landing/pricing.html')
