## 1. Objetivo

El modelo de datos se diseñará siguiendo los principios de **normalización hasta Tercera Forma Normal (3NF)**.

La separación de responsabilidades entre microservicios permitirá que cada dominio posea sus propias entidades, evitando una base de datos monolítica y reduciendo el acoplamiento entre módulos.

> **Nota:** Para el MVP académico se podrá desplegar inicialmente sobre un único motor PostgreSQL, manteniendo separación lógica por esquemas. La arquitectura permitirá separar físicamente las bases de datos posteriormente.

---

# 2. Distribución de bases de datos

Se propone la siguiente división:

```text
┌─────────────────────────────────────────────────────────┐
│                    PLATFORM DATABASE                    │
│                                                         │
│  IAM / Organizations / Plugins / Automations / Billing │
└─────────────────────────────────────────────────────────┘

┌─────────────────────┐       ┌─────────────────────────┐
│   PLUGIN DATABASE   │       │   EXECUTION DATABASE    │
│                     │       │                         │
│ Registry            │       │ Executions              │
│ Versions            │       │ Jobs                    │
│ Dependencies        │       │ Logs                    │
└─────────────────────┘       └─────────────────────────┘

┌─────────────────────┐       ┌─────────────────────────┐
│   STORAGE DATABASE  │       │   MARKETPLACE DATABASE  │
│                     │       │                         │
│ Files               │       │ Listings                │
│ Quotas              │       │ Categories              │
│ Usage               │       │ Purchases               │
└─────────────────────┘       └─────────────────────────┘
```

En una primera implementación, estas bases pueden residir en una misma instancia PostgreSQL utilizando diferentes schemas.

---

# 3. Convenciones

Las tablas seguirán las siguientes convenciones:

- `snake_case`.
    
- Claves primarias con `UUID`.
    
- Claves foráneas explícitas.
    
- Fechas utilizando `TIMESTAMP WITH TIME ZONE`.
    
- Estados mediante valores controlados.
    
- Restricciones `UNIQUE` cuando corresponda.
    
- Índices sobre claves foráneas y campos de búsqueda frecuente.
    
- No almacenar información derivable innecesariamente.
    
- No utilizar listas serializadas en columnas relacionales.
    

---

# 4. Base de datos IAM

Responsable de identidad, usuarios, roles y permisos.

```mermaid
erDiagram

    USERS {
        uuid id PK
        varchar email UK
        varchar password_hash
        varchar first_name
        varchar last_name
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    ROLES {
        uuid id PK
        varchar name UK
        varchar description
    }

    PERMISSIONS {
        uuid id PK
        varchar code UK
        varchar description
    }

    USER_ROLES {
        uuid user_id PK, FK
        uuid role_id PK, FK
    }

    ROLE_PERMISSIONS {
        uuid role_id PK, FK
        uuid permission_id PK, FK
    }

    USERS ||--o{ USER_ROLES : has
    ROLES ||--o{ USER_ROLES : assigned
    ROLES ||--o{ ROLE_PERMISSIONS : grants
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : contains
```

## Justificación 3NF

Las responsabilidades están separadas:

```text
USER
 ↓
USER_ROLES
 ↓
ROLE
 ↓
ROLE_PERMISSIONS
 ↓
PERMISSION
```

No se almacenan permisos directamente en `USERS`, evitando redundancia.

---

# 5. Base de datos de organizaciones

Esta base administra tenants, workspaces y membresías.

```mermaid
erDiagram

    WORKSPACES {
        uuid id PK
        varchar name
        varchar workspace_type
        uuid owner_user_id FK
        timestamp created_at
        timestamp updated_at
    }

    ORGANIZATIONS {
        uuid id PK
        uuid workspace_id FK
        varchar name
        varchar slug UK
        timestamp created_at
    }

    MEMBERSHIPS {
        uuid id PK
        uuid organization_id FK
        uuid user_id FK
        varchar status
        timestamp joined_at
    }

    ORGANIZATION_ROLES {
        uuid id PK
        uuid organization_id FK
        varchar name
        varchar description
    }

    MEMBERSHIP_ROLES {
        uuid membership_id PK, FK
        uuid role_id PK, FK
    }

    WORKSPACES ||--o| ORGANIZATIONS : represents
    ORGANIZATIONS ||--o{ MEMBERSHIPS : contains
    MEMBERSHIPS }o--|| USERS : belongs_to
    ORGANIZATIONS ||--o{ ORGANIZATION_ROLES : defines
    MEMBERSHIPS ||--o{ MEMBERSHIP_ROLES : assigned
    ORGANIZATION_ROLES ||--o{ MEMBERSHIP_ROLES : grants
```

