# IT Asset Management Module for Odoo 18

A comprehensive IT asset management solution for Odoo 18 that enables companies to efficiently track, manage, and maintain their IT infrastructure including computers, servers, mobile devices, and software licenses.

## 🚀 Key Features

### 📊 **Asset Management**
- **Asset Registry**: Complete tracking of computers, servers, mobile devices, software licenses
- **Technical Specifications**: Store detailed hardware/software specifications, serial numbers, warranties
- **Asset Categories**: Organize by type, department, location with hierarchical structure
- **Lifecycle Tracking**: Monitor status from purchase → available → assigned → maintenance → disposal
- **QR Code & Barcode**: Generate and print asset labels for easy identification

### 👥 **Assignment System**
- **Employee Assignments**: Assign assets to specific employees with full history tracking
- **Assignment Workflow**: Streamlined process for asset allocation and returns
- **Condition Tracking**: Monitor asset condition on assignment and return
- **Bulk Operations**: Efficiently manage multiple asset assignments

### 📋 **Request Management**
- **Request Types**: New asset, repair, replacement, upgrade, return requests
- **Approval Workflow**: Configurable multi-level approval process
- **Status Tracking**: Real-time request status with automated notifications
- **Priority Management**: Set urgency levels and deadlines
- **Cost Tracking**: Monitor estimated vs actual costs

### 📈 **Analytics & Reporting**
- **Dashboard Views**: Real-time overview of asset utilization and requests
- **Asset Reports**: Comprehensive reporting on inventory, assignments, and maintenance
- **Cost Analysis**: Track total cost of ownership and ROI
- **Warranty Tracking**: Monitor warranty status and expiration alerts

### 🌐 **Portal Access**
- **Employee Self-Service**: View assigned assets and submit requests via portal
- **Request Tracking**: Monitor request progress and history
- **Asset Details**: Access specifications and assignment information

## 🔧 Requirements

- **Odoo**: 18.0+
- **Python**: 3.12+
- **PostgreSQL**: 13+
- **Dependencies**: `base`, `mail`, `portal`, `hr`

### Key Models

#### `it.asset`
Core asset model storing all IT equipment information including:
- Asset identification and categorization
- Technical specifications
- Purchase and warranty information
- Current status and location
- Assignment history

#### `it.asset.request`
Request management system handling:
- Request types (new asset, repair, return)
- Workflow states and transitions
- Approval processes
- Comments and communication

#### `it.asset.assignment`
Asset-employee relationship tracking:
- Current and historical assignments
- Assignment dates and reasons
- Return processes and conditions

### Access Control

#### Internal Users (Managers)
- **IT Asset Manager**: Full access to all asset management features
- **Department Manager**: Access to departmental assets and requests
- **IT Support**: Access to repair requests and asset maintenance

#### Portal Users (Employees)
- **Employee**: View assigned assets and submit requests
- **Department Head**: Additional visibility into department assets

### Security Features
- Role-based access control using Odoo security groups
- Record-level security rules for data isolation
- Portal access restrictions for employee data
- Audit logging for all asset movements and changes

### Quick Start Guide
1. Create asset categories (Computers, Servers, Mobile, etc.)
2. Add your first assets with complete specifications
3. Configure user permissions and portal access
4. Set up approval workflows for requests

## 💼 Usage

### **IT Managers**
- **Assets**: Create, categorize, and manage IT inventory
- **Assignments**: Assign assets to employees and track history
- **Requests**: Approve/reject employee requests and manage workflows
- **Reports**: Generate analytics and cost reports

### **Employees (Portal)**
- **My Assets**: View assigned equipment and specifications
- **Submit Requests**: Request new equipment or repairs
- **Track Status**: Monitor request progress and updates

## 🔧 Customization

Built with standard Odoo architecture for easy extension:
- Custom fields and workflows
- Integration with other Odoo modules
- Custom reports and dashboards
- API integration capabilities

---

# 📋 Модуль Управління IT Активами для Odoo 18

Комплексне рішення для управління IT активами в Odoo 18, що дозволяє компаніям ефективно відстежувати, керувати та обслуговувати свою IT інфраструктуру, включаючи комп'ютери, сервери, мобільні пристрої та програмні ліцензії.

## 🚀 Основні функції

