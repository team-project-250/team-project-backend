# EasyRent — Бекенд-roadmap

Покроковий план побудови всього бекенду, мілстоун за мілстоуном.
Кожен мілстоун = одна гілка `feature/*` від `develop` → PR → рев'ю → мерж.

Джерело правди щодо обсягу: документ функціональних вимог (ID вигляду FR-*/CR-*/UI-*) та макети дизайну.

---

## Домовленості (вирішуємо один раз, застосовуємо всюди)

| Тема | Рішення |
| --- | --- |
| База API | усе під `/api/`, один router/urlconf на застосунок, `include("apps.<x>.urls")` у `config/urls.py` |
| Автентифікація | **клієнтських акаунтів немає.** Усі публічні ендпоінти — `AllowAny`. Автентифікація лише для `/admin/` (персонал, session auth). `POST` бронювання/callback — публічний + throttle. |
| Пагінація | глобально `PageNumberPagination`, `PAGE_SIZE = 12`. Перевизначати на рівні в'юхи: каталог = 6/стор. (UI-2.3.01, уточнено в TP250-89), `?page_size=` до 50, малі фіксовані списки (міста, категорії, FAQ) = `pagination_class = None` |
| Фільтрація | `django-filter`, `FilterSet` на кожен list-ендпоінт |
| Гроші | `DecimalField(max_digits=8, decimal_places=2)`. Ніколи float. |
| Дати | дати оренди — `DateField` (без часу). `USE_TZ = True`, `TIME_ZONE = "Europe/Kyiv"` (уже налаштовано) |
| Телефон | зберігати як введено, валідувати регуляркою (`+?\d{10,15}`). Хелпер `normalize_phone()` у спільному модулі |
| Бізнес-логіка | живе в `apps/<x>/services.py`, не у в'юхах чи серіалізаторах |
| Enum-и | `models.TextChoices` |
| Тести | `pytest`, по застосунках `apps/<x>/tests/test_*.py`, `pytestmark = pytest.mark.django_db`. Покривати кожну функцію з `services.py`. |
| Seed-дані | JSON-фікстури в `apps/<x>/fixtures/`. Одна команда `python manage.py seed_demo` вантажить їх усі (додається в M1, розширюється щомілстоуна). |
| Зображення | `ImageField`. Dev: віддаються з `MEDIA_ROOT`. **Сховище медіа для продакшену — відкрите питання** (диск Render проти Cloudinary/S3) — див. M10. |
| OpenAPI | `drf-spectacular`. Тегувати кожен viewset (`@extend_schema(tags=["catalog"])`). |
| Коміти | Conventional Commits зі скоупом: `feat(catalog): ...`, `test(bookings): ...`. Дрібні, одна логічна зміна кожен. |
| Definition of done (кожен мілстоун) | `ruff check . && ruff format --check . && mypy . && pytest` зелені · міграції в комітах · адмінка робоча · ендпоінти в `/api/docs/` · фікстура оновлена · список ендпоінтів у README оновлено · PR у `develop` з рев'ю + зеленим CI |

---

## Граф залежностей

```
M1 locations ─┐
M2 reviews    │
              ├─> M3 catalog ─┬─> M5 bookings ─┬─> M6 callback
              │               │                ├─> M7 my-bookings
              │               │                └─> M8 catalog availability filter
M4 static pages & FAQ         │
                              └────────────────────> M9 home aggregator ──> M10 hardening & deploy
```

Рекомендований порядок: **M1 → M2 → M3 → M5 → M6 → M7 → M8 → M4 → M9 → M10**.
M4 (статичні сторінки) ні від чого не залежить — можна робити будь-коли / паралельно іншим тіммейтом.

---

## M0 — Фундамент ✅ (уже на `develop`, PR #1)

DRF + розбиття налаштувань + PostgreSQL + CORS + drf-spectacular + скелети `apps/catalog` та `apps/bookings` + CI + Docker Postgres + smoke-тести. Робити нічого не треба.

---

## M1 — Locations · `feature/cities`

