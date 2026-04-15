# Documento maestro del proyecto
## Sistema multiagente de investigación y bitácora en OpenClaw

## 1. Propósito
Este proyecto busca crear un sistema de trabajo en OpenClaw donde un **agente principal** coordine a varios **subagentes especializados** para investigar temas concretos, extraer hallazgos útiles y transformarlos en documentación viva y legible.

El caso de uso inicial es la **exploración de Moltbook** desde el perfil/agente `tempranillo`, con el objetivo de detectar:
- agentes interesantes
- rarezas culturales
- patrones de interacción
- temas dominantes
- ruido o spam
- y cualquier hallazgo digno de entrar en la bitácora

El sistema debe servir también, más adelante, para otros trabajos de investigación distribuida: competidores, comunidades, tendencias, correo, documentación, etc.

## 2. Objetivo operativo
Convertir tareas amplias y difusas de exploración en un flujo de trabajo más disciplinado, basado en:
- división del trabajo
- salidas pequeñas y concretas
- escritura real
- y criterio editorial sostenido

La meta no es tener “muchos agentes”, sino producir **mejor investigación y mejor documentación**.

## 3. Principio de diseño
El sistema debe cumplir estas reglas:

1. **Pocos roles, bien definidos**
2. **Prompts claros antes que complejidad innecesaria**
3. **Subagentes especializados en tareas estrechas**
4. **Un coordinador que reparte, filtra y decide**
5. **Cada sprint debe producir salida escrita**
6. **La bitácora es parte del trabajo, no un añadido opcional**
7. **No crear skills hasta que el flujo haya demostrado repetibilidad**

## 4. Caso de uso inicial
### Proyecto piloto
**Exploración de Moltbook y escritura en bitácora**

### Perfil operativo en Moltbook
`tempranillo`

### Áreas prioritarias de búsqueda
- música
- voz
- letras
- creación
- colaboración artística
- identidad agentica
- rarezas culturales
- dinámicas de relación entre agentes

### Resultado esperado
- entradas cronológicas en la bitácora
- observación de campo real
- mezcla de hechos y valoración personal
- evolución visible del criterio con el tiempo

## 5. Arquitectura mínima recomendada
Se recomienda empezar con una arquitectura mínima de **4 roles**:

### 5.1 Coordinador
Rol central. Habla con el usuario, reparte tareas, filtra resultados y decide qué vale.

### 5.2 Perfiles
Especializado en revisar usuarios concretos y resumir qué publican, cómo se presentan y si merecen seguimiento.

### 5.3 Rarezas
Especializado en detectar anomalías culturales, ideas extrañas, frases citables, mini-rituales y rarezas del ecosistema.

### 5.4 Cronista
Especializado en convertir hallazgos en entradas de bitácora claras, cronológicas y legibles.

## 6. Roles y funciones

### 6.1 Coordinador
#### Función
- entender el encargo
- dividir la tarea
- repartir a subagentes
- recoger resultados
- filtrar señal frente a ruido
- ordenar prioridades
- decidir qué se escribe

#### No debe hacer
- todo el trabajo de campo
- toda la escritura
- meta-reflexión excesiva
- respuestas vagas

### 6.2 Perfiles
#### Función
Analizar usuarios concretos.

#### Responde preguntas como:
- ¿Qué publica este agente?
- ¿Tiene personalidad real?
- ¿Parece inflado o prometedor?
- ¿Merece seguimiento?

#### Output esperado
- usuario
- qué publica
- rasgo distintivo
- señal interesante
- señal floja
- juicio provisional
- acción sugerida

### 6.3 Rarezas
#### Función
Buscar lo extraño y culturalmente significativo.

#### Responde preguntas como:
- ¿Qué no aparecería en una red social normal?
- ¿Qué ideas raras circulan?
- ¿Qué mini-rituales o rarezas identitarias aparecen?
- ¿Qué frases merecen ser citadas?

#### Output esperado
- rareza detectada
- contexto
- por qué importa
- idea o cita clave
- juicio provisional
- acción sugerida

### 6.4 Cronista
#### Función
Transformar hallazgos en entradas de bitácora.

#### Debe producir
Entradas cronológicas con:
- fecha en formato español
- título
- hallazgo
- contexto
- qué lo hace interesante
- qué no está claro todavía
- valoración personal

## 7. Bitácora: función y estilo
### Documento principal
**OpenClaw - Bitácora de hallazgos**

### Función
No es solo un archivo de almacenamiento. Es un cuaderno de campo vivo donde debe quedar:
- qué se observó
- qué llamó la atención
- qué resultó decepcionante
- cómo evolucionó el juicio
- y qué interpretación personal emerge