### 📊 **Управління активами**
- **Реєстр активів**: Повне відстеження комп'ютерів, серверів, мобільних пристроїв, програмних ліцензій
- **Технічні специфікації**: Зберігання детальних характеристик обладнання/ПЗ, серійних номерів, гарантій
- **Категорії активів**: Організація за типом, відділом, місцем розташування з ієрархічною структурою
- **Відстеження життєвого циклу**: Моніторинг статусу від покупки → доступний → призначений → обслуговування → утилізація
- **QR-коди та штрих-коди**: Генерація та друк етикеток активів для легкої ідентифікації

### 👥 **Система призначень**
- **Призначення співробітникам**: Призначення активів конкретним співробітникам з повною історією відстеження
- **Робочий процес призначення**: Спрощений процес розподілу та повернення активів
- **Відстеження стану**: Моніторинг стану активу при призначенні та поверненні
- **Масові операції**: Ефективне управління множинними призначеннями активів

### 📋 **Управління запитами**
- **Типи запитів**: Запити на новий актив, ремонт, заміну, оновлення, повернення
- **Робочий процес затвердження**: Налаштований багаторівневий процес затвердження
- **Відстеження статусу**: Статус запитів у реальному часі з автоматичними сповіщеннями
- **Управління пріоритетами**: Встановлення рівнів терміновості та дедлайнів
- **Відстеження витрат**: Моніторинг планованих та фактичних витрат

### 📈 **Аналітика та звітність**
- **Панелі інструментів**: Огляд використання активів та запитів у реальному часі
- **Звіти по активах**: Комплексна звітність по інвентарю, призначенням та обслуговуванню
- **Аналіз витрат**: Відстеження загальної вартості володіння та ROI
- **Відстеження гарантії**: Моніторинг статусу гарантії та сповіщення про закінчення

### 🌐 **Портальний доступ**
- **Самообслуговування співробітників**: Перегляд призначених активів та подання запитів через портал
- **Відстеження запитів**: Моніторинг прогресу та історії запитів
- **Деталі активів**: Доступ до специфікацій та інформації про призначення

## 🔧 Вимоги

- **Odoo**: 18.0+
- **Python**: 3.12+
- **PostgreSQL**: 13+
- **Залежності**: `base`, `mail`, `portal`, `hr`

### Ключові моделі

#### `it.asset`
Основна модель активу, що зберігає всю інформацію про IT обладнання:
- Ідентифікація та категоризація активів
- Технічні специфікації
- Інформація про покупку та гарантію
- Поточний статус та місцезнаходження
- Історія призначень

#### `it.asset.request`
Система управління запитами:
- Типи запитів (новий актив, ремонт, повернення)
- Стани робочого процесу та переходи
- Процеси затвердження
- Коментарі та комунікація

#### `it.asset.assignment`
Відстеження зв'язку актив-співробітник:
- Поточні та історичні призначення
- Дати призначення та причини
- Процеси повернення та умови

### Контроль доступу

#### Внутрішні користувачі (Менеджери)
- **IT Asset Manager**: Повний доступ до всіх функцій управління активами
- **Department Manager**: Доступ до активів відділу та запитів
- **IT Support**: Доступ до запитів на ремонт та обслуговування активів

#### Користувачі порталу (Співробітники)
- **Employee**: Перегляд призначених активів та подання запитів
- **Department Head**: Додаткова видимість активів відділу

### Функції безпеки
- Рольовий контроль доступу з використанням груп безпеки Odoo
- Правила безпеки на рівні записів для ізоляції даних
- Обмеження доступу до порталу для даних співробітників
- Аудит журналу всіх переміщень активів та змін

### Швидкий старт
1. Створити категорії активів (Комп'ютери, Сервери, Мобільні та ін.)
2. Додати перші активи з повними специфікаціями
3. Налаштувати дозволи користувачів та доступ до порталу
4. Налаштувати робочі процеси затвердження для запитів

## 💼 Використання

### **IT Менеджери**
- **Активи**: Створення, категоризація та управління IT інвентарем
- **Призначення**: Призначення активів співробітникам та відстеження історії
- **Запити**: Затвердження/відхилення запитів співробітників та управління робочими процесами
- **Звіти**: Генерація аналітики та звітів по витратах

### **Співробітники (Портал)**
- **Мої активи**: Перегляд призначеного обладнання та специфікацій
- **Подача запитів**: Запит нового обладнання або ремонту
- **Відстеження статусу**: Моніторинг прогресу запитів та оновлень

## 🔧 Кастомізація

Побудований зі стандартною архітектурою Odoo для легкого розширення:
- Користувацькі поля та робочі процеси
- Інтеграція з іншими модулями Odoo
- Користувацькі звіти та панелі інструментів
- Можливості інтеграції API

---