**Чому перша:** селектор міста + пункт самовивозу (адреса / телефон / години) є в шапці й футері **кожної** сторінки (FR-1.1.02, FR-1.1.07, UI-1.6.03). Маленька, без залежностей.

### Кроки
1. `python manage.py startapp locations apps/locations` → виправити `apps.py` (`name = "apps.locations"`), додати в `LOCAL_APPS`, почистити boilerplate, додати теку `tests/`.
   `feat(locations): add locations app`
2. Модель `City`: `name`, `slug`, `is_default`, `is_active`, `order`, `pickup_address`, `pickup_phone`, `working_hours` (дефолт `"Пн-Нд: Цілодобово"`, CR-1.1.01). Гарантувати єдиний дефолт у `save()`/`clean()`. `makemigrations` + `migrate`.
   `feat(locations): add City model with pickup point info`
3. Адмінка: `list_display`/`list_editable` для `is_default`, `is_active`, `order`; `prepopulated_fields` для slug.
   `feat(locations): register City in admin`
4. API: `CitySerializer`, `CityViewSet(ReadOnlyModelViewSet)` (`lookup_field="slug"`, `pagination_class=None`, лише активні), router `cities`, підключити в `config/urls.py`.
   → `GET /api/cities/`, `GET /api/cities/{slug}/`
   `feat(locations): add cities API endpoint`
5. Тести: список повертає лише активні, detail за slug, інваріант «лише один дефолт».
   `test(locations): cover the cities endpoint`
6. Фікстура `fixtures/cities.json`: Луцьк (дефолт), Львів, Київ, Одеса — з даними самовивозу з футера.
   Додати команду `seed_demo` (`apps/locations/management/commands/seed_demo.py`), яка викликає `loaddata cities`.
   `chore(locations): add cities fixture and seed_demo command`
7. Документація: список ендпоінтів у README + беклог у `DEVELOPMENT_PLAN.md`.
   `docs: document the cities endpoint`

### Готово, коли
`GET /api/cities/` повертає 4 міста з даними самовивозу; в адмінці їх можна редагувати; рівно одне — дефолтне.

---

## M2 — Reviews · `feature/reviews`

**Обсяг:** карусель «Відгуки клієнтів» на головній (UI-1.5.01). Ні від чого не залежить.

### Кроки
1. `startapp reviews apps/reviews`, зареєструвати.
   `feat(reviews): add reviews app`
2. Модель `Review`: `author_name`, `avatar` (`ImageField`, blank), `rating` (`PositiveSmallIntegerField`, валідатори 1–5), `text`, `published_on` (`DateField`), `is_published` (дефолт `False`), `created_at`. `Meta.ordering = ["-published_on", "-id"]`.
   `feat(reviews): add Review model`
3. Адмінка: `list_display` (author, rating, published_on, is_published), `list_filter` (is_published, rating), масова дія «Publish selected».
   `feat(reviews): register Review in admin with moderation`
4. API: `ReviewSerializer`, `ReviewViewSet(ReadOnlyModelViewSet)` — `queryset = Review.objects.filter(is_published=True)`. Опційно `?limit=` або пагінація. Router `reviews`.
   → `GET /api/reviews/`
   `feat(reviews): add reviews API endpoint`
5. Тести: неопубліковані приховані, сортування за датою спадання, валідація рейтингу.
   `test(reviews): cover the reviews endpoint`
6. Фікстура `fixtures/reviews.json` (6–8 опублікованих). Розширити `seed_demo`.
   `chore(reviews): add reviews fixture`
7. Документація.
   `docs: document the reviews endpoint`

### Готово, коли
`GET /api/reviews/` повертає лише опубліковані відгуки, найновіші першими; менеджери модерують в адмінці.

---

## M3 — Каталог: категорії та техніка · `feature/catalog-equipment`

**Обсяг:** категорії мега-меню (FR-1.1.04), сітка каталогу + фільтри + сортування + пагінація (FR-2.1–2.3), дані сторінки товару (FR-3.1, FR-3.4), каруселі «Популярна техніка» / «Інша техніка». **Залежить від M1 (City).**
Фільтр/статус доступності **відкладено на M8** (потрібні бронювання).