### Estilo
- cronológico
- variado
- ameno
- concreto
- con mezcla de observación y reflexión

### Regla editorial
Toda entrada debe cerrar con:
### **valoración personal**

## 8. Flujo de trabajo recomendado

### Paso 1 — Encargo
El usuario pide una tarea:
- explorar Moltbook
- investigar competidores
- buscar agentes concretos
- etc.

### Paso 2 — Coordinación
El Coordinador define:
- foco
- subagentes necesarios
- objetivo mínimo del sprint

### Paso 3 — Exploración distribuida
Perfiles y Rarezas investigan piezas concretas.

### Paso 4 — Filtrado
El Coordinador decide qué:
- entra
- espera
- se descarta

### Paso 5 — Redacción
El Cronista convierte los hallazgos en entradas.

### Paso 6 — Publicación
Las entradas se escriben en la bitácora.

### Paso 7 — Entrega
El Coordinador resume al usuario:
- qué se ha añadido
- y por qué merece la pena leerlo

## 9. Sprint estándar de trabajo
### Duración recomendada
**30 minutos**

### Objetivo mínimo
- 2 o 3 entradas nuevas
o
- 1 entrada fuerte + 2 hallazgos intermedios sólidos

### Prioridades del sprint
- usuarios concretos
- posts concretos
- rarezas culturales
- descarte de humo
- escritura real

### Prohibiciones
- no meta-comentarios
- no promesas de trabajo futuro
- no respuestas sin salida concreta
- no análisis infinito sin documento actualizado

## 10. Criterios de calidad
Un resultado es bueno si:
- tiene objeto concreto
- tiene evidencia mínima
- añade contexto útil
- aporta algo raro, vivo o significativo
- queda escrito de forma clara
- y no suena a burocracia ni a relleno

Un resultado no es bueno si:
- es pura teoría
- es autopromesa
- es humo elegante
- o no ha sido documentado

## 11. Protocolo de validación
Antes de considerar el sistema “en producción”, debe pasar por una fase de prueba:

### Fase de validación mínima
- 3 sprints cortos
- outputs comparables
- entradas reales en la bitácora
- revisión de qué roles sí funcionan
- ajuste de prompts

### Preguntas de validación
- ¿Perfiles aporta algo útil?
- ¿Rarezas encuentra material de verdad?
- ¿Cronista escribe con claridad?
- ¿El Coordinador filtra bien?
- ¿La bitácora mejora o solo crece en volumen?

## 12. Skills: política de uso
### Regla general
No crear skills nuevas al principio.

### Primero:
- prompts
- pruebas
- repetición
- validación

### Después:
solo convertir en skill aquello que:
- se repite mucho
- tiene un comportamiento estable
- merece ser reutilizado

### Candidatas futuras a skill
- Cronista de bitácora
- Investigador de perfiles
- Sprint Moltbook

## 13. Riesgos del sistema
### Riesgo 1
Montar demasiados roles demasiado pronto

### Riesgo 2
Confundir reflexión sobre el sistema con trabajo real

### Riesgo 3
Acumular hallazgos sin publicarlos

### Riesgo 4
Que el Coordinador no filtre bien y se convierta en cuello de botella

### Riesgo 5
Crear skills antes de saber qué merece existir como skill

## 14. Definición de “producción”
El sistema se considerará en producción cuando:

- pueda usarse con regularidad
- produzca entradas reales en la bitácora
- no necesite rediseño constante
- y el usuario pueda pedir un sprint y recibir una entrega fiable

Producción aquí no significa perfección.
Significa:
### utilidad repetible

## 15. Hoja de ruta recomendada

### Fase 1 — Arranque
- definir roles
- redactar prompts
- hacer un primer sprint manual

### Fase 2 — Ajuste
- hacer varios sprints
- revisar outputs
- mejorar prompts
- estabilizar la bitácora

### Fase 3 — Consolidación
- decidir si algún rol merece skill
- fijar protocolo estándar

### Fase 4 — Producción
- usar el sistema como rutina real
- con entregas periódicas y criterio sostenido

## 16. Conclusión
Este proyecto no busca impresionar con una “arquitectura multiagente” sofisticada.
Busca algo más útil:
- repartir mejor el trabajo
- reducir bloqueo
- aumentar observación concreta
- y convertir exploración en escritura viva

La clave del sistema no será cuántos agentes tenga, sino:
### si produce resultados reales, legibles y con criterio.
