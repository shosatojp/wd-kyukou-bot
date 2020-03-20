config = {
    "url_prefix": "https://kyukou.monoid.app",
    "mongo_url": "mongodb://mongo:27017/",
    "port": 5426,
    "line": {
        "__ENV__access_token": "KYUKOU_LINE_ACCESS_TOKEN",
        "__ENV__channel_secret": "KYUKOU_LINE_CHANNEL_SECRET",
        "__ENV__channel_id": "KYUKOU_LINE_CHANNEL_ID",
    },
    "line_notify": {
        "__ENV__client_id": "KYUKOU_LINE_NOTIFY_client_ID",
        "__ENV__client_secret": "KYUKOU_LINE_NOTIFY_client_SECRET",
        "redirect_uri": "/api/v1/line/notify"
    },
    "twitter": {
        "callback_path": "/api/v1/twitter/callback",
        "webhook_path": "/api/v1/twitter/webhook",
        "__ENV__consumer_key": "KYUKOU_TWITTER_CONSUMER_KEY",
        "__ENV__consumer_key_secret": "KYUKOU_TWITTER_CONSUMER_KEY_SECRET",
        "__ENV__access_token": "KYUKOU_TWITTER_ACCESS_TOKEN",
        "__ENV__access_token_secret": "KYUKOU_TWITTER_ACCESS_TOKEN_SECRET",
        "account_activity_api_env": "kyukou"
    },
    "email": {
        "__ENV__password": "KYUKOU_LINE_CHANNEL_SECRET",
        "__ENV__smtp_server": "KYUKOU_SMTP_SERVER",
        "__ENV__smtp_port": "KYUKOU_SMTP_PORT",
        "__ENV__from_addr": "KYUKOU_FROM_ADDR"
    },
    "google": {
        "__ENV__google_client_secret": "KYUKOU_GOOGLE_CLIENT_SECRET",
        "__ENV__client_id": "KYUKOU_GOOGLE_CLIENT_ID",
        "scope": "email profile openid https://www.googleapis.com/auth/calendar.events",
        "access_type": "offline",
        "prompt": "consent",
        "response_type": "code"
    },
    "public_dir": "./web/public",
    "index": "index.html",
    "__ENV__admin_email_addr": "KYUKOU_FROM_ADDR",
    "default_notify": {
        "type": "day",
        "offset": -97200
    },
    "__ENV__hash_salt": "KYUKOU_HASH_SALT",
    "logfile": "../log/kyukou.log",
    "log_level": 1,
    "log": {
        "slack": {
            "__ENV__slack_webhook": "KYUKOU_SLACK_WEBHOOK",
            "log_level_gt": 3
        }
    }
}
