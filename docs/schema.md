# Концептуальная схема данных StudySwap

Предварительная концептуальная схема предметной области. Отражает состав сущностей,
связи и кардинальности, ключевые атрибуты, статусы и правила целостности.
Схема согласована с реализованными моделями (реализация опережает документацию).

## ER-диаграмма

```mermaid
erDiagram
    Institution ||--o{ Faculty : "faculties"
    Faculty |o--o{ Department : "departments"
    Department |o--o{ Discipline : "disciplines"
    Institution |o--o{ Teacher : "teachers"
    Faculty |o--o{ Teacher : "teachers"
    Department |o--o{ Teacher : "teachers"
    Institution |o--o{ User : "users"
    Faculty |o--o{ User : "users"
    User ||--o{ Material : "author"
    Discipline ||--o{ Material : "materials"
    Teacher ||--o{ Material : "materials"
    MaterialType ||--o{ Material : "materials"
    Material }o--o{ Tag : "tags"
    Material ||--o{ MaterialFile : "files"
    Material ||--o{ DownloadEvent : "download_events"
    MaterialFile ||--o{ DownloadEvent : "download_events"
    User ||--o{ DownloadEvent : "download_events"
    Material ||--o{ Review : "reviews"
    User ||--o{ Review : "reviews"
    Material ||--o{ Comment : "comments"
    User ||--o{ Comment : "comments"
    Material ||--o{ Complaint : "complaints"
    User ||--o{ Complaint : "complaints_filed"
    User |o--o{ Complaint : "complaints_handled"

    Institution {
        string name "unique"
        bool is_active
    }
    Faculty {
        string name
        bool is_active
        string institution FK
    }
    Department {
        string name
        string short_name
        bool is_active
        string faculty FK "nullable"
    }
    Discipline {
        string code
        string name
        bool is_active
        string department FK "nullable"
    }
    Teacher {
        string full_name
        bool is_active
        string institution FK "nullable"
        string faculty FK "nullable"
        string department FK "nullable"
    }
    MaterialType {
        string code "unique"
        string name
        text description
        bool is_active
    }
    User {
        string email "unique, USERNAME_FIELD"
        string full_name
        string role "USER | MODERATOR | ADMIN"
        int course "nullable"
        string group
        bool is_active
        bool is_staff
        datetime date_joined
        string institution FK "nullable"
        string faculty FK "nullable"
    }
    Tag {
        string name "unique"
    }
    Material {
        string title
        text description
        int semester
        int academic_year "стартовый год"
        string status "MaterialStatus"
        bool is_verified_by_community
        text moderation_reason
        decimal average_rating "кэш, nullable"
        int rating_count "кэш"
        int download_count "кэш"
        datetime published_at "nullable"
        datetime archived_at "nullable"
        string author FK
        string discipline FK
        string teacher FK
        string type FK
    }
    MaterialFile {
        file file
        string original_name
        string mime_type
        int size_bytes
        string checksum_sha256
        datetime uploaded_at
        string material FK
    }
    DownloadEvent {
        datetime downloaded_at
        string material FK
        string file FK
        string user FK
    }
    Review {
        int score "1..5"
        text text
        string material FK
        string user FK
    }
    Comment {
        text body
        datetime created_at
        string material FK
        string user FK
    }
    Complaint {
        text text
        string status "NEW | RESOLVED"
        text resolution_note
        string material_status_before "nullable"
        datetime created_at
        datetime resolved_at "nullable"
        string material FK
        string reporter FK
        string moderator FK "nullable"
    }
```

## Сущности и назначение

| Сущность | Назначение |
|---|---|
| Institution, Faculty, Department | Иерархия учебного заведения (справочники) |
| Discipline, Teacher, MaterialType | Атрибутивные справочники для поиска материалов |
| User | Учётная запись с ролью и учебными атрибутами |
| Material | Учебный материал: атрибуты, статус модерации, кэшированные метрики |
| MaterialFile | Прикреплённый файл (UUID-имя, SHA-256, размер) |
| Tag | Тег темы; связь с материалами «многие-ко-многим» |
| DownloadEvent | Факт скачивания файла пользователем (основание допуска к оценке) |
| Review | Оценка 1–5 с текстом отзыва; одна на пользователя на материал |
| Comment | Комментарий/вопрос в обсуждении материала |
| Complaint | Жалоба пользователя и результат её обработки модератором |

Сущности Institution, Faculty, Department, Discipline, Teacher, MaterialType, Material,
Review наследуют `core.models.TimeStampedModel` — служебные временные метки
создания/изменения (`created_at` и др.).

## Статусы

**MaterialStatus:** `MODERATION` (на модерации) → `PUBLISHED` (опубликован) /
`REJECTED` (отклонён); из `PUBLISHED` возможны `NEEDS_REVISION` (на доработке),
`HIDDEN` (скрыт), `ARCHIVED` (в архиве).

**ComplaintStatus:** `NEW` (новая) → `RESOLVED` (обработана).

**UserRole:** `USER`, `MODERATOR`, `ADMIN`; гость — неаутентифицированный субъект.

## Ограничения целостности

- `Faculty`: уникальность пары (institution, name).
- `Review`: уникальность пары (material, user) — одна оценка на пользователя на материал.
- `Institution.name`, `MaterialType.code`, `Tag.name`, `User.email` — уникальны.
- `Review.score`: 1 ≤ score ≤ 5 (валидаторы уровня модели).
- Кэшированные поля Material (`average_rating`, `rating_count`, `download_count`) и
  служебные даты (`published_at`, `archived_at`) недоступны для ручного редактирования.

## Политики удаления

| Связь | Политика | Обоснование |
|---|---|---|
| Material → author / discipline / teacher / type | PROTECT | Нельзя удалить справочник или автора, на которых ссылается материал |
| Faculty → Institution | PROTECT | Сохранность иерархии справочников |
| Discipline → Department, Teacher → справочники, User → справочники | SET_NULL | Удаление справочника не уничтожает зависимые записи |
| MaterialFile / DownloadEvent / Review / Comment / Complaint → Material | CASCADE | Подчинённые записи не существуют без материала |
| Complaint → moderator | SET_NULL | Жалоба сохраняется после удаления учётной записи модератора |

## Бизнес-правила, отражённые в схеме

1. **Допуск к оценке:** оценка возможна только при наличии `DownloadEvent`
   (пользователь скачал материал); автор не оценивает собственный материал.
2. **Метка времени публикации:** `published_at` проставляется при первом переходе
   в `PUBLISHED` и далее не перезаписывается; `archived_at` — при первом переходе в `ARCHIVED`.
3. **Рейтинг материала:** `average_rating` = среднее `Review.score`, `rating_count` = число оценок.
4. **Рейтинг автора:** среднее оценок по всем его материалам, когда-либо опубликованным
   (`published_at IS NOT NULL`).
5. **Балльный баланс автора:** `Σ(score) − 3 × N` по тем же материалам (нейтральная оценка 3
   не изменяет баланс).
6. **Жалоба:** подаётся только на `PUBLISHED`-материал; повторная необработанная жалоба
   того же заявителя на тот же материал блокируется. При обработке фиксируются
   `moderator`, `resolution_note`, `material_status_before`, `resolved_at`.
7. **Публичность:** каталог, карточка и скачивание доступны только для `PUBLISHED`;
   скачивание — только аутентифицированным пользователям.
8. **Архивация:** автор переводит собственный опубликованный материал в `ARCHIVED`;
   физическое удаление из БД не предусмотрено.