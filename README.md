# ¿A qué jugamos?

Web para decidir entre amigos a qué juego de Steam jugar, deslizando cartas al estilo Tinder.

- **Sin cuentas ni servidor propio:** el navegador de quien crea la sala guarda la partida y los demás se conectan a él directamente (WebRTC con [PeerJS](https://peerjs.com/)).
- **Catálogo de Steam bajo demanda:** la API de Steam no se puede consultar desde el navegador (no permite CORS). Por eso la GitHub Action `.github/workflows/update-catalog.yml` ejecuta `scripts/update_catalog.py`, que regenera `games.json` y vuelve a publicar la web. Solo se lanza a mano, nunca de forma programada:
  - desde la app: el anfitrión pulsa «Actualizar catálogo de Steam» en su sala (se abre GitHub) y la app carga el catálogo nuevo en cuanto está listo, también para los invitados;
  - o en la pestaña **Actions** → «Actualizar catálogo y publicar» → **Run workflow**.
  - Modo `precios` (≈1 min): precios y ofertas. Modo `completo` (≈20 min): también juegos nuevos, reseñas y etiquetas.
  - Solo puede lanzarlo una cuenta con permiso de escritura en el repositorio.

## Cómo se juega

1. Una persona crea la sala y comparte el enlace de «Invitar».
2. Cada uno elige sus temáticas y desliza: → sí, ← no.
3. Un «no» descarta el juego para todos. Lo que gusta a alguien aparece primero en el mazo de los demás.
4. Cuando a todos los conectados les gusta el mismo juego: ¡match!

El anfitrión debe tener la página abierta mientras se vota. Si la recarga, la sala se recupera.