### Моделі (`apps/catalog/models.py`)
| Модель | Поля |
| --- | --- |
| `Category` | `name`, `slug`, `order`, `is_active` — 6 фіксованих (FR-1.1.04) |
| `Equipment` | `name`, `slug`, `sku`, `category` (FK→PROTECT), `short_description`, `description`, `price_per_day` (Decimal), `rating` (Decimal, дефолт 0 — для «По рейтингу»), `is_popular` (bool — карусель головної), `is_active`, `main_image`, `available_cities` (M2M→City), `created_at` |
| `EquipmentImage` | `equipment` (FK), `image`, `order` — галерея/мініатюри (UI-3.1.02) |
| `EquipmentSpec` | `equipment` (FK), `label`, `value`, `order` — таб «Характеристики» (FR-3.4.04) |
| `EquipmentIncludedItem` | `equipment` (FK), `name`, `order` — таб «Комплектація» (FR-3.4.03) |
| `EquipmentBenefit` | `equipment` (FK), `text`, `order` — переваги з галочками на сторінці товару (CR-3.1.01/02) |

> Припущення: **одна фізична одиниця на позицію техніки**. Якщо згодом знадобиться кілька одиниць на місто — додати `units_count` у through-модель (зазначено, зараз не робимо).

### Кроки
1. Моделі + `makemigrations catalog` + `migrate`.
   `feat(catalog): add Category and Equipment models`
   `feat(catalog): add equipment images, specs, included items and benefits`
2. Адмінка: `CategoryAdmin`; `EquipmentAdmin` з inline-формами (images, specs, included items, benefits), `list_filter` (category, is_popular, is_active, available_cities), `list_display` (name, category, price_per_day, is_popular), `prepopulated_fields`, `filter_horizontal` для `available_cities`.
   `feat(catalog): configure catalog admin with inlines`
3. Серіалізатори:
   - `CategorySerializer`
   - `EquipmentListSerializer` (картка: id, name, slug, price_per_day, main_image, rating, category, is_popular, основна мітка доступності)
   - `EquipmentDetailSerializer` (+ images, specs, included_items, benefits, available_cities, description)
   `feat(catalog): add catalog serializers`
4. В'юхи + фільтри:
   - `CategoryViewSet(ReadOnlyModelViewSet)` — `pagination_class=None`
   - `EquipmentViewSet(ReadOnlyModelViewSet)` — `lookup_field="slug"`, `EquipmentListSerializer` для list / `EquipmentDetailSerializer` для retrieve
   - `EquipmentFilter`: `category` (slug, multi), `city` (slug, multi через `available_cities`), діапазон ціни
   - сортування: `rating` (дефолт `-rating`), `price_per_day` (FR-2.2)
   - list `PAGE_SIZE = 6` (кастомний клас пагінації, `?page_size=` до 50)
   - додаткові query-параметри: `?is_popular=true` (головна), `?exclude=<slug>` (карусель «Інша техніка»)
   → `GET /api/categories/`, `GET /api/equipment/`, `GET /api/equipment/{slug}/`
   `feat(catalog): add categories and equipment endpoints with filters and sorting`
5. Порожній результат обробляє DRF (повертає `results: []`); фронт показує текст CR-2.4.01.
6. Тести: фільтр за category/city, сортування за ціною asc/desc, дефолтне сортування за rating, пагінація = 8, фільтр `is_popular`, detail містить вкладені блоки, неактивна техніка прихована.
   `test(catalog): cover catalog filtering, sorting and detail`
7. Фікстури: `categories.json` (6), `equipment.json` (~10 з макетів, зі specs/images/benefits, `is_popular` на 3–4). Розширити `seed_demo`. Покласти реальні фото товарів у `media/` або посилатися на плейсхолдери.
   `chore(catalog): add catalog seed fixtures`
8. Документація.
   `docs: document the catalog endpoints`

