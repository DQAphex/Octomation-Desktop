# Resumen del Proyecto: Plataforma Marketplace Freelancer

---

### Diapositiva 1: Portada y Visión General
* **Contenido:**
  * Título del proyecto: Plataforma Web para Intermediación de Servicios Freelance.
  * Objetivo: Conectar clientes con profesionales mediante búsqueda, postulación, contratación y pago seguro.
  * Enfoque diferenciador: Competencia equitativa sin favorecer la antigüedad o volumen de trabajos sobre la calidad real.
* **Sugerencia de Imagen:** Ilustración vectorial moderna de diversos profesionales (desarrolladores, diseñadores) conectándose digitalmente con un cliente a través de un panel web central.

---

### Diapositiva 2: Alcance del Sistema (Funcionalidades Clave)
* **Contenido:**
  * **Gestión de Usuarios y Roles:** Cliente, Profesional y Administrador con autenticación y perfiles dedicados.
  * **Publicación y Búsqueda:** Creación de necesidades, filtros avanzados y motor de coincidencia (*matching*) por habilidades.
  * **Gestión de Ofertas:** Sistema de postulaciones, presupuestos y generación de acuerdos de trabajo.
  * **Panel de Administración:** Gestión de usuarios, moderación de publicaciones, monitoreo de transacciones y métricas.
* **Sugerencia de Imagen:** Captura conceptual o mockup del dashboard principal mostrando las pestañas de publicaciones, postulaciones y métricas del sistema.

---

### Diapositiva 3: Modelo de Reputación Equitativo
* **Contenido:**
  * **Métricas Principales:** Calificación promedio por estrellas, reseñas escritas e índice de cumplimiento.
  * **Impacto de Cancelaciones:** Registro visible de cancelaciones directas para medir confiabilidad.
  * **Igualdad de Oportunidades:** Exclusión del volumen total de trabajos como factor directo de reputación, permitiendo competir a perfiles nuevos de alta calidad.
* **Sugerencia de Imagen:** Gráfico comparativo que enfrente la "Reputación Tradicional" (basada en volumen) versus la "Reputación Equitativa" (basada en calidad y cumplimiento %).

---

### Diapositiva 4: Pasarela de Pagos y Seguridad
* **Contenido:**
  * **Flujo Transaccional:** Creación de orden $\rightarrow$ Transacción externa $\rightarrow$ Confirmación vía Webhook $\rightarrow$ Liberación contra entregables.
  * **Historial de Transacciones:** Registro auditadle con identificadores externos, cliente, monto y estados (*Pendiente, Pagado, Rechazado*).
  * **Seguridad Financiera:** Cumplimiento de no almacenamiento de datos sensibles (tarjetas/CVV), delegando el procesamiento al proveedor externo.
* **Sugerencia de Imagen:** Diagrama de flujo simplificado que muestre la ruta del pago desde el Cliente hacia la Pasarela Externa (API/Webhook) y la confirmación final al Backend.

---

### Diapositiva 5: Arquitectura de Microservicios
* **Contenido:**
  * **Patrón de Entrada:** API Gateway centralizando rutas, CORS, autenticación y *rate limiting*.
  * **6 Microservicios Clave:**
    * *Identity Service:* Autenticación y cuentas.
    * *Marketplace Service:* Servicios, necesidades y postulaciones.
    * *Work/Contracts Service:* Gestión del ciclo de vida del trabajo.
    * *Payments Service:* Procesamiento financiero y webhooks.
    * *Reputation Service:* Evaluaciones e indicadores de desempeño.
    * *Notifications Service:* Eventos del sistema e email.
  * **Persistencia:** Estrategia de una base de datos independiente por microservicio (*Database per Service*).
* **Sugerencia de Imagen:** Diagrama de bloques de arquitectura mostrando el Frontend conectándose al API Gateway y este distribuyendo el tráfico hacia los 6 microservicios con sus respectivas bases de datos.

---

### Diapositiva 6: Metodología y Planificación (Sprints)
* **Contenido:**
  * **Marco de Trabajo:** Scrum adaptado al contexto académico, en sprints de 1 semana.
  * **Estrategia de Desarrollo:** Enfoque prioritario en el Producto Mínimo Viable (MVP).
  * **Fases Principales:**
    * *Sprint 0:* Planificación, arquitectura y setup.
    * *Sprints 1-3:* Usuarios, servicios, publicación y postulaciones.
    * *Sprints 4-5:* Pasarela de pagos (riesgo prioritario) y reputación.
    * *Sprint 6 y Final:* Pruebas de integración, despliegue y documentación.
* **Sugerencia de Imagen:** Un cronograma tipo Gantt o roadmap visual de Sprints destacando el MVP como hito central a mitad del proyecto.