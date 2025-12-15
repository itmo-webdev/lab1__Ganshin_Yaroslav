from prometheus_client import Counter

# Доп. метрики, необходимые, видимо, для каких-то бизнес-целей.
NEWS_CREATED = Counter('news_created_total', 'Total news created')
USERS_REGISTERED = Counter('users_registered_total', 'Total users registered')
NEWS_NOTIFICATIONS_SENT = Counter('news_notifications_sent_total', 'Total news notifications sent')