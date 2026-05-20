import sqlite3
from flask import g
from datetime import datetime

DATABASE = 'portal.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            position TEXT,
            department TEXT,
            phone TEXT,
            avatar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            instructor TEXT,
            duration TEXT,
            difficulty TEXT DEFAULT 'beginner',
            image TEXT,
            is_published INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            video_url TEXT,
            file_path TEXT,
            image TEXT,
            order_num INTEGER DEFAULT 0,
            duration TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            correct_answer INTEGER NOT NULL,
            points INTEGER DEFAULT 1,
            image TEXT,
            explanation TEXT,
            FOREIGN KEY (lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lesson_id INTEGER NOT NULL,
            status TEXT DEFAULT 'not_started',
            score INTEGER,
            completed_at TIMESTAMP,
            attempts INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (lesson_id) REFERENCES lessons (id) ON DELETE CASCADE,
            UNIQUE(user_id, lesson_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            test_id INTEGER NOT NULL,
            selected_answer INTEGER,
            is_correct INTEGER,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

def seed_demo_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    cursor.execute("INSERT INTO users (username, password, email, full_name, role, position, department) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ('admin', 'admin123', 'admin@gakcson.ru', 'Администратор', 'admin', 'Системный администратор', 'ИТ отдел'))
    cursor.execute("INSERT INTO users (username, password, email, full_name, role, position, department) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ('user1', 'user123', 'ivanov@gakcson.ru', 'Иванов Иван Иванович', 'user', 'Социальный работник', 'Отдел социальной работы'))
    cursor.execute("INSERT INTO users (username, password, email, full_name, role, position, department) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ('user2', 'user123', 'petrova@gakcson.ru', 'Петрова Анна Сергеевна', 'user', 'Специалист по социальной работе', 'Отдел социальной работы'))
    
    cursor.execute("INSERT INTO courses (title, description, category, instructor, duration, difficulty, is_published) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ('Основы социальной работы', 'Курс знакомит с основами деятельности социального работника, этическими нормами и стандартами обслуживания. Включает изучение законодательства в сфере социальной защиты населения.', 
                    'Социальная работа', 'Сидоренко Е.В.', '2 недели', 'beginner', 1))
    cursor.execute("INSERT INTO courses (title, description, category, instructor, duration, difficulty, is_published) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ('Безопасность и охрана труда', 'Курс по охране труда для работников социальной сферы. Изучение правил техники безопасности, оказания первой помощи, профилактики профессиональных заболеваний.',
                    'Охрана труда', 'Мельников А.П.', '1 неделя', 'beginner', 1))
    cursor.execute("INSERT INTO courses (title, description, category, instructor, duration, difficulty, is_published) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ('Работа с пожилыми людьми', 'Специализированный курс по обслуживанию пожилых граждан и инвалидов. Особенности коммуникации, психология старения, специфика ухода за маломобильными категориями населения.',
                    'Социальная работа', 'Волкова О.И.', '3 недели', 'intermediate', 1))
    
    course_id = 1
    cursor.execute("INSERT INTO lessons (course_id, title, content, order_num, duration) VALUES (?, ?, ?, ?, ?)",
                   (course_id, 'Введение в профессию социального работника', 
                    '<h2>Кто такой социальный работник?</h2><p>Социальный работник — это специалист, оказывающий помощь гражданам, нуждающимся в социальной поддержке. Основные функции:</p><ul><li>Обеспечение социально-бытового обслуживания;</li><li>Помощь в оформлении документов;</li><li>Содействие в получении медицинской помощи;</li><li>Психологическая поддержка;</li><li>Информирование о социальных услугах.</li></ul><h2>Принципы работы</h2><p>Социальный работник руководствуется принципами:</p><ul><li>Гуманизм и уважение к личности;</li><li>Конфиденциальность;</li><li>Добровольность помощи;</li><li>Индивидуальный подход.</li></ul>',
                    1, '30 мин'))
    cursor.execute("INSERT INTO lessons (course_id, title, content, order_num, duration) VALUES (?, ?, ?, ?, ?)",
                   (course_id, 'Нормативно-правовая база', 
                    '<h2>Законодательство в сфере социальной защиты</h2><p>Основные нормативные документы:</p><ul><li>Федеральный закон № 442-ФЗ "Об основах социального обслуживания граждан в РФ";</li><li>Федеральный закон № 181-ФЗ "О социальной защите инвалидов в РФ";</li><li>Конвенция ООН о правах инвалидов;</li><li>Региональные нормативные акты.</li></ul><h2>Категории получателей социальных услуг</h2><p>Социальные услуги предоставляются:</p><ul><li>Пожилым гражданам;</li><li>Инвалидам;</li><li>Семьям с детьми;</li><li>Лицам без определённого места жительства;</li><li>Другим нуждающимся категориям.</li></ul>',
                    2, '45 мин'))
    cursor.execute("INSERT INTO lessons (course_id, title, content, order_num, duration) VALUES (?, ?, ?, ?, ?)",
                   (course_id, 'Этика социального работника', 
                    '<h2>Профессиональная этика</h2><p>Этические нормы социальной работы включают:</p><ul><li><strong>Уважение</strong> — признание ценности каждого человека независимо от его положения;</li><li><strong>Конфиденциальность</strong> — неразглашение личной информации;</li><li><strong>Честность</strong> — открытость и достоверность информации;</li><li><strong>Профессионализм</strong> — компетентность и ответственность;</li><li><strong>Терпимость</strong> — уважение к культурным различиям.</li></ul><h2>Запрещённые действия</h2><p>Социальный работник не вправе:</p><ul><li>Принимать подарки от подопечных;</li><li>Использовать служебное положение в личных целях;</li><li>Разглашать информацию о подопечных третьим лицам;</li><li>Оказывать услуги за плату.</li></ul>',
                    3, '30 мин'))
    
    course_id = 2
    cursor.execute("INSERT INTO lessons (course_id, title, content, order_num, duration) VALUES (?, ?, ?, ?, ?)",
                   (course_id, 'Охрана труда: основные понятия', 
                    '<h2>Что такое охрана труда?</h2><p>Охрана труда — система сохранения жизни и здоровья работников в процессе трудовой деятельности.</p><h2>Основные направления:</h2><ul><li>Идентификация опасных факторов;</li><li>Профилактика травматизма;</li><li>Обеспечение безопасных условий труда;</li><li>Обучение и инструктаж;</li><li>Средства индивидуальной защиты.</li></ul><h2>Ответственность</h2><p>Работодатель обязан обеспечить безопасные условия труда. Ра��отник обязан соблюдать правила охраны труда.</p>',
                    1, '25 мин'))
    cursor.execute("INSERT INTO lessons (course_id, title, content, order_num, duration) VALUES (?, ?, ?, ?, ?)",
                   (course_id, 'Первая помощь', 
                    '<h2>Базовая первая помощь</h2><p>При оказании помощи необходимо:</p><ol><li>Оценить обстановку и обеспечить безопасность;</li><li>Вызвать скорую помощь (103 или 112);</li><li>Оказать первую помощь;</li><li>До прибытия медиков.</li></ol><h2>При потере сознания</h2><ul><li>Проверить пульс и дыхание;</li><li>Придать устойчивое боковое положение;</li><li>Контролировать состояние до приезда скорой.</li></ul><h2>При травмах</h2><ul><li>Остановить кровотечение;</li><li>Наложить шину при переломах;</li><li>Приложить холод при ушибах.</li></ul>',
                    2, '40 мин'))
    
    course_id = 3
    cursor.execute("INSERT INTO lessons (course_id, title, content, order_num, duration) VALUES (?, ?, ?, ?, ?)",
                   (course_id, 'Психология пожилых людей', 
                    '<h2>Особенности психики пожилых</h2><p>С возрастом происходят изменения:</p><ul><li>Замедление процессов переработки информации;</li><li>Изменения в памяти (особенно кратковременной);</li><li>Эмоциональная лабильность;</li><li>Потребность в общении и признании.</li></ul><h2>Рекомендации по общению</h2><ul><li>Говорить чётко и медленно;</li><li>Использовать простой язык;</li><li>Проявлять терпение и уважение;</li><li>Слушать активно;</li><li>Избегать争论ов и поучений.</li></ul>',
                    1, '35 мин'))
    cursor.execute("INSERT INTO lessons (course_id, title, content, order_num, duration) VALUES (?, ?, ?, ?, ?)",
                   (course_id, 'Уход за маломобильными пациентами', 
                    '<h2>Правила перемещения</h2><ul><li>Использовать правильную технику подъёма;</li><li>Применять вспомогательные средства;</li><li>Обеспечивать удобное положение;</li><li>Избегать резких движений.</li></ul><h2>Профилактика пролежней</h2><ul><li>Менять положение каждые 2 часа;</li><li>Использовать противопролежневые матрасы;</li><li>Следить за гигиеной кожи;</li><li>Обеспечить правильное питание.</li></ul><h2>Гигиенические процедуры</h2><p>При проведении гигиенических процедур необходимо:</p><ul><li>Соблюдать приватность;</li><li>Использовать одноразовые материалы;</li><li>Контролировать температуру воды;</li><li>Высушивать кожу после мытья.</li></ul>',
                    2, '50 мин'))
    
    lesson_id = 1
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'Какая из перечисленных функций НЕ относится к обязанностям социального работника?',
                    '["Обеспечение социально-бытового обслуживания","Оказание юридической помощи в суде","Помощь в оформлении документов","Психологическая поддержка"]', 1, 1))
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'Какой принцип является основным в социальной работе?',
                    '["Индивидуальный подход","Конфиденциальность","Оплата услуг","Государственное финансирование"]', 1, 1))
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'Федеральный закон № 442-ФЗ регулирует:',
                    '["Об основах социального обслуживания граждан","О социальной защите инвалидов","О пенсионном обеспечении","О медицинской помощи"]', 0, 1))
    
    lesson_id = 2
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'Какие категории граждан могут получать социальные услуги?',
                    '["Только пожилые","Только инвалиды","Пожилые, инвалиды, семьи с детьми и другие нуждающиеся","Только малоимущие"]', 2, 1))
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'Что НЕ входит в обязанности социального работника по закону?',
                    '["Обеспечение питанием","Оказание медицинских услуг","Содействие в получении образования","Помощь в трудоустройстве"]', 1, 1))
    
    lesson_id = 3
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'Какое действие запрещено социальному работнику?',
                    '["Принимать подарки от подопечных","Разглашать личную информацию","Использовать служебное положение в личных целях","Все перечисленные действия"]', 3, 1))
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'Принцип конфиденциальности означает:',
                    '["Нельзя фотографировать подопечных","Нельзя разглашать личную информацию о подопечных","Нельзя обсуждать работу с коллегами","Нельзя вести записи"]', 1, 1))
    
    lesson_id = 4
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'Что включает система охраны труда?',
                    '["Только технику безопасности","Сохранение жизни и здоровья работников","Только обучение","Только средства защиты"]', 1, 1))
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'При обнаружении пострадавшего без сознания first действие:',
                    '["Начать искусственное дыхание","Проверить пульс и дыхание","Дать воды","Сделать массаж сердца"]', 1, 1))
    
    lesson_id = 5
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'Какой телефон для вызова скорой помощи?',
                    '["101","102","103","104"]', 2, 1))
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'При переломе конечности first нужно:',
                    '["Дать обезболивающее","Наложить шину","Согреть","Растереть"]', 1, 1))
    
    lesson_id = 6
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'С возрастом чаще всего ухудшается:',
                    '["Долговременная память","Кратковременная память","Профессиональные навыки","Знание языков"]', 1, 1))
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'При общении с пожилым человеком рекомендуется:',
                    '["Говорить быстро","Использовать сложные термины","Говорить чётко и медленно","Перебивать"]', 2, 1))
    
    lesson_id = 7
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'Как часто нужно менять положение лежачего пациента?',
                    '["Каждые 30 минут","Каждые 2 часа","Раз в сутки","1 раз в неделю"]', 1, 1))
    cursor.execute("INSERT INTO tests (lesson_id, question, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (lesson_id, 'Для профилактики пролежней важно:',
                    '["Использовать жёсткий матрас","Обеспечить правильное питание","Все перечисленное","Ограничить движения"]', 2, 1))
    
    conn.commit()
    conn.close()