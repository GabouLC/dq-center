## Historia o issue

Cierra: HU-__ / #__

<!-- Una rama y un pull request por historia. Si no hay historia (docs, CI, mantenimiento), enlaza el issue o explica por qué no lo hay. -->

## Qué cambia

<!-- En pocas líneas: qué se hizo y por qué. Si tocaste el flujo (ingesta, homologación, Privacy Gate, motor), dilo. -->

-

## Cómo se verificó

<!-- Pega la salida real, no un "funciona". Marca lo que corriste y anota lo que NO probaste. -->

- [ ] `pytest -q`: <!-- pega la última línea de la salida (N passed) -->
- [ ] `npm run build` en `web/`: <!-- resultado -->
- [ ] Prueba de aceptación contra el manifiesto: 0 diferencias en las cuatro etapas (si toca el flujo)
- [ ] Capturas o evidencia en `docs/evidencias/`: <!-- ruta -->
- Lo que no probé:

## Definition of Done

Copiada de [docs/sprints/README.md](../docs/sprints/README.md#definition-of-done):

- [ ] Código con pruebas: cada criterio de aceptación tiene al menos una prueba automatizada, y el CI (pytest y build de la web) pasa
- [ ] 0 diferencias contra el manifiesto en las cuatro etapas (si toca el flujo; si no, marca "no aplica" y di por qué)
- [ ] ADR en `docs/adr/` si algo se aparta del Documento de Arquitectura (o "no aplica")
- [ ] Evidencia visual o de datos en `docs/evidencias/`
- [ ] Sin credenciales: ni claves, tokens ni cadenas de conexión (van en variables de entorno; `.env.example` sin valores)
- [ ] Revisado por otro integrante (nadie aprueba su propio PR)
- [ ] El issue de la historia queda cerrado y enlaza su evidencia

## Capturas

<!-- Arrastra aquí las capturas del portal (antes y después). Sin datos reales ni credenciales a la vista. -->
