# Ролевая модель и авторизация

- Роли: `user`, `admin`.
- Все защищенные ручки требуют Bearer-токен. 401/403 генерируются ТОЛЬКО зависимостями в `app/dependencies.py`.

Зависимости
- get_current_user: проверяет JWT, загружает пользователя.
- require_role("admin"): ограничивает доступ только для админов.
- require_verified_author: проверяет флаг `is_verified_author`.
- resolve_news_and_check_editable: подгружает новость и проверяет право на редактирование (автор или админ).
- resolve_comment_and_check_owner: подгружает комментарий и проверяет право на редактирование/удаление (автор или админ).

Аутентификация
- Логин/пароль: `/auth/register`, `/auth/login`.
- GitHub OAuth: `/auth/github/login` → `/auth/github/callback`.

Сессии и токены
- Access JWT генерируется на стороне API.
- Refresh-токены хранятся в таблице `refresh_sessions` вместе с `user_agent`.
- Обновление токена: `/auth/refresh`.
- Выход: `/auth/logout` (удаляет refresh-сессию).
- Список моих сессий: `/auth/sessions`.
