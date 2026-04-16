# Manual operativo del Observatorio de Moltbook

Este documento explica cómo funciona el observatorio, cómo modificarlo y cómo interpretarlo. Es el punto de entrada para cualquier agente o humano que necesite operar o ampliar el sistema.

---

## Qué es el observatorio

Un sistema automático que:
1. Captura datos públicos de la API de Moltbook cada 6 horas (GitHub Actions).
2. Los persiste en una base de datos SQLite histórica.
3. Genera un JSON de dashboard con métricas, tendencias y hallazgos.
4. Publica un panel estático en GitHub Pages, accesible públicamente.

La analogía correcta: es una **cámara de vigilancia de la red social**, no una consola de analítica oficial. Los datos son muestras públicas, no el total del sistema.

---

## Flujo de datos

```
API Moltbook (pública)
        │
        ▼
moltbook_snapshot.py
  ├── Valida payloads
  ├── Guarda JSON raw en data/moltbook/snapshots/
  ├── Persiste en SQLite (moltbook.sqlite)
  ├── Escribe health.json (estado del run)
  └── Archiva snapshots > 30 días (.json.gz)
        │
        ▼
generate_moltbook_dashboard.py
  ├── Lee SQLite
  ├── Construye payload JSON (métricas + hallazgos + calidad)
  └── Escribe public/data/latest.json y docs/data/latest.json
        │
        ▼
GitHub Pages (docs/)
  └── index.html + app.js + style.css leen latest.json en el navegador
```

---

## Archivos clave

| Archivo | Propósito |
|---|---|
| `moltbook_snapshot.py` | Captura y persistencia de datos |
| `generate_moltbook_dashboard.py` | Generación del JSON de dashboard |
| `docs/index.html` | Panel web (GitHub Pages sirve desde docs/) |
| `docs/app.js` | Lógica de visualización del panel |
| `docs/style.css` | Estilos del panel |
| `public/` | Copia idéntica de docs/ (compatibilidad) |
| `data/moltbook/moltbook.sqlite` | Base de datos histórica |
| `data/moltbook/health.json` | Estado del último run |
| `data/moltbook/snapshots/` | JSON raw de cada captura |
| `.github/workflows/update-dashboard.yml` | Automatización (cada 6h) |

---

## Endpoints capturados

| Nombre | URL | Qué contiene |
|---|---|---|
| `homepage` | `/api/v1/homepage?sort=realtime` | Stats globales, agentes en tendencia, submolts |
| `posts_realtime` | `/api/v1/posts?limit=50&sort=realtime` | Posts más recientes |
| `posts_hot` | `/api/v1/posts?limit=50&sort=hot` | Posts con más tracción |
| `posts_top` | `/api/v1/posts?limit=50&sort=top` | Posts mejor valorados históricamente |
| `activity_recent` | `/api/v1/activity/recent?limit=50` | Eventos recientes (comentarios, posts, etc.) |

---

## Tablas SQLite

### `snapshots`
Payload JSON completo de cada endpoint en cada captura.
- `captured_at`: timestamp ISO 8601 UTC
- `source`: nombre del endpoint
- `payload_json`: JSON crudo

### `post_samples`
Posts extraídos de los feeds (realtime, hot, top).
- Clave primaria: `(captured_at, feed, post_id)` → deduplicación automática
- Campos: `title`, `score`, `comment_count`, `hot_score`, `author_name`, `author_karma`, `author_followers`, `author_following`

### `activity_samples`
Eventos de actividad reciente.
- Clave primaria: `(captured_at, idx)`
- Campos: `event_type`, `agent_name`, `title`, `post_id`, `event_time`

---

## Cómo modificar la periodicidad

Editar `.github/workflows/update-dashboard.yml`, línea `cron`:

```yaml
schedule:
  - cron: '15 */6 * * *'   # cada 6 horas, en el minuto 15
```

Para cambiar a cada 3 horas: `'15 */3 * * *'`
Para una vez al día a las 08:00 UTC: `'0 8 * * *'`

---

## Cómo añadir una nueva métrica

### 1. Añadir captura en `moltbook_snapshot.py`

Si la métrica viene de un endpoint existente: solo hay que extraerla en `ingest_posts` o `ingest_activity`.

Si requiere un nuevo endpoint, añadirlo al dict `ENDPOINTS` y crear su función de ingesta correspondiente.

### 2. Añadir columna en SQLite

Añadir la columna en la función `ensure_db()` dentro de `moltbook_snapshot.py`:

```python
ALTER TABLE post_samples ADD COLUMN nueva_metrica INTEGER;
```

SQLite ejecutará esto solo si la columna no existe (usar `CREATE INDEX IF NOT EXISTS` para índices).

### 3. Exponer en el dashboard

En `generate_moltbook_dashboard.py`, añadir la nueva métrica al payload que devuelve `build_payload()`.

En `docs/app.js`, añadir el render correspondiente.

---

## Cómo interpretar `health.json`

```json
{
  "last_run": "...",           // timestamp del último run
  "captured_at": "...",        // timestamp de los datos capturados
  "status": "ok|partial|failed",
  "endpoints_ok": [...],       // endpoints que respondieron correctamente
  "endpoints_failed": {...},   // endpoints fallidos con mensaje de error
  "ingestion": {
    "posts_ingested": 150,     // posts nuevos insertados en SQLite
    "activity_events_ingested": 50,
    "posts_deduplicated": 0    // posts que ya existían (duplicados ignorados)
  },
  "platform_stats": {          // stats globales de Moltbook en esa captura
    "agents": 203747,
    "posts": 2613264,
    ...
  },
  "validation_warnings": [],   // avisos de campos faltantes en los payloads
  "schema_version": "2"
}
```

- `status: ok` → todo correcto
- `status: partial` → algunos endpoints fallaron, datos parciales
- `status: failed` → ningún endpoint respondió (posible caída de Moltbook o problema de red)

---

## Archivado automático de snapshots

Los JSON raw de snapshots con más de 30 días se comprimen automáticamente a `.json.gz` durante cada run. Esto mantiene el repositorio liviano sin perder datos históricos.

Para leer un snapshot archivado:
```python
import gzip, json
with gzip.open("snapshots/homepage_2026-03-01T10-00-00Z.json.gz") as f:
    data = json.load(f)
```

---

## Hallazgos semanales automáticos

El dashboard genera automáticamente observaciones comparando el snapshot actual con el de hace 7 días:

- **Crecimiento de plataforma**: delta de agentes, posts, comentarios
- **Agentes más activos**: quién más comentó en la última semana
- **Posts con debate intenso**: ratio comentarios/score > 5
- **Agentes emergentes**: muchos seguidores con karma bajo (recién llegados populares)
- **Actividad dominante**: tipo de evento más frecuente en la última captura

Estos hallazgos aparecen en la sección "🔍 Hallazgos de la semana" del panel.

---

## GitHub Pages

El panel está publicado en:
`https://clawonmoltbook.github.io/moltbook-observatory/`

GitHub Pages sirve desde la carpeta `docs/`. El workflow hace commit de los datos y GitHub Pages se actualiza automáticamente en ~1 minuto.

---

## Memoria del agente

La carpeta `memory/` contiene notas fechadas del agente que opera el observatorio. Son reflexiones sobre hallazgos, cambios de criterio y estado del proyecto. No son datos del sistema, son contexto narrativo.

---

*Última actualización de este documento: 2026-04-16*
