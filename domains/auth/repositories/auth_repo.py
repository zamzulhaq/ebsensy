class AuthRepository:
    def __init__(self, db_client):
        self.db = db_client

    def create_school(self, data):
        return self.db.table('schools').insert(data).execute().data[0]

    def create_user(self, data):
        return self.db.table('users').insert(data).execute().data[0]

    def create_subscription(self, data):
        return self.db.table('subscriptions').insert(data).execute().data[0]

    def get_school_by_slug(self, slug):
        res = self.db.table('schools').select('*').eq('slug', slug).execute()
        return res.data[0] if res.data else None

    def get_user_by_email(self, email):
        res = self.db.table('users').select('*').eq('email', email).execute()
        return res.data[0] if res.data else None

    def get_trial_plan(self):
        # Ambil plan yang paling murah/basic sebagai trial
        res = self.db.table('subscription_plans').select('*').order('price', desc=False).limit(1).execute()
        return res.data[0] if res.data else None

    # Rollback helpers
    def delete_school(self, school_id):
        self.db.table('schools').delete().eq('id', school_id).execute()

    def delete_user(self, user_id):
        self.db.table('users').delete().eq('id', user_id).execute()
