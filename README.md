Это вариант исправенной версии приложения, на данный момент является актуальным и протестированным. В идеале ( для полного тестирования всех функций приложения ), все удобно запускать через docker-compose.yml ( фронт + бек + бд и пр. ). Ручки работают. Аутентификация, кеширование, воркер, асинхронность, корректная структура проекта...

Единственное, некоторый старый функционал я не успел удалить ( касается переменных и ряда ныне нефункциональных кусков кода ( использовал во время тестирования )).+Я еще в процессе размышлений касаемо alembic.

Также, т.к. в данном случае я .env не грузил,я в некоторых перемеенных положил значения для тестирования, чтобы было +- понятно, что происходит ( особенно касаемо модулей, отвечающих за безопасность... ).


Изменения относительно прошлой версии ( подразумеваю предыдущий вариант в этой же ветке, т.к., как уже писал, пересобирвл проект практически полностью, соотв., большого смысла сравнивать его с абсолютно неудачным вариантом https://github.com/itmo-webdev/lab1__Ganshin_Yaroslav/tree/cash нету, более того, ветвь эту я, кажется, удалил.

- Доработано кэширование (доработка доработки ):
  - Внедрено кэширование через Redis для новостей и отдельных пользователей.
  - Сессии пользователей (refresh токены) теперь хранятся исключительно в Redis , полностью удалена соответствующая таблица из БД.
  - Реализована инвалидация кэша при изменении данных.
  - Добавлено логирование для отслеживания использования кэша для пользователей.
  - 
- Аутентификация:
  - Полностью переведена на использование Redis для хранения refresh токенов, что обеспечивает быстрый доступ и снижает нагрузку на БД.
  - Чуть скорректировал вход через гитхаб
- Асинхронность:
  - Проект продолжает использовать FastAPI и SQLAlchemy с AsyncSession для асинхронной работы с БД, а также асинхронный клиент Redis и Celery для фоновых задач.
  - 
- Скорректирована работа воркера ( в том числе: интеграция Celery для обработки фоновых задач, таких как уведомления о новых новостях и еженедельные дайджесты, с логированием вместо отправки реальных писем )











Теперь быстро протестирую функционал (уточню, что тестирование происходило на разных этапах реализации проекта, соотв., изображения финального интерфейса проекта находятся в конце readme.md ):


Необходимо закрыть все ручки
<img width="897" height="430" alt="image" src="https://github.com/user-attachments/assets/b9f8a5e5-b924-48b0-b135-54a4df0510f7" />

<img width="1224" height="345" alt="image" src="https://github.com/user-attachments/assets/4d19fe7e-c7ba-49d0-b412-967fedb4049a" />


 
Необходимо поддержать авторизацию через GitHub OAuth
  <img width="218" height="179" alt="image" src="https://github.com/user-attachments/assets/69e4f8e9-b7c4-48e2-b06f-273a9e059f3a" />


Необходимо поддержать флаг "верифицирован ли как автор" при попытке создать новость
<img width="463" height="171" alt="image" src="https://github.com/user-attachments/assets/6c6032af-0bdb-4e91-9bf2-c84ef1bff723" />

Обновить флаг для админов, которые могу выполнять все операции.Роль тут будет либо юзер либо админ.

<img width="697" height="304" alt="image" src="https://github.com/user-attachments/assets/b72fcf62-74dd-4c97-90ad-84cb838a9caa" />

Сценарий использования
Запустить локально сервис
Можно авторизоваться через GitHub, так же можно авторизовать через логин и пароль, нужны для этого дополнительные ручки
Если пользователь не верифицирован как автор, то создать новость он не может
Пользователь может редактировать свою же новость, помимо этого и удалять
Комментарии могут оставлять любые пользователи, авторы комментариев могут их редактировать и удалять
Пользователь с ролью админ может делать все вышеперечисленное\

Если пользователь не верифицирован как автор, то создать новость он не может

<img width="1244" height="574" alt="image" src="https://github.com/user-attachments/assets/043ba16e-ffd2-4ac0-b56f-b0b695e739c8" />



Создание API для новостей

1)
Нужно написать CRUD API, используя FastAPI, который содержит следующие сущности:
Новость
Пользователь
Комментарий

<img width="1067" height="584" alt="image" src="https://github.com/user-attachments/assets/46f14268-9b11-407b-91c1-1ebb8815cf95" />

