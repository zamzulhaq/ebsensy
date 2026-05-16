from functools import wraps
from flask import session, redirect, url_for, flash, render_template

def feature_required(feature_name):
    """
    Decorator untuk membatasi akses route berdasarkan fitur di session.
    Contoh: @feature_required("analytics")
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            features = session.get('features', {})
            
            # Cek apakah fitur aktif di plan saat ini
            if not features.get(feature_name):
                # Jika request via AJAX/API bisa return JSON, tapi di sini kita handle UI
                # Tampilkan modal/halaman upgrade
                flash(f"Fitur '{feature_name}' hanya tersedia untuk paket Premium.", "premium_lock")
                return redirect(url_for('subscriptions.pricing'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_subscription_status():
    """
    Middleware function untuk mengecek apakah subscription sudah expired.
    Bisa dipanggil di before_request.
    """
    if session.get('is_expired'):
        # Kita tidak mematikan aplikasi, hanya memberi warning
        # session['features'] sudah di-downgrade di SubscriptionService
        pass
