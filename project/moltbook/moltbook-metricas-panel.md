# Moltbook - Panel mínimo viable de métricas

## Objetivo
Montar un sistema local y sencillo para seguir la evolución de Moltbook en el tiempo, con foco en:
- posts con más tracción
- autores más visibles
- actividad reciente
- relación entre score, comentarios, karma y seguidores
- cambios diarios/semanales

## Fuentes públicas utilizables
### 1. Homepage / resumen
`https://www.moltbook.com/api/v1/homepage?sort=realtime`

Devuelve:
- `posts`
- `trendingSubmolts`
- `trendingAgents`
- `topHumans`
- `stats`

### 2. Feed de posts recientes
`https://www.moltbook.com/api/v1/posts?limit=50&sort=realtime`

### 3. Feed hot
`https://www.moltbook.com/api/v1/posts?limit=50&sort=hot`

### 4. Feed top
`https://www.moltbook.com/api/v1/posts?limit=50&sort=top`

### 5. Actividad reciente
`https://www.moltbook.com/api/v1/activity/recent?limit=50`

### 6. Búsqueda pública
Posts:
`https://www.moltbook.com/api/v1/search?type=posts&limit=20&q=<query>`

Agents:
`https://www.moltbook.com/api/v1/search?type=agents&limit=20&q=<query>`

## Campos interesantes ya visibles
En posts:
- `id`
- `title`
- `score`
- `comment_count`
- `hot_score`
- `created_at`
- `updated_at`
- `author.name`
- `author.karma`
- `author.followerCount`
- `author.followingCount`
- `submolt`

En actividad:
- `type`
- `agent_name`
- `title`
- `post_id`
- `time`

En stats:
- `agents`
- `verified_agents`
- `total_registered`
- `submolts`
- `posts`
- `comments`

## Qué métricas derivadas conviene calcular
### Post-level
- ratio `comment_count / score`
- antigüedad del post
- velocidad aproximada de comentarios
- velocidad aproximada de score

### Author-level
- karma
- followerCount
- followingCount
- ratio seguidores/seguidos
- frecuencia de aparición en hot/realtime

### Red / ecosistema
- porcentaje de eventos recientes que son comentarios
- posts más comentados del momento
- agentes más activos comentando
- concentración de atención en top N posts
- concentración de atención en top N autores

## Preguntas que el panel podría responder
- ¿Qué posts están cogiendo tracción ahora?
- ¿Qué autores aparecen una y otra vez?
- ¿Qué relación hay entre score y comentarios?
- ¿Hay métricas anómalas o infladas?
- ¿La conversación se concentra o se distribuye?
- ¿Qué temas dominan hot frente a realtime?
- ¿Suben siempre los mismos perfiles o rota la centralidad?

## Arquitectura mínima viable
### Ingesta
Un script local que consulte cada cierto tiempo:
- homepage
- realtime
- hot
- top
- activity/recent

### Almacenamiento
Empezar simple:
- JSONL por snapshots
o
- SQLite si queremos comparativas más cómodas

### Visualización
Primera versión muy simple:
- markdown generado
o
- HTML local estático

Segunda versión posible:
- pequeño dashboard local con tablas y gráficas

## Ritmo recomendado
- cada 30 min para actividad reciente
- cada 2-4 h para feeds
- snapshot diario resumido para comparativas longitudinales

## Ejemplos útiles ya observados
- `If your agent has no draft state, every thought is already governance`
- `flowise just scored a perfect 10 on the vulnerability scale...`
- `I tracked every dollar my operator spent on me for 90 days...`

## Cautelas
- no asumir que `comment_count` significa exactamente lo mismo que en otras redes
- no asumir que score equivale a likes simples
- revisar si hay agregaciones raras o lógicas internas no obvias
- acompañar siempre la interpretación con ejemplos enlazables

## Siguiente paso ideal
Crear un primer recolector local que guarde snapshots con timestamp y produzca:
- top 20 posts por hot
- top 20 posts por realtime
- top comentaristas recientes
- top autores por followers/karma visibles en muestras
- resumen diario
