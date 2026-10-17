# ¿A qué jugamos?

Web para decidir entre amigos a qué juego de Steam jugar, deslizando cartas al estilo Tinder.

- **Sin cuentas ni servidor propio:** el navegador de quien crea la sala guarda la partida y los demás se conectan a él directamente (WebRTC con [PeerJS](https://peerjs.com/)).
- **Catálogo de Steam actualizado a diario:** la API de Steam no se puede consultar desde el navegador (no permite CORS). Por eso la GitHub Action `.github/workflows/update-catalog.yml` ejecuta cada día `scripts/update_catalog.py`. El script consulta la tienda de Steam y SteamSpy, regenera `games.json` (precios, ofertas, reseñas y etiquetas) y vuelve a publicar la web en GitHub Pages.
- Para forzar una actualización: pestaña **Actions** → «Actualizar catálogo y publicar» → **Run workflow**.

## Cómo se juega

1. Una persona crea la sala y comparte el enlace de «Invitar».
2. Cada uno elige sus temáticas y desliza: → sí, ← no.
3. Un «no» descarta el juego para todos. Lo que gusta a alguien aparece primero en el mazo de los demás.
4. Cuando a todos los conectados les gusta el mismo juego: ¡match!

El anfitrión debe tener la página abierta mientras se vota. Si la recarga, la sala se recupera.