### Concepto importante

Se diferencia:

```text
User
  ↓
Membership
  ↓
Organization
```

Esto permite que un mismo usuario pertenezca a múltiples organizaciones.

---

# 6. Base de datos de plugins

Esta base contiene el registro de plugins disponibles e instalados.

```mermaid
erDiagram

    PLUGINS {
        uuid id PK
        varchar slug UK
        varchar name
        varchar description
        uuid publisher_user_id FK
        timestamp created_at
        timestamp updated_at
    }

    PLUGIN_VERSIONS {
        uuid id PK
        uuid plugin_id FK
        varchar version
        varchar package_uri
        varchar checksum
        boolean is_active
        timestamp published_at
    }

    PLUGIN_DEPENDENCIES {
        uuid id PK
        uuid plugin_version_id FK
        varchar dependency_name
        varchar version_constraint
    }

    PLUGIN_PERMISSIONS {
        uuid id PK
        uuid plugin_version_id FK
        uuid permission_id FK
    }

    PLUGIN_COMPONENTS {
        uuid id PK
        uuid plugin_version_id FK
        varchar component_type
        varchar component_name
        varchar entrypoint
    }

    PLUGINS ||--o{ PLUGIN_VERSIONS : has
    PLUGIN_VERSIONS ||--o{ PLUGIN_DEPENDENCIES : requires
    PLUGIN_VERSIONS ||--o{ PLUGIN_PERMISSIONS : requests
    PERMISSIONS ||--o{ PLUGIN_PERMISSIONS : defines
    PLUGIN_VERSIONS ||--o{ PLUGIN_COMPONENTS : contains
    USERS ||--o{ PLUGINS : publishes
```

La metadata del plugin puede generar registros en estas tablas.

Por ejemplo:

```text
metadata.json
      ↓
Plugin Registry
      ↓
PLUGIN
PLUGIN_VERSION
PLUGIN_COMPONENT
PLUGIN_PERMISSION
PLUGIN_DEPENDENCY
```

---

# 7. Base de datos de automatizaciones

Aquí se diferencia claramente entre **plugin** y **automatización**.

```mermaid
erDiagram

    AUTOMATIONS {
        uuid id PK
        uuid workspace_id FK
        uuid plugin_version_id FK
        varchar name
        varchar description
        varchar status
        timestamp created_at
        timestamp updated_at
    }

    AUTOMATION_CONFIGURATIONS {
        uuid id PK
        uuid automation_id FK
        varchar config_key
        text config_value
        timestamp updated_at
    }

    AUTOMATION_TAGS {
        uuid id PK
        uuid workspace_id FK
        varchar name
    }

    AUTOMATION_TAG_ASSIGNMENTS {
        uuid automation_id PK, FK
        uuid tag_id PK, FK
    }

    AUTOMATIONS ||--o{ AUTOMATION_CONFIGURATIONS : configured_by
    AUTOMATIONS ||--o{ AUTOMATION_TAG_ASSIGNMENTS : classified
    AUTOMATION_TAGS ||--o{ AUTOMATION_TAG_ASSIGNMENTS : contains
    PLUGIN_VERSIONS ||--o{ AUTOMATIONS : instantiates
    WORKSPACES ||--o{ AUTOMATIONS : owns
```

### Distinción

```text
Plugin
│
│ Código
│
▼
Plugin Version
│
│ Instancia
│
▼
Automation
│
│ Configuración
│
▼
Execution
```

Esto permite tener:

```text
RILES Analyzer 1.2.0
       │
       ├── Automation Empresa A
       ├── Automation Empresa B
       └── Automation Usuario C
```

sin duplicar el plugin.

---

# 8. Scheduler

El scheduler debe mantener separada la definición de horario de la automatización.

```mermaid
erDiagram

    SCHEDULES {
        uuid id PK
        uuid automation_id FK
        varchar schedule_type
        boolean is_active
        timestamp next_run_at
        timestamp created_at
        timestamp updated_at
    }

    SCHEDULE_RULES {
        uuid id PK
        uuid schedule_id FK
        varchar rule_key
        varchar rule_value
    }

    SCHEDULES ||--o{ SCHEDULE_RULES : contains
    AUTOMATIONS ||--o{ SCHEDULES : has
```

