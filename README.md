# Sistema de Profesionales (ERP multi-tenant)

Plataforma tipo ERP multi-tenant para profesionistas (médicos, dentistas, barberos, etc.) enfocada en la gestión de citas, expedientes y control operativo del negocio. El sistema contempla dos experiencias principales:

- **Perfil del profesionista**: su espacio principal de administración, personalización y control.
- **Perfil del cliente/invitado**: acceso mediante enlace de invitación para ver/gestionar su información o citas según permisos.

Incluye personalización por profesionista, usando **DaisyUI** para una interfaz consistente y adaptable. El backend está construido con **Django + Django REST Framework**, persistencia en **PostgreSQL** y autenticación con **JWT**. El frontend (no incluido en este repositorio) está diseñado con **Vue + Vite + TailwindCSS**.

---

## Características principales

- **Multi-tenant por profesionista**: aislamiento lógico de datos para cada profesional.
- **Gestión de citas**: disponibilidad, agenda, recordatorios, historial.
- **Expedientes y registros**: información clínica/servicios, notas y documentos asociados.
- **Clientes/invitados**: flujo de acceso mediante enlace de invitación.
- **Personalización por profesionista**: temas, branding y configuración por perfil.
- **API REST** con autenticación JWT y estructura escalable.

---

## Stack tecnológico

**Backend**
- Django
- Django REST Framework
- PostgreSQL
- JWT (autenticación y autorización)

**Frontend (referencial)**
- Vue
- Vite
- TailwindCSS + DaisyUI

---

## Instalación (backend)

### 1) Requisitos previos

- Python 3.10+ (recomendado)
- PostgreSQL 12+
- virtualenv o similar

### 2) Configuración del entorno

Copia el archivo de ejemplo y completa tus variables:

```bash
cp example.env .env
```

Variables mínimas (ver `example.env`):

```
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
```

### 3) Crear y activar entorno virtual

```bash
python -m venv .venv
source .venv/bin/activate
```

### 4) Instalar dependencias

```bash
pip install -r requirements.txt
```

### 5) Migraciones y superusuario

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6) Ejecutar el servidor

```bash
python manage.py runserver
```
El backend quedará disponible en `http://127.0.0.1:8000/`.

### 7) Checar documentación API
La documentación de las APIs dicponible `http://127.0.0.1:8000/api/docs/`
---

## Funcionamiento (visión general)

### Multi-tenant para profesionistas
Cada profesionista funciona como un "tenant" lógico con su propio espacio de datos: citas, clientes, expedientes y configuración. El aislamiento permite operar múltiples profesionales en una misma instancia del sistema sin mezclar información.

### Flujo del profesionista
1. Registra/gestiona su perfil profesional.
2. Configura disponibilidad, servicios y preferencias de agenda.
3. Administra clientes, citas y expedientes desde su panel.
4. Personaliza su entorno (branding, paleta, texto, etc.).

### Flujo de clientes/invitados
1. Reciben un enlace de invitación.
2. Acceden a su información, citas y registros permitidos.
3. Pueden aceptar o reprogramar citas según configuración.

### Seguridad y autenticación
El acceso a la API se protege con JWT. Cada rol (profesionista, staff, cliente) posee permisos adecuados según su contexto. Esto asegura que la información del tenant se mantenga aislada y segura.

---

## Sugerencias de mejoras e implementaciones futuras

### 1) Multi-tenant avanzado
- **Esquemas por tenant** (postgres schemas) o middleware de separación más estricto.
- **Panel de administración multi-tenant** para operar instancias y planes.

### 2) Gestión de agenda
- Integración con Google Calendar / Outlook.
- Notificaciones por WhatsApp, SMS o email.
- Configuración de disponibilidad inteligente (bloques, descansos, horarios especiales).

### 3) Expedientes y documentos
- Almacenamiento de archivos médicos/servicios en S3 o GCS.
- Versionado y auditoría de cambios en expedientes.

### 4) Facturación y pagos
- Integración con Stripe/MercadoPago.
- Facturación electrónica (según país/región).

### 5) Personalización y branding
- Builder de landing por profesionista.
- Plantillas y temas por sector (médico, estética, dental).

### 6) Observabilidad y calidad
- Logging estructurado y trazas distribuidas.
- Tests de integración y cobertura automática.
- Monitoreo con Prometheus/Grafana.

---

## Estructura del proyecto (backend)

```
backend/
core/
users/
manage.py
requirements.txt
```

> Nota: El frontend se gestiona en un repositorio separado (Vue + Vite + TailwindCSS).

---

## Contribuciones

Si deseas contribuir, por favor abre un issue o envía un PR con la descripción detallada del cambio.

---

## Licencia

Pendiente de definir.