<img width="1059" height="548" alt="image" src="https://github.com/user-attachments/assets/905bd3b8-ea5d-4a90-82bc-698fb5665d03" />

<img width="1060" height="629" alt="image" src="https://github.com/user-attachments/assets/fb7bfba4-44f7-4e1d-81c7-bb44d53bc43b" />

Сценарий использования
Запустить локально сервис
Создать пользователей
Создать новость, которая прикреплена к пользователю (автор)
Создать комментарий к новости от другого пользователя
Изменить новость
Изменить комментарий
Удалить новость вместе со всеми комментариями
<img width="1176" height="126" alt="image" src="https://github.com/user-attachments/assets/c8ac4fd1-6b52-444d-8e81-69028a12dcba" />

<img width="1221" height="613" alt="image" src="https://github.com/user-attachments/assets/ed4a7bfc-c4cf-4949-8965-2d39b128da6e" />

Создам пользователя:

<img width="987" height="587" alt="image" src="https://github.com/user-attachments/assets/f32564b1-dfdd-4dca-84d1-2d1121041ebd" />

<img width="957" height="620" alt="image" src="https://github.com/user-attachments/assets/311b516b-79e3-4abb-978b-6d36b13801b6" />

Чтобы запостить новость, мне нужно авторизироваться и зайти как автор:
<img width="893" height="317" alt="image" src="https://github.com/user-attachments/assets/b2f3a22e-9198-422a-a94a-959d5ec66136" />

Для этого сделаю пользователя автором:
(залогинюсь как админ для начала )
<img width="722" height="597" alt="image" src="https://github.com/user-attachments/assets/a0fd9ee0-8fd1-41c4-9105-eb1a68c1f027" />

<img width="952" height="473" alt="image" src="https://github.com/user-attachments/assets/2c01384e-1c76-4dc5-ac31-68921d6271aa" />

Сделаю моего пользователя автором

<img width="978" height="567" alt="image" src="https://github.com/user-attachments/assets/af4bb24a-7c0a-476f-af0f-a582dca23a32" />

<img width="1019" height="643" alt="image" src="https://github.com/user-attachments/assets/33571aa8-2842-417e-a772-38e773252b22" />

<img width="1076" height="516" alt="image" src="https://github.com/user-attachments/assets/f5b086b5-8bc9-4ece-8038-0ab1c94eaac4" />








<img width="1044" height="557" alt="image" src="https://github.com/user-attachments/assets/e63234f6-df6b-4008-9a3d-a3c05060da40" />

<img width="1028" height="585" alt="image" src="https://github.com/user-attachments/assets/5094d9b0-d516-4bba-99f9-9f0599521f33" />

<img width="851" height="635" alt="image" src="https://github.com/user-attachments/assets/5bb47c58-0e7b-41b7-a0d1-4d6dbbb38f0d" />

<img width="989" height="564" alt="image" src="https://github.com/user-attachments/assets/fba9e9f5-2e75-4148-bb7b-af36819ad099" />

<img width="1098" height="624" alt="image" src="https://github.com/user-attachments/assets/37a2adee-4426-4848-9116-02c39b5ef9c3" />


<img width="512" height="201" alt="image" src="https://github.com/user-attachments/assets/69181c0d-bf7b-4036-9e43-5fc52939cb34" />


Последние изображения интерфейса:

<img width="1635" height="906" alt="image" src="https://github.com/user-attachments/assets/ce9342ad-39b9-4e59-8a52-fe6bfbf4f931" />

<img width="1671" height="888" alt="image" src="https://github.com/user-attachments/assets/758b940d-b5b3-4a31-bcc5-c2a843f9589f" />


Логи работы воркера ( как раз был конец недели, все успешно сработало )
<img width="1305" height="358" alt="image" src="https://github.com/user-attachments/assets/ee05aeca-8f86-4d37-995e-8a612d0cc840" />


<img width="1678" height="508" alt="image" src="https://github.com/user-attachments/assets/bdcb793f-fc1c-4dee-837c-addba14aba2a" />

<img width="1886" height="904" alt="image" src="https://github.com/user-attachments/assets/9b22af59-3048-4478-b837-4e4884b210a9" />

<img width="830" height="833" alt="image" src="https://github.com/user-attachments/assets/7eb3e000-2642-4100-9892-2dc8782cc016" />