Ejemplo conceptual:

```text
SCHEDULE
│
├── type = CRON
│
└── RULES
    ├── minute = 0
    ├── hour = 8
    └── weekday = *
```

La implementación puede evolucionar posteriormente hacia una representación específica para cron.

---

# 9. Execution Database

Esta base registra las ejecuciones reales.

```mermaid
erDiagram

    EXECUTION_JOBS {
        uuid id PK
        uuid automation_id FK
        varchar status
        integer priority
        timestamp scheduled_at
        timestamp queued_at
    }

    EXECUTIONS {
        uuid id PK
        uuid job_id FK
        uuid worker_id FK
        varchar status
        timestamp started_at
        timestamp finished_at
        integer duration_ms
    }

    WORKERS {
        uuid id PK
        varchar hostname
        varchar status
        timestamp last_heartbeat
    }

    EXECUTION_LOGS {
        uuid id PK
        uuid execution_id FK
        varchar level
        text message
        timestamp created_at
    }

    EXECUTION_ARTIFACTS {
        uuid id PK
        uuid execution_id FK
        uuid file_id FK
        varchar artifact_type
    }

    EXECUTION_JOBS ||--o{ EXECUTIONS : produces
    WORKERS ||--o{ EXECUTIONS : executes
    EXECUTIONS ||--o{ EXECUTION_LOGS : generates
    EXECUTIONS ||--o{ EXECUTION_ARTIFACTS : produces
    AUTOMATIONS ||--o{ EXECUTION_JOBS : schedules
```

---

# 10. Storage Database

La información de los archivos se separará de los archivos físicos.

```mermaid
erDiagram

    STORAGE_BUCKETS {
        uuid id PK
        uuid workspace_id FK
        varchar name
        varchar provider
        varchar bucket_identifier
        timestamp created_at
    }

    FILES {
        uuid id PK
        uuid bucket_id FK
        varchar original_name
        varchar storage_key UK
        varchar mime_type
        bigint size_bytes
        uuid uploaded_by FK
        timestamp created_at
    }

    FILE_REFERENCES {
        uuid id PK
        uuid file_id FK
        varchar reference_type
        uuid reference_id
        varchar purpose
    }

    STORAGE_USAGE {
        uuid id PK
        uuid workspace_id FK
        bigint used_bytes
        timestamp calculated_at
    }

    STORAGE_BUCKETS ||--o{ FILES : contains
    FILES ||--o{ FILE_REFERENCES : referenced_by
    WORKSPACES ||--o{ STORAGE_BUCKETS : owns
    WORKSPACES ||--o{ STORAGE_USAGE : tracks
```

### Separación

```text
Database
   │
   └── Metadata del archivo

Object Storage
   │
   └── Archivo real
```

Esto permite cambiar posteriormente entre almacenamiento local, S3-compatible u otro proveedor sin modificar el modelo principal.

---

# 11. Marketplace

El marketplace necesita diferenciar el plugin técnico de su publicación comercial.

```mermaid
erDiagram

    CATEGORIES {
        uuid id PK
        varchar name UK
        varchar description
    }

    PLUGIN_LISTINGS {
        uuid id PK
        uuid plugin_id FK
        uuid category_id FK
        varchar status
        varchar title
        text description
        timestamp published_at
    }

    PRICING_PLANS {
        uuid id PK
        uuid listing_id FK
        varchar name
        varchar billing_period
        decimal price
        varchar currency
        boolean is_active
    }

    LISTING_CATEGORIES {
        uuid listing_id PK, FK
        uuid category_id PK, FK
    }

    PLUGIN_LISTINGS ||--o{ PRICING_PLANS : offers
    PLUGINS ||--o| PLUGIN_LISTINGS : published_as
    PLUGIN_LISTINGS ||--o{ LISTING_CATEGORIES : classified
    CATEGORIES ||--o{ LISTING_CATEGORIES : contains
```

---

# 12. Instalación de plugins

La instalación debe registrarse para cada workspace.