### Готово, коли
Сторінку каталогу можна повністю зібрати з API: фільтр (category, city), сортування (rating, price), пагінація (8/стор.); сторінка товару рендерить галерею + таби; каруселі головної та «Інша техніка» використовують `?is_popular=true` / `?exclude=`.

---

## M5 — Бронювання: створення + розрахунок ціни · `feature/bookings-create`

**Обсяг:** повна форма бронювання (FR-3.3.01), розрахунок ціни на сервері, перевірка доступності. **Залежить від M3, M1.**

### Модель (`apps/bookings/models.py`)
`Booking`:
- `number` (`ER-XXXXX`, unique, автогенерація)
- `equipment` (FK→PROTECT), `city` (FK→PROTECT)
- `customer_name`, `customer_phone`
- `start_date`, `end_date`
- `delivery_method` (`TextChoices`: `PICKUP`, `COURIER`), `delivery_address` (blank; обов'язкове, коли `COURIER`)
- `payment_method` (`TextChoices`: `CASH`, `TRANSFER`)
- `status` (`TextChoices`: `PENDING`, `CONFIRMED`, `ACTIVE`, `COMPLETED`, `CANCELLED`; дефолт `PENDING`)
- `comment` (blank)
- заморожена ціна: `rental_days`, `price_per_day`, `delivery_fee`, `discount_amount` (дефолт 0), `total_price`
- `created_at`, `updated_at`

### Сервіси (`apps/bookings/services.py`)
- `generate_booking_number()` — `ER-` + 5 випадкових цифр, повтор при колізії
- `rental_days(start, end)` → `(end - start).days + 1` (включно)
- `quote(equipment, start, end, delivery_method)` → dict `{rental_days, price_per_day, delivery_fee, total}`
  `delivery_fee = 100 if COURIER else 0` (глобальне правило). Знижка — **лише вручну**, ніколи автоматично (FR-1.6.02).
- `assert_available(equipment, city, start, end, *, exclude_booking=None)` — всередині `transaction.atomic()` з `select_for_update()` на бронюваннях, що перетинаються. Перетин = `existing.start_date <= new.end_date AND existing.end_date >= new.start_date`, `status in {PENDING, CONFIRMED, ACTIVE}`. Також перевірити `city in equipment.available_cities`.
- `create_booking(data)` — оркеструє: валідація дат (`start >= today`, `end >= start`), `assert_available`, `quote`, `generate_booking_number`, збереження.

### Кроки
1. Модель + `makemigrations bookings` + `migrate`.
   `feat(bookings): add Booking model`
2. `services.py` — ціна, генератор номера, перевірка доступності, `create_booking`.
   `feat(bookings): add booking pricing and availability services`
3. Адмінка: `list_display` (number, equipment, customer_phone, dates, status, total_price), `list_filter` (status, city, delivery_method), `search_fields` (number, customer_phone), заморожена ціна read-only, дія **«Apply 10% Instagram discount»** (ставить `discount_amount = round(subtotal * 0.1, 2)`, перераховує `total_price`).
   `feat(bookings): configure bookings admin with manual discount action`
4. API:
   - `BookingCreateSerializer` (вхід: equipment slug, city slug, name, phone, dates, delivery_method, delivery_address, payment_method, comment) — `validate()` викликає сервіси; крос-польові перевірки
   - `BookingSerializer` (вихід: number, status, розклад ціни, короткі дані техніки)
   - `POST /api/bookings/` → `CreateAPIView` (або `@api_view`) — `AllowAny` + `AnonRateThrottle` (scope `booking`)
   - опційно `POST /api/bookings/quote/` — попередній розрахунок ціни без створення (зручно для екрана «Оформлення оренди»)
   `feat(bookings): add booking create and quote endpoints`
5. Тести (найважливіші):
   - ціна = дні × ставка + доставка, кількість днів включно
   - `COURIER` додає 100, `PICKUP` додає 0
   - дати, що перетинаються, — відхилено; суміжні (end == наступний start? вирішити — трактувати передачу в той самий день як конфлікт)
   - техніка недоступна в місті — відхилено
   - минула дата початку — відхилено
   - номер бронювання унікальний + формат
   - конкурентне створення не робить подвійного бронювання (симулювати сервісом у транзакційному тесті)
   `test(bookings): cover pricing, availability and booking creation`
6. Фікстура: кілька зразкових бронювань, щоб екрани календаря / «Мої бронювання» мали дані. Розширити `seed_demo`.
   `chore(bookings): add sample bookings fixture`
7. Документація + `.env.example`, якщо додано налаштування рейту throttle.
   `docs: document the bookings endpoints`

### Готово, коли
`POST /api/bookings/` створює бронювання з порахованою на сервері сумою та унікальним номером і відхиляє запити з перетином дат / не тим містом / минулою датою. Менеджер може застосувати знижку 10% в адмінці.

---

## M6 — Бронювання в 1 клік (callback) · `feature/quick-booking`

**Обсяг:** «Забронювати в 1 клік» (FR-3.3.02) — попап, лише телефон, «менеджер зв'яжеться з вами». **Залежить від M3.**

### Кроки
1. Модель `CallbackRequest` (в `apps/bookings`): `equipment` (FK→SET_NULL, null), `phone`, `start_date`/`end_date` (null — попередньо обраний діапазон, якщо є), `comment` (blank), `is_processed` (дефолт False), `created_at`.
   `feat(bookings): add CallbackRequest model`
2. Адмінка: `list_display` (phone, equipment, created_at, is_processed), `list_filter` (is_processed), дія «Mark processed».
   `feat(bookings): register CallbackRequest in admin`
3. API: `CallbackRequestSerializer`, `POST /api/callback-requests/` — `AllowAny` + throttle. Відповідь = payload підтвердження (фронт показує «Дякуємо, менеджер зв'яжеться...»).
   `feat(bookings): add callback request endpoint`
4. Тести: створює рядок, валідація телефону, throttle.
   `test(bookings): cover callback requests`
5. Документація.
   `docs: document the callback endpoint`

### Готово, коли
`POST /api/callback-requests/` фіксує лід; менеджери бачать і обробляють його в адмінці.

---

## M7 — Мої бронювання: пошук + скасування · `feature/my-bookings`

**Обсяг:** екран «Мої бронювання» — список за телефоном, скасування (макет, екран 5). **Залежить від M5.**

> Зауваження щодо безпеки: пошук лише за телефоном — слабкий. Для цього проєкту прийнятно за вимогами, але: (a) жорсткий throttle, (b) розглянути вимогу `number` + `phone` разом для скасування. Задокументувати компроміс у PR.

### Кроки
1. API:
   - `GET /api/bookings/?phone=<phone>` — повертає бронювання цього телефону, найновіші першими. **Вимагати `phone`** (400, якщо немає — ніколи не віддавати всі). `AnonRateThrottle` (scope `booking-lookup`, напр. `20/hour`).
   - `POST /api/bookings/{number}/cancel/` — тіло `{ "phone": "..." }` має збігатися з бронюванням. Дозволено лише коли `status in {PENDING, CONFIRMED}` і `start_date` у майбутньому. Ставить `CANCELLED`. Сервіс `cancel_booking(number, phone)` у `services.py`.
   `feat(bookings): add my-bookings lookup and cancellation`
2. Тести: пошук вимагає phone, повертає лише збіги, сортування; скасування happy path; скасування відхилено для чужого телефону / вже розпочатого / завершеного / вже скасованого.
   `test(bookings): cover my-bookings lookup and cancellation`
3. Документація.
   `docs: document my-bookings endpoints`

### Готово, коли
Екран «Мої бронювання» працює: ввести телефон → побачити бронювання → скасувати майбутнє.

---

## M8 — Фільтр і статус доступності в каталозі · `feature/catalog-availability`

**Обсяг:** відкладена частина каталогу — бейдж «Доступно / Заброньовано до ДД.ММ» (UI-1.3.02/03, UI-3.1.04) і фільтр доступності (FR-2.1.04). **Залежить від M3 + M5.**

### Кроки
1. Сервіс `apps/catalog/services.py` (або перевикористати bookings): `equipment_availability(equipment, on_date=today)` → `("available", None)` або `("booked", next_free_date)`. Пакетний варіант `annotate_availability(queryset, on_date)` для list-ендпоінта (уникнути N+1 — один запит по всіх активних бронюваннях).
   `feat(catalog): add equipment availability service`
2. Серіалізатори: додати об'єкт `availability` (`{status, available_from}`) у list & detail серіалізатори.
   `feat(catalog): expose availability status on equipment`
3. Фільтр: `EquipmentFilter.availability` = `available` / `booked` (метод-фільтр через сервіс).
   `feat(catalog): add availability filter to the catalog`
4. Ендпоінт календаря: `GET /api/equipment/{slug}/availability/?month=YYYY-MM` → `{ "unavailable": ["2026-08-14", ...] }` або діапазони, з бронювань `status in {PENDING, CONFIRMED, ACTIVE}` (FR-3.2.03, UI-3.2.04). Дефолт — поточний місяць; обмежити діапазон (напр. 6 місяців уперед).
   `feat(catalog): add equipment availability calendar endpoint`
5. Тести: заброньована техніка показує `booked` + правильний `available_from`; фільтр `availability=available` виключає зараз заброньоване; календар перелічує правильні дні для заданого місяця; скасовані бронювання не блокують.
   `test(catalog): cover availability status, filter and calendar`
6. Документація.
   `docs: document the availability calendar endpoint`

### Готово, коли
Картки каталогу показують правильний бейдж, фільтр доступності працює, а календар на сторінці товару робить заброньовані дати неактивними.

---

## M4 — Статичні контент-сторінки та FAQ · `feature/static-pages`

**Обсяг:** 5 посилань із шапки (FR-1.1.01): Контакти, Умови бронювання, Про нас, Питання та відповіді, Доставка і оплата. Також таби товару «Доставка і оплата» / «Умови оренди» (FR-3.4.05, CR-3.4.02). Без залежностей — можна паралельно з M1–M3.

### Кроки
1. `startapp content apps/content`, зареєструвати.
   `feat(content): add content app`
2. Моделі:
   - `StaticPage`: `slug` (unique), `title`, `body` (`TextField`, Markdown або HTML — обрати одне), `is_published`, `updated_at`. Seed: `contacts`, `booking-terms`, `about`, `delivery-payment`.
   - `FAQItem`: `question`, `answer`, `order`, `is_published`.
   `feat(content): add StaticPage and FAQItem models`
3. Адмінка для обох (`prepopulated_fields` slug; `list_editable` order/is_published).
   `feat(content): register content models in admin`
4. API: `GET /api/pages/{slug}/` (`RetrieveAPIView`, лише опубліковані, інакше 404), `GET /api/faq/` (list, опубліковані, впорядковані).
   `feat(content): add pages and FAQ endpoints`
5. Тести: неопубліковане → 404 / приховане; сортування FAQ.
   `test(content): cover pages and FAQ endpoints`
6. Фікстури з реальними текстами (умови оренди CR-1.4.05–.10, доставка/оплата CR-3.4.02). Розширити `seed_demo`.
   `chore(content): add content fixtures`
7. Документація.
   `docs: document content endpoints`

### Готово, коли
Кожне посилання з шапки та таби товару «Умови оренди» / «Доставка і оплата» віддаються з `/api/pages/...` та `/api/faq/`.

---

## M9 — Агрегатор головної сторінки · `feature/home-endpoint`

**Обсяг:** один запит, що наповнює лендинг. **Залежить від M1, M2, M3 (+ M8 для статусів).**

### Кроки
1. `apps/content` (або крихітний `apps/home`) — `HomeView(APIView)`, `AllowAny`:
   ```json
   GET /api/home/
   {
     "cities":            [ ...CitySerializer ],
     "categories":        [ ...CategorySerializer ],          // для мега-меню
     "popular_equipment": [ ...EquipmentListSerializer ],     // is_popular=True, ліміт ~8
     "reviews":           [ ...ReviewSerializer ],            // останні 6 опублікованих
     "pickup":            { ...дані самовивозу дефолтного міста }
   }
   ```
   Маркетинговий текст (hero, бейджі, кроки, умови оренди, промо, копірайт) лишається константами на фронті — це фіксований текст у вимогах, поза обсягом CMS.
   `feat(home): add aggregated /api/home/ endpoint`
2. `@extend_schema` з явним response-серіалізатором, щоб `/api/docs/` показував форму.
3. Тести: ключі присутні, popular відфільтровано, reviews обмежені й опубліковані, pickup = дефолтне місто.
   `test(home): cover the home endpoint`
4. Документація.
   `docs: document the /api/home/ endpoint`

### Готово, коли
Фронт рендерить весь лендинг із `GET /api/home/` + статичний текст.

---

## M10 — Зміцнення та деплой · `feature/backend-hardening`

1. **Throttling** — `REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES/RATES"]`: базовий `anon` + скоупи `booking`, `booking-lookup`, `callback`. Налаштовується через env.
   `feat(config): add API throttling`
2. **Формат помилок** — кастомний `EXCEPTION_HANDLER`, що повертає `{ "detail": ..., "errors": {field: [...]} }` консистентно.
   `feat(config): add a consistent DRF exception handler`
3. **Логування** — `LOGGING` у stdout (JSON у прод), request-id, warn на 5xx.
   `feat(config): add structured logging`
4. **Медіа в продакшені** — вирішити: Cloudinary/S3 (`django-storages`) проти персистентного диска Render. Реалізувати обране; додати env-змінні в `.env.example` та `render.yaml`.
   `feat(config): configure production media storage`
5. **CORS** — виставити `CORS_ORIGINS` на задеплоєний фронт; `CSRF_TRUSTED_ORIGINS` для адмінки.
6. **Seed-команда** — фіналізувати `python manage.py seed_demo` (ідемпотентна), задокументувати.
   `chore: finalise the seed_demo command`
7. **Поліш OpenAPI** — описи, приклади, теги, `SPECTACULAR_SETTINGS` servers.
   `docs(api): polish the OpenAPI schema`
8. **Деплой** — Render Blueprint з `render.yaml`, підняти Postgres, прогнати міграції + `seed_demo`, smoke-тест живого URL, посилання в обидва README.
9. **Чеклист / шаблони PR** — виправити `.github/pull_request_template.md` (`mypy .`, не `mypy app`).
   `chore: fix stale PR template`
10. Мерж `develop` → `main`, тег `v1.0.0`.

### Готово, коли
API задеплоєно, з throttling, спостережуваністю, документацією, і фронт вказує на нього.

---

## Карта ендпоінтів (фінальний стан)

| Метод | Шлях | Мілстоун |
| --- | --- | --- |
| GET | `/api/cities/` · `/api/cities/{slug}/` | M1 |
| GET | `/api/reviews/` | M2 |
| GET | `/api/categories/` | M3 |
| GET | `/api/equipment/` · `/api/equipment/{slug}/` | M3 |
| GET | `/api/equipment/{slug}/availability/?month=` | M8 |
| POST | `/api/bookings/` · `/api/bookings/quote/` | M5 |
| GET | `/api/bookings/?phone=` | M7 |
| POST | `/api/bookings/{number}/cancel/` | M7 |
| POST | `/api/callback-requests/` | M6 |
| GET | `/api/pages/{slug}/` · `/api/faq/` | M4 |
| GET | `/api/home/` | M9 |
| — | `/api/schema/` · `/api/docs/` · `/admin/` | M0 |

## Застосунки (фінальний стан)

```
apps/
├── locations/   City + пункти самовивозу
├── reviews/     відгуки клієнтів (модеровані)
├── catalog/     Category, Equipment (+ images, specs, included items, benefits), доступність
├── bookings/    Booking, CallbackRequest, сервіси ціни/доступності
└── content/     StaticPage, FAQItem, агрегатор головної
```
