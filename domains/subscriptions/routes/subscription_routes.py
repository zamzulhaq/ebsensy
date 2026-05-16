from flask import Blueprint, render_template, session, redirect, url_for
from domains.subscriptions.repositories.subscription_repo import SubscriptionRepository
from domains.subscriptions.services.subscription_service import SubscriptionService

subscriptions_bp = Blueprint('subscriptions', __name__, template_folder='../templates')

def get_sub_service():
    from app import admin_supabase
    repo = SubscriptionRepository(admin_supabase)
    return SubscriptionService(repo)

@subscriptions_bp.route('/pricing')
def pricing():
    service = get_sub_service()
    plans = service.get_pricing_data()
    return render_template('subscriptions/pricing.html', plans=plans)

@subscriptions_bp.route('/upgrade/<plan_id>')
def upgrade(plan_id):
    # Logika integrasi payment gateway (Stripe/Midtrans) akan di sini
    # Untuk sekarang kita simulasi sukses
    return render_template('subscriptions/upgrade_modal.html', plan_id=plan_id)