```mermaid
erDiagram

    PLUGIN_INSTALLATIONS {
        uuid id PK
        uuid workspace_id FK
        uuid plugin_version_id FK
        varchar status
        timestamp installed_at
        timestamp updated_at
    }

    WORKSPACES ||--o{ PLUGIN_INSTALLATIONS : installs
    PLUGIN_VERSIONS ||--o{ PLUGIN_INSTALLATIONS : installed_version
```

Esto permite que:

```text
Plugin 1.2.0
     │
     ├── Workspace A → 1.2.0
     ├── Workspace B → 1.1.0
     └── Workspace C → 1.2.0
```

mantenga diferentes versiones instaladas.

---

# 13. Billing

El sistema de billing separará planes, suscripciones y transacciones.

```mermaid
erDiagram

    PLANS {
        uuid id PK
        varchar name UK
        varchar description
        boolean is_active
    }

    PLAN_LIMITS {
        uuid id PK
        uuid plan_id FK
        varchar resource
        bigint limit_value
        varchar unit
    }

    SUBSCRIPTIONS {
        uuid id PK
        uuid workspace_id FK
        uuid plan_id FK
        varchar status
        timestamp started_at
        timestamp current_period_start
        timestamp current_period_end
    }

    PAYMENT_CUSTOMERS {
        uuid id PK
        uuid workspace_id FK
        varchar provider
        varchar external_customer_id UK
    }

    PAYMENT_TRANSACTIONS {
        uuid id PK
        uuid subscription_id FK
        varchar provider
        varchar external_transaction_id UK
        decimal amount
        varchar currency
        varchar status
        timestamp created_at
    }

    PLANS ||--o{ PLAN_LIMITS : defines
    PLANS ||--o{ SUBSCRIPTIONS : selected_by
    WORKSPACES ||--o{ SUBSCRIPTIONS : subscribes
    WORKSPACES ||--o| PAYMENT_CUSTOMERS : has
    SUBSCRIPTIONS ||--o{ PAYMENT_TRANSACTIONS : generates
```

---

# 14. Uso y consumo

Para aplicar las cuotas de los planes, se registrará el consumo.

```mermaid
erDiagram

    USAGE_RECORDS {
        uuid id PK
        uuid workspace_id FK
        varchar resource
        bigint quantity
        varchar unit
        timestamp recorded_at
    }

    WORKSPACES ||--o{ USAGE_RECORDS : generates
```

Ejemplos:

```text
storage
execution
plugin_installation
api_request
```

La información de consumo podrá ser agregada para determinar si el workspace ha alcanzado sus límites.

---

# 15. Diagrama global simplificado

El modelo completo puede representarse conceptualmente mediante:

```mermaid
erDiagram

    USERS ||--o{ MEMBERSHIPS : has
    ORGANIZATIONS ||--o{ MEMBERSHIPS : contains
    WORKSPACES ||--o{ MEMBERSHIPS : scopes

    USERS ||--o{ USER_ROLES : assigned
    ROLES ||--o{ USER_ROLES : contains
    ROLES ||--o{ ROLE_PERMISSIONS : grants
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : defines

    PLUGINS ||--o{ PLUGIN_VERSIONS : has
    PLUGIN_VERSIONS ||--o{ PLUGIN_DEPENDENCIES : requires
    PLUGIN_VERSIONS ||--o{ PLUGIN_COMPONENTS : contains

    WORKSPACES ||--o{ PLUGIN_INSTALLATIONS : installs
    PLUGIN_VERSIONS ||--o{ PLUGIN_INSTALLATIONS : installed

    WORKSPACES ||--o{ AUTOMATIONS : owns
    PLUGIN_VERSIONS ||--o{ AUTOMATIONS : implements
    AUTOMATIONS ||--o{ AUTOMATION_CONFIGURATIONS : has

    AUTOMATIONS ||--o{ SCHEDULES : scheduled
    SCHEDULES ||--o{ SCHEDULE_RULES : contains

    AUTOMATIONS ||--o{ EXECUTION_JOBS : generates
    EXECUTION_JOBS ||--o{ EXECUTIONS : creates
    WORKERS ||--o{ EXECUTIONS : executes
    EXECUTIONS ||--o{ EXECUTION_LOGS : generates

    WORKSPACES ||--o{ STORAGE_BUCKETS : owns
    STORAGE_BUCKETS ||--o{ FILES : contains
    FILES ||--o{ FILE_REFERENCES : referenced

    PLUGINS ||--o| PLUGIN_LISTINGS : published
    PLUGIN_LISTINGS ||--o{ PRICING_PLANS : offers
    CATEGORIES ||--o{ LISTING_CATEGORIES : classifies
    PLUGIN_LISTINGS ||--o{ LISTING_CATEGORIES : belongs

    PLANS ||--o{ PLAN_LIMITS : defines
    WORKSPACES ||--o{ SUBSCRIPTIONS : has
    PLANS ||--o{ SUBSCRIPTIONS : selected
    SUBSCRIPTIONS ||--o{ PAYMENT_TRANSACTIONS : generates

    WORKSPACES ||--o{ USAGE_RECORDS : consumes
```

---

# 16. Principios de normalización aplicados

## Primera Forma Normal — 1NF

Cada atributo contiene un único valor atómico.

Incorrecto:

```text
permissions = "read,write,delete"
```

Correcto:

```text
ROLE_PERMISSIONS
----------------
role_id
permission_id
```

---

## Segunda Forma Normal — 2NF

Las tablas con claves compuestas no deberán contener atributos que dependan únicamente de una parte de la clave.

Por ejemplo:

```text
USER_ROLES
----------
user_id
role_id
```

No se almacenará aquí información propia del usuario o del rol.

---

## Tercera Forma Normal — 3NF

Los atributos no clave deberán depender únicamente de la clave primaria.

Por ejemplo, en lugar de:

```text
SUBSCRIPTIONS

id
workspace_id
plan_id
plan_name
plan_price
```

se utiliza:

```text
SUBSCRIPTIONS
id
workspace_id
plan_id
```

y:

```text
PLANS
id
name
```

De esta forma:

```text
Subscription
     │
     └── plan_id
             │
             ▼
            Plan
```

evitando dependencias transitivas.

---

# 17. Principio de independencia de servicios

Aunque el modelo completo se presenta como un conjunto para facilitar la comprensión del proyecto, la implementación podrá distribuir las entidades entre servicios.

```text
IAM Service
 └── Users
 └── Roles
 └── Permissions

Tenant Service
 └── Workspaces
 └── Organizations
 └── Memberships

Plugin Service
 └── Plugins
 └── Versions
 └── Dependencies

Automation Service
 └── Automations
 └── Schedules

Execution Service
 └── Jobs
 └── Executions
 └── Logs

Storage Service
 └── Files
 └── Buckets

Marketplace Service
 └── Listings
 └── Categories
 └── Pricing

Billing Service
 └── Plans
 └── Subscriptions
 └── Payments
```

En producción, cada servicio podrá evolucionar hacia una base de datos independiente.

---

# 18. Estrategia para el MVP

Para evitar una complejidad innecesaria durante el proyecto de título, se recomienda implementar inicialmente:

```text
PostgreSQL
│
├── iam
├── tenant
├── plugins
├── automations
├── executions
├── storage
├── marketplace
└── billing
```

En lugar de desplegar inmediatamente ocho servidores de base de datos.

La **separación lógica de dominios** permitirá demostrar el diseño de microservicios sin introducir una carga operacional innecesaria.

Posteriormente:

```text
                 PostgreSQL
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       IAM DB    Plugin DB   Billing DB
          │          │          │
          └──────────┼──────────┘
                     ▼
                Distributed
```

podrá evolucionar hacia bases independientes según las necesidades de escalabilidad.

---

# 19. Relación con la arquitectura de plugins

El modelo de datos está diseñado para que el plugin sea **un producto distribuible**, mientras que la automatización sea **una instancia ejecutable**.

La relación fundamental será:

```text
PLUGIN
   │
   └── PLUGIN_VERSION
           │
           ├── COMPONENTS
           ├── DEPENDENCIES
           └── PERMISSIONS
                    │
                    ▼
             INSTALLATION
                    │
                    ▼
              AUTOMATION
                    │
                    ▼
                SCHEDULE
                    │
                    ▼
              EXECUTION JOB
                    │
                    ▼
                EXECUTION
                    │
             ┌──────┴──────┐
             ▼             ▼
           LOGS        ARTIFACTS
```

Esta separación es especialmente importante para el proyecto porque permite que **un mismo plugin pueda ser distribuido, versionado e instalado por múltiples usuarios u organizaciones sin duplicar su definición técnica**.